"""
Page definitions for the experiment.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""


from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants, FruitOffer, Purchase
from django.forms import modelformset_factory, ModelForm, IntegerField, HiddenInput


class NormalWaitPage(WaitPage):
    # For whatever reason, oTree suddenly issues a warning "page_sequence cannot contain a class called 'WaitPage'"...
    # So it appears we have to define an own WaitPage which is exactly the same...
    pass


class OfferForm(ModelForm):
    old_amount = IntegerField(initial=0, widget=HiddenInput)

    class Meta:
        model = FruitOffer
        fields = ('old_amount', 'kind', 'amount', 'price')


def get_offers_formset():
    """Helper method that returns a Django formset for a dynamic amount of FruitOffers."""
    return modelformset_factory(FruitOffer, form=OfferForm, extra=1)


def get_purchases_formset(n_forms=0):
    """
    Helper method that returns a Django formset for a dynamic amount of Purchases. Initially `n_forms` empty
    forms are shown.
    """
    return modelformset_factory(Purchase, fields=('amount', 'fruit'), extra=n_forms)


class CreateOffersPage(Page):
    """
    First page: Page where sellers can define their offers.
    """

    def vars_for_template(self):
        """
        Define the forms that will be shown.
        """

        OffersFormSet = get_offers_formset()

        if self.player.role() == 'seller':
            # For the seller, show a formset with fruit offers. If this is not the first round, already defined
            # fruit offers will be loaded.
            # The seller can choose to buy fruit from the wholesale market at fixed prices defined in
            # `FruitOffer.PURCHASE_PRICES`.

            player_offers_qs = FruitOffer.objects.filter(seller=self.player)   # load existing offers for this player

            return {
                'purchase_prices': FruitOffer.PURCHASE_PRICES,
                'offers_formset': OffersFormSet(queryset=player_offers_qs),
            }
        else:  # nothing to do for customers at this page
            return {}

    def before_next_page(self):
        """
        Implement custom form handling for formsets.
        """
        if self.player.role() == 'buyer':   # nothing to do for customers at this page
            return

        # get the formset
        OffersFormSet = get_offers_formset()

        # fill it with the submitted data
        offers_formset = OffersFormSet(self.form.data)

        # iterate through the forms in the formset
        offers_objs = []   # stores *new* FruitOffer objects
        cost = 0           # total cost for the seller buying fruits that she or he can offer on the market
        for form_idx, form in enumerate(offers_formset.forms):
            if form.is_valid():
                if self.subsession.round_number > 1 and form.cleaned_data.get('id'):    # update an existing offer
                    # set the new amount and price for an existing offer
                    new_amount = form.cleaned_data['amount']
                    new_price = form.cleaned_data['price']
                    changed_offer = form.cleaned_data['id']
                    changed_offer.amount = form.cleaned_data['old_amount'] + new_amount   # increment existing amount
                    changed_offer.price = new_price

                    if changed_offer.amount > 0:
                        changed_offer.save()    # save existing offer (update)
                        cost += new_amount * FruitOffer.PURCHASE_PRICES[changed_offer.kind]   # update total cost
                    else:
                        changed_offer.delete()  # offers that dropped to amount zero will be removed
                elif form.cleaned_data.get('amount', 0) > 0:    # create new offer
                    # create a new FruitOffer object with the submitted data and set the seller to the current player
                    submitted_data = {k: v for k, v in form.cleaned_data.items() if k != 'old_amount'}
                    offer = FruitOffer(**submitted_data, seller=self.player)
                    cost += offer.amount * FruitOffer.PURCHASE_PRICES[offer.kind]   # update total cost
                    offers_objs.append(offer)

            else:   # invalid forms are not handled well so far -> we just ignore them
                print('player %d: invalid form #%d' % (self.player.id_in_group, form_idx))

        # store the new offers in the DB (insert new data)
        if offers_objs:
            FruitOffer.objects.bulk_create(offers_objs)

        # update seller's balance
        self.player.balance -= cost


class PurchasePage(Page):
    """
    Second page: Page where customers can buy offered fruit.
    """

    def vars_for_template(self):
        """
        Define the forms that will be shown.
        """

        if self.player.role() == 'buyer':
            # load the all offers for this round (by filtering for same subsession)
            # use `select_related` for quicker data retrieval
            offers = FruitOffer.objects.select_related('seller__subsession', 'seller__participant').\
                filter(seller__subsession=self.player.subsession).\
                order_by('seller', 'kind')

            # get a formset for purchases, one for each available offer
            PurchasesFormSet = get_purchases_formset(len(offers))

            # fill the formset with data from the offers
            purchases_formset = PurchasesFormSet(initial=[{'amount': 0, 'fruit': offer}
                                                          for offer in offers],
                                                 queryset=Purchase.objects.none())

            return {
                'purchases_formset': purchases_formset,                 # formset as whole
                'offers_with_forms': zip(offers, purchases_formset),    # formset where each form is combined with the
                                                                        #  related offer
            }
        else:  # for sellers, only show the fruit she/he currently offers
            offers = FruitOffer.objects.filter(seller=self.player).order_by('kind')

            return {
                'sellers_offers': offers
            }

    def before_next_page(self):
        """
        Implement custom form handling for formsets.
        """

        if self.player.role() == 'seller':  # nothing to do for sellers at this page
            return

        # get the formset for purchases
        PurchasesFormSet = get_purchases_formset()

        # pass it the submitted data
        purchases_formset = PurchasesFormSet(self.form.data)

        # iterate through the forms in the formset
        purchase_objs = []    # stores new Purchase objects
        total_price = 0       # total cost for the customer
        for form_idx, form in enumerate(purchases_formset.forms):
            # handle valid forms where at least 1 item was bought
            if form.is_valid() and form.cleaned_data['amount'] > 0:
                # create a new Purchase object with the submitted data and set the buyer to the current player
                purchase = Purchase(**form.cleaned_data, buyer=self.player)
                #purchase.fruit.amount -= purchase.amount       # decrease amount of available fruit (nope - this will
                                                                # be done below in the Results page)
                prod = purchase.amount * purchase.fruit.price   # total price for this offer
                purchase.fruit.seller.balance += prod           # increase seller's balance
                total_price += prod                    # add to total price

                #purchase.fruit.save()   # seller will be saved automatically (as it is a Player object)
                purchase_objs.append(purchase)

        # store the purchases in the DB
        Purchase.objects.bulk_create(purchase_objs)

        # update buyer's balance
        self.player.balance -= total_price


class Results(Page):
    """
    Third page: Summarize results of this round.
    """

    def vars_for_template(self):
        """
        Transactions and change in balance for both player roles.
        """

        if self.player.role() == 'buyer':
            # for a customer, load all purchases she or he made in this round
            transactions = Purchase.objects.select_related('buyer__subsession', 'buyer__participant',
                                                           'fruit__seller__participant'). \
                filter(buyer=self.player).\
                order_by('fruit__seller', 'fruit__kind')
        else:
            # for a seller, load all sales she or he made in this round
            transactions = Purchase.objects.select_related('buyer__participant', 'fruit__seller'). \
                filter(fruit__seller=self.player).\
                order_by('buyer', 'fruit__kind')

        return {
            'transactions': transactions,
            'balance_change': sum([t.amount * t.fruit.price for t in transactions])
        }

    def before_next_page(self):
        """
        Update the balance for this round
        """

        if self.subsession.round_number < Constants.num_rounds:
            # get player instance for next round
            next_round = self.subsession.round_number + 1
            next_player = self.player.in_round(next_round)

            # set the current balance as the new initial balance for the next round
            next_player.initial_balance = self.player.balance
            next_player.balance = next_player.initial_balance

            if self.player.role() == 'seller':
                # copy sellers' offers to the new round

                # fetch all sales from this seller in this round
                sales_from_seller = list(Purchase.objects.select_related('fruit').filter(fruit__seller=self.player))

                # fetch all offers from this seller in this round and iterate through them
                for o in FruitOffer.objects.filter(seller=self.player):
                    o.pk = None   # set primary key to None in order to store as new FruitOffer object

                    # find the related purchase if fruit from this offer was bought
                    related_purchase_ind = None
                    for p_i, purchase in enumerate(sales_from_seller):
                        if purchase.fruit == o:
                            related_purchase_ind = p_i
                            break

                    if related_purchase_ind is not None:
                        # decrease the amount of available fruit for this offer
                        rel_purchase = sales_from_seller.pop(related_purchase_ind)
                        o.amount -= rel_purchase.amount

                    # set the seller as the player instance for the next round
                    o.seller = next_player

                    # store to database
                    o.save()


# define the page sequence. interleave with WaitPages because purchases can only be made after offers were defined and
# results can only be shown after purchases were made.
page_sequence = [
    CreateOffersPage,
    NormalWaitPage,
    PurchasePage,
    NormalWaitPage,
    Results,
    NormalWaitPage
]

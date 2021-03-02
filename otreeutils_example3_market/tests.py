"""
Automated tests for the experiment.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

import random

from otree.api import Currency as c, currency_range, Submission
from . import pages
from ._builtin import Bot
from .models import Constants, FruitOffer, Purchase


def _fill_submitdata(submitdata, objs, i):
    for k, v in objs.items():
        submitdata['form-%d-%s' % (i, k)] = v


class PlayerBot(Bot):
    def _create_offers_input(self):
        if self.round_number == 1:
            existing_offers = []
        else:
            # prev_round = self.subsession.round_number - 1
            # prev_player = self.player.in_round(prev_round)

            existing_offers = list(FruitOffer.objects.filter(seller=self.player))

        n_new_offers = random.randint(0, 5)
        offer_objs = existing_offers + [None] * n_new_offers

        submitdata = {}
        offers_properties = []
        for i, prev_offer in enumerate(offer_objs):
            if prev_offer is not None:
                offer = {
                    'id': prev_offer.pk,
                    'old_amount': prev_offer.amount,
                    'amount': 0,
                    'price': float(prev_offer.price),
                    'kind': prev_offer.kind
                }
            else:
                offer = {'old_amount': 0}

            rand_data = {
                'amount': random.randint(0, 10),
                'price': round(random.uniform(0, 3), 2)
            }

            if prev_offer is None or random.choice((1, 0)):
                offer.update(rand_data)

                if prev_offer is None:
                    offer['kind'] = random.choice(FruitOffer.KINDS)[0]

            _fill_submitdata(submitdata, offer, i)

            offer['new_amount'] = offer['old_amount'] + offer['amount']

            if offer['new_amount'] > 0:
                offers_properties.append(offer)

        # formset metadata
        submitdata['form-TOTAL_FORMS'] = len(offer_objs)
        submitdata['form-INITIAL_FORMS'] = len(existing_offers)
        submitdata['form-MIN_NUM_FORMS'] = len(existing_offers)
        submitdata['form-MAX_NUM_FORMS'] = 1000

        return submitdata, offers_properties

    def _check_offers(self, offers_properties):
        if offers_properties is not None:
            offers_properties = offers_properties[:]   # copy

        saved_offers = FruitOffer.objects.filter(seller=self.player)

        if self.player.role() == 'buyer':
            assert len(saved_offers) == 0, 'buyer should not offer anything'
            assert offers_properties is None
        else:
            assert len(saved_offers) == len(offers_properties)

            # check saved offers
            n_matches = 0
            for o1 in saved_offers:
                assert o1.seller == self.player, 'seller is not current player'

                for i_o2, o2 in enumerate(offers_properties):
                    if 'id' in o2:
                        ids_match = o1.pk == o2['id']
                    else:
                        ids_match = True

                    if o1.kind == o2['kind'] and o1.amount == o2['new_amount'] and o1.price == c(o2['price'])\
                            and ids_match:
                        n_matches += 1
                        offers_properties.pop(i_o2)
                        break

            assert len(offers_properties) == 0 and n_matches == len(saved_offers),\
                'saved offers do not match submitted data'

    def _create_purchases_input(self):
        offers = FruitOffer.objects.select_related('seller__subsession', 'seller__participant'). \
            filter(seller__subsession=self.player.subsession). \
            order_by('seller', 'kind')

        submitdata = {}
        purchases_properties = []
        for i, o in enumerate(offers):
            purchase = {
                'amount': random.randint(0, 3),
                'fruit': o.pk
            }

            _fill_submitdata(submitdata, purchase, i)

            if purchase['amount'] > 0:
                purchases_properties.append(purchase)

        # formset metadata
        submitdata['form-TOTAL_FORMS'] = len(offers)
        submitdata['form-INITIAL_FORMS'] = 0
        submitdata['form-MIN_NUM_FORMS'] = 0
        submitdata['form-MAX_NUM_FORMS'] = len(offers)

        return submitdata, purchases_properties

    def _check_purchases(self, purchases_properties):
        if purchases_properties is not None:
            purchases_properties = purchases_properties[:]  # copy

        saved_purchases = Purchase.objects.filter(buyer=self.player)

        if self.player.role() == 'seller':
            assert len(saved_purchases) == 0, 'seller should not purchase anything'
            assert purchases_properties is None
        else:
            assert len(saved_purchases) == len(purchases_properties)

            # check saved purchases
            n_matches = 0
            for p1 in saved_purchases:
                assert p1.buyer == self.player, 'buyer is not current player'

                for i_p2, p2 in enumerate(purchases_properties):
                    if p1.fruit.pk == p2['fruit'] and p1.amount == p2['amount']:
                        n_matches += 1
                        purchases_properties.pop(i_p2)
                        break

            assert len(purchases_properties) == 0 and n_matches == len(saved_purchases),\
                'saved purchases do not match submitted data'

    def _check_balance(self, offers_properties, purchases_properties):
        if self.player.role() == 'seller':
            cost = 0
            for o in offers_properties:
                cost += o['amount'] * FruitOffer.PURCHASE_PRICES[o['kind']]

            gain = 0
            for p in Purchase.objects.select_related('fruit').filter(fruit__seller=self.player):
                gain += p.amount * p.fruit.price

            assert self.player.balance == self.player.initial_balance - cost + gain
        else:
            cost = 0
            for p in purchases_properties:
                fruit = FruitOffer.objects.get(pk=p['fruit'])
                cost += p['amount'] * fruit.price

            assert self.player.balance == self.player.initial_balance - cost

    def play_round(self):
        if self.player.role() == 'buyer':
            offers_input = None
            offers_properties = None
        else:
            assert self.player.role() == 'seller', 'player role is something other than buyer or seller'
            offers_input, offers_properties = self._create_offers_input()

        # disable HTML checking because formset forms are created dynamically with JavaScript
        yield Submission(pages.CreateOffersPage, offers_input, check_html=False)

        self._check_offers(offers_properties)

        if self.player.role() == 'buyer':
            purchases_input, purchases_properties = self._create_purchases_input()
        else:
            purchases_input = None
            purchases_properties = None

        yield Submission(pages.PurchasePage, purchases_input, check_html=False)

        self._check_purchases(purchases_properties)

        yield Submission(pages.Results)

        self._check_balance(offers_properties, purchases_properties)

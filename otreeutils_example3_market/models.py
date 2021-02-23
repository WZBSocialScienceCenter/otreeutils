"""
Model definitions including "custom data models" `FruitOffer` and `Purchase`.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

import random

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)

from otree.db.models import ForeignKey, Model
from otreeutils.admin_extensions import custom_export


author = 'Markus Konrad'

doc = """
Example experiment: selling/buying products on a market.
Implemented with custom data models.

Many individuals (1 ... N-1) are selling fruit with two attributes (e.g. kind of fruit and price). Each chooses a kind
and a price. Then individual N needs to choose which fruit to buy.  
"""


class Constants(BaseConstants):
    name_in_url = 'market'
    players_per_group = None
    num_rounds = 3


class Subsession(BaseSubsession):
    def creating_session(self):   # oTree 2 method name (used to be before_session_starts)
        if self.round_number == 1:
            # for each player, set a random initial balance in the first round
            for p in self.get_players():
                p.initial_balance = c(random.triangular(1, 20, 10))
                p.balance = p.initial_balance


class Group(BaseGroup):   # we're not using groups
    pass


class Player(BasePlayer):
    initial_balance = models.CurrencyField()   # balance at the start of the round
    balance = models.CurrencyField()           # balance at the end of the round

    def role(self):
        """
        Define the role of each player. The first player is always the "buyer" i.e. customer whereas all other players
        are selling fruit.
        """
        if self.id_in_group == 1:
            return 'buyer'
        else:
            return 'seller'


class FruitOffer(Model):
    """
    Custom data model derived from Django's generic `Model` class. This class defines an offer of fruit with three
    properties:
    - amount of available fruit
    - selling price per item
    - kind of fruit

    Additionally, a reference to the seller is stored via a `ForeignKey` to `Player`.
    """

    KINDS = (
        ('Apple', 'Apple'),
        ('Orange', 'Orange'),
        ('Banana', 'Banana'),
    )
    PURCHASE_PRICES = {
        'Apple': c(0.20),
        'Orange': c(0.30),
        'Banana': c(0.50),
    }

    amount = models.IntegerField(label='Amount', min=0, initial=0)           # number of fruits available
    price = models.CurrencyField(label='Price per fruit', min=0, initial=0)
    kind = models.StringField(choices=KINDS)
    # easy to add more attributes per fruit, e.g.:
    #is_organic = models.BooleanField()   # if True: organic fruit, else conventional

    # creates many-to-one relation -> this fruit is sold by a certain player, a player can sell many fruits
    seller = ForeignKey(Player, on_delete=models.CASCADE)

    class CustomModelConf:
        """
        Configuration for otreeutils admin extensions.
        This class and its attributes must be existent in order to include this model in the data viewer / data export.
        """
        data_view = {
            'exclude_fields': ['seller_id'],
            'link_with': 'seller'
        }
        export_data = {
            'exclude_fields': ['seller_id'],
            'link_with': 'seller'
        }


class Purchase(Model):
    """
    Custom data model derived from Django's generic `Model` class. This class defines a purchase made by a certain
    customer (buyer) for a certain fruit. Hence it stores a reference to a buyer via a `ForeignKey` to `Player` and
    a reference to a fruit offer via a `ForeignKey` to `FruitOffer`. Additionally, the amount of fruit bought is
    stored.
    """

    amount = models.IntegerField(min=1)    # fruits taken
    # price = models.CurrencyField(min=0)   optional: allow bargaining

    fruit = ForeignKey(FruitOffer, on_delete=models.CASCADE)     # creates many-to-one relation -> this purchase
                                                                 # relates to a certain fruit offer
                                                                 # many purchases can be made for this offer (as long
                                                                 # as there's at least 1 fruit left)
    buyer = ForeignKey(Player, on_delete=models.CASCADE)         # creates many-to-one relation -> this fruit is bought
                                                                 # by a certain player *in a certain round*. a player
                                                                 # can buy many fruits.

    class CustomModelConf:
        """
        Configuration for otreeutils admin extensions.
        This class and its attributes must be existent in order to include this model in the data viewer / data export.
        """
        data_view = {
            'exclude_fields': ['buyer_id'],
            'link_with': 'buyer'
        }
        export_data = {
            'exclude_fields': ['buyer_id'],
            'link_with': 'buyer'
        }
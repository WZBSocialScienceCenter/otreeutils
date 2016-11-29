from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)


author = 'Markus Konrad'

doc = """
Example 1 for usage of the otreeutils package.
"""


class Constants(BaseConstants):
    name_in_url = 'otreeutils_example1'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    understanding_questions_wrong_attempts = models.PositiveIntegerField()   # number of wrong attempts on understanding quesions page

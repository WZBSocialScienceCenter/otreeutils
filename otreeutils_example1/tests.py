import random

from otree.api import Currency as c, currency_range
from . import views
from ._builtin import Bot
from .models import Constants


class PlayerBot(Bot):
    def play_round(self):
        yield (views.SomeUnderstandingQuestions, {
            'understanding_questions_wrong_attempts': random.randint(0, 10),
        })

        yield (views.ExtendedPageWithTimeoutWarning, )

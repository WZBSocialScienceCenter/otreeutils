import random

from . import pages
from ._builtin import Bot


class PlayerBot(Bot):
    def play_round(self):
        yield (pages.SomeUnderstandingQuestions, {
            'understanding_questions_wrong_attempts': random.randint(0, 10),
        })

        yield (pages.ExtendedPageWithTimeoutWarning, )

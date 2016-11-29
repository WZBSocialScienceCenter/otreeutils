from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants

from otreeutils.surveys import SurveyPage

#survey_pages = generate_pages_for_survey_player(models.Player, 'otreeutils_example2.views')


class SurveyPage1(SurveyPage):
    pass

SurveyPage1.setup_survey(models.Player, 0)

page_sequence = [
    SurveyPage1,
]

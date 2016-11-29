from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants

from otreeutils.surveys import SurveyPage, setup_survey_pages


class SurveyIntro(Page):
    pass


class SurveyPage1(SurveyPage):
    pass


class SurveyPage2(SurveyPage):
    pass


class SurveyPage3(SurveyPage):
    pass

survey_pages = [
    SurveyPage1,
    SurveyPage2,
    SurveyPage3,
]

setup_survey_pages(models.Player, survey_pages)

page_sequence = [
    SurveyIntro,
]

page_sequence.extend(survey_pages)
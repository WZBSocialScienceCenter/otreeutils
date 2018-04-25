# Definition of views/pages for the survey.
# Please note: When using oTree 2.x, this file should be called "pages.py" instead of "views.py"
#

from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants

from otreeutils.surveys import SurveyPage, setup_survey_pages


class SurveyIntro(Page):
    pass


# let's create the survey pages here
# unfortunately, it's not possible to create them dynamically


class SurveyPage1(SurveyPage):
    pass


class SurveyPage2(SurveyPage):
    pass


class SurveyPage3(SurveyPage):
    pass


# Create a list of survey pages.
# The order is important! The survey questions are taken in the same order
# from the SURVEY_DEFINITIONS in models.py

survey_pages = [
    SurveyPage1,
    SurveyPage2,
    SurveyPage3,
]

# Common setup for all pages (will set the questions per page)
setup_survey_pages(models.Player, survey_pages)

page_sequence = [
    SurveyIntro,
]

# add the survey pages to the page sequence list
page_sequence.extend(survey_pages)
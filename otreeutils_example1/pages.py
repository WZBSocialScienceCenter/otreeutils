from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants

from otreeutils.pages import AllGroupsWaitPage, ExtendedPage, UnderstandingQuestionsPage, APPS_DEBUG


class SomeUnderstandingQuestions(UnderstandingQuestionsPage):
    page_title = 'Example 1.1: A page with some understanding questions'
    #set_correct_answers = APPS_DEBUG    # this is the default setting
    set_correct_answers = False   # do not fill out the correct answers in advance (this is for fast skipping through pages)
    form_model = models.Player
    form_field_n_wrong_attempts = 'understanding_questions_wrong_attempts'
    questions = [
        {
            'question': 'What is 2+2?',
            'options': [2, 4, 5, 8],
            'correct': 4,
        },
        {
            'question': 'What is π?',
            'options': [1.2345, 3.14159],
            'correct': 3.14159,
            'hint': 'You can have a look at Wikipedia!'
        },
        {
            'question': 'Is this too easy?',
            'options': ['Yes', 'No', 'Maybe'],
            'correct': 'Yes',
        },
    ]


class ExtendedPageWithTimeoutWarning(ExtendedPage):
    page_title = 'Example 1.2: A page with timeout warning.'
    timeout_warning_seconds = 10
    timeout_warning_message = "You're too slow. Hurry up!"


class PageWithCustomURLName(ExtendedPage):
    custom_name_in_url = 'foobar'


page_sequence = [
    SomeUnderstandingQuestions,
    AllGroupsWaitPage,
    ExtendedPageWithTimeoutWarning,
    PageWithCustomURLName,
]

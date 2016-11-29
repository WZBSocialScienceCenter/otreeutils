from django import forms

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)

from otreeutils.surveys import create_player_model_for_survey


author = 'Your name here'

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = 'otreeutils_example2'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


GENDER_CHOICES = (
    ('female', 'Female'),
    ('male', 'Male'),
    ('no_answer', 'Prefer not to answer'),
)

YESNO_CHOICES = (
    ('yes', 'Yes'),
    ('no', 'No'),
)

Player = create_player_model_for_survey('otreeutils_example2.models', (
    {
        'page_title': 'Survey Questions - Page 1',
        'survey_fields': [
            ('q1_a', {
                'text': 'How old are you?',
                'field': models.PositiveIntegerField(min=18, max=100),
            }),
            ('q1_b', {
                'text': 'Please tell us your gender.',
                'field': models.CharField(choices=GENDER_CHOICES),
            }),
        ]
    },
    {
        'page_title': 'Survey Questions - Page 2',
        'survey_fields': [
            ('q2_a', {
                'text': 'Are you a student?',
                'field': models.CharField(choices=YESNO_CHOICES),
            }),
            ('q2_b', {
                'text': 'If so, in which field of study?',
                'field': models.CharField(blank=True),
            }),
        ]
    },
    {
        'page_title': 'Survey Questions - Page 3',
        'survey_fields': [
            ('q3_a', {
                'text': 'Did you enjoy the experiment?',
                'field': models.CharField(choices=YESNO_CHOICES),
            }),
        ]
    }
))
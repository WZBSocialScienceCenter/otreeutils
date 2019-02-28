from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)

from otreeutils.surveys import create_player_model_for_survey, generate_likert_field, generate_likert_table


author = 'Markus Konrad'

doc = """
Example 2 for usage of the otreeutils package.
"""


class Constants(BaseConstants):
    name_in_url = 'otreeutils_example2'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


# some pre-defined choices

GENDER_CHOICES = (
    ('female', 'Female'),
    ('male', 'Male'),
    ('no_answer', 'Prefer not to answer'),
)

YESNO_CHOICES = (
    ('yes', 'Yes'),
    ('no', 'No'),
)

# define a Likert 5-point scale with its labels

likert_5_labels = (
    'Strongly disagree',
    'Disagree',
    'Neither agree nor disagree',
    'Agree',
    'Strong agree'
)

likert_5point_field = generate_likert_field(likert_5_labels)


# define survey questions per page
# for each page define a page title and a list of questions
# the questions have a field name, a question text (input label), and a field type (model field class)
SURVEY_DEFINITIONS = (
    {
        'page_title': 'Survey Questions - Page 1 - Simple questions and inputs',
        'survey_fields': [
            ('q_age', {   # field name (which will also end up in your "Player" class and hence in your output data)
                'text': 'How old are you?',   # survey question
                'field': models.PositiveIntegerField(min=18, max=100),  # the same as in normal oTree model field definitions
            }),
            ('q_gender', {
                'text': 'Please tell us your gender.',
                'field': models.CharField(choices=GENDER_CHOICES),
            }),
        ]
    },
    {
        'page_title': 'Survey Questions - Page 2 - Likert 5-point scale',
        'survey_fields': [
            ('q_otree_surveys', {  # most of the time, you'd add a "help_text" for a Likert scale question. You can use HTML:
                'help_text': """
                <p>Consider this quote:</p>
                <blockquote>
                    "oTree is great to make surveys, too."
                </blockquote>
                <p>What do you think?</p>
                """,
                'field': likert_5point_field(),   # don't forget the parentheses at the end!
            }),
            ('q_just_likert', {
                 'label': 'Another Likert scale input:',  # optional, no HTML
                 'field': likert_5point_field(),  # don't forget the parentheses at the end!
            }),
        ]
    },
    {
        'page_title': 'Survey Questions - Page 3 - Several forms',
        'survey_fields': [   # you can also split into questions into several forms for better CSS styling
            {                # you need to provide a dict then. you can add more keys to the dict which are then available in the template
                'form_name': 'first_form',   # optional, can be used for CSS styling
                'fields': [
                    ('q_student', {
                        'text': 'Are you a student?',
                        'field': models.CharField(choices=YESNO_CHOICES),
                    }),
                    ('q_field_of_study', {
                        'text': 'If so, in which field of study?',
                        'field': models.CharField(blank=True),
                    }),
                ]
            },
            {
                'form_name': 'second_form',  # optional, can be used for CSS styling
                'fields': [
                    ('q_otree_years', {
                         'text': 'For how many years do you use oTree?',
                         'help_text': '<small>This is a help text.</small>',
                         'help_text_below': True,
                         'field': models.PositiveIntegerField(min=0, max=10),
                    })
                ]
            },
        ]
    },
    {
        'page_title': 'Survey Questions - Page 4 - Likert scale table',
        'survey_fields': [
            # create a table of Likert scale choices
            # we use the same 5-point scale a before and specify four rows for the table,
            # each with a tuple (field name, label)
            generate_likert_table(likert_5_labels,
                                  [
                                      ('q_pizza_tasty', 'Tasty'),
                                      ('q_pizza_spicy', 'Spicy'),
                                      ('q_pizza_cold', 'Too cold'),
                                      ('q_pizza_satiable', 'Satiable'),
                                  ],
                                  form_help_initial='<p>How was your latest Pizza?</p>',  # HTML to be placed on top of form
                                  form_help_final='<p>Thank you!</p>'                     # HTML to be placed below form
            )
        ]
    }
)

# now dynamically create the Player class from the survey definitions
Player = create_player_model_for_survey('otreeutils_example2.models', SURVEY_DEFINITIONS)
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
    def creating_session(self):
        for i, p in enumerate(self.get_players()):
            p.treatment = (i % 2) + 1   # every second player gets treatment 2


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

EBAY_ITEMS_PER_WEEK = (
    ('<5', 'less than 5'),
    ('5-10', 'between 5 and 10'),
    ('>10', 'more than 10'),
)

# define a Likert 5-point scale with its labels

likert_5_labels = (
    'Strongly disagree',
    'Disagree',
    'Neither agree nor disagree',
    'Agree',
    'Strongly agree'
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
        'survey_fields': [   # you can also split questions into several forms for better CSS styling
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
                                      ('q_pizza_cold', 'Too cold<br>or even frozen'),
                                      ('q_pizza_satiable', 'Satiable'),
                                  ],
                                  form_help_initial='<p>How was your latest Pizza?</p>',  # HTML to be placed on top of form
                                  form_help_final='<p>Thank you!</p>',                    # HTML to be placed below form
                                  table_row_header_width_pct=15,                          # width of row header (first column) in percent. default: 25
            )
        ]
    },
    {
        'page_title': 'Survey Questions - Page 5 - Forms depending on other variable',
        'survey_fields': [  # we define two forms here ...
            {   # ... this one is shown when player.treatment == 1 ...
                'form_name': 'treatment_1_form',
                'fields': [
                    ('q_treatment_1', {
                        'text': 'This is a question for treatment 1: Do you feel tired?',
                        'field': models.CharField(choices=YESNO_CHOICES, blank=True),
                    }),
                ]
            },
            {   # ... this one is shown when player.treatment == 2 ...
                'form_name': 'treatment_2_form',  # optional, can be used for CSS styling
                'fields': [
                    ('q_treatment_2', {
                        'text': "This is a question for treatment 2:  Don't you feel tired?",
                        'field': models.CharField(choices=YESNO_CHOICES, blank=True),
                    }),
                ]
            },
        ]
    },
    {
        'page_title': 'Survey Questions - Page 6 - Conditional fields and widget adjustments',
        'survey_fields': [
            ('q_uses_ebay', {
                'text': 'Do you sell things on eBay?',
                'field': models.CharField(choices=YESNO_CHOICES),
            }),
            ('q_ebay_member_years', {
                'text': 'For how many years are you an eBay member?',
                'field': models.IntegerField(min=1, blank=True, default=None),
                'input_suffix': 'years',                      # display suffix "years" after input box
                'widget_attrs': {'style': 'display:inline'},  # adjust widget style
                # set a JavaScript condition. if it evaluates to true (here: if "uses ebay" is set to "yes"),
                # this input is shown:
                'condition_javascript': '$("#id_q_uses_ebay").val() === "yes"'
            }),
            ('q_ebay_sales_per_week', {
                'text': 'How many items do you sell on eBay per week?',
                'field': models.CharField(choices=EBAY_ITEMS_PER_WEEK, blank=True, default=None),
                # set a JavaScript condition. if it evaluates to true (here: if "uses ebay" is set to "yes"),
                # this input is shown:
                'condition_javascript': '$("#id_q_uses_ebay").val() === "yes"'
            }),
        ]
    },
    {
        'page_title': 'Survey Questions - Page 7 - Random data input for quick debugging',
        'form_help_initial': """
<p>On this page, the form is filled in randomly if you run the experiment in debug mode (i.e. with
   <code>otree devserver</code> or <code>otree runserver</code> so that <code>APPS_DEBUG</code> is <code>True</code>
   &mdash; see <code>settings.py</code>).</p>
<p>This feature is enabled for this page in <code>pages.py</code> like this:</p>

<code>class SurveyPage7(SurveyPage):
    debug_fill_forms_randomly = True</code> 
""",
        'survey_fields': [
            # similar to page 4
            generate_likert_table(likert_5_labels,
                                  [
                                      ('q_weather_cold', "It's too cold"),
                                      ('q_weather_hot', "It's too hot"),
                                      ('q_weather_rainy', "It's too rainy"),
                                  ],
                                  form_help_initial='<p>What do you think about the weather?</p>',
                                  form_help_final='<p>&nbsp;</p>',
                                  form_name='likert_table'
            ),
            {   # if you use a likert table *and* other questions on the same page, you have to wrap the other questions
                # in a extra "sub-form", i.e. an extra dict with "fields" list
                'form_name': 'other_questions',  # optional, can be used for CSS styling
                'fields': [
                    ('q_monthly_income', {
                        'text': "What's your monthly income?",
                        'field': models.CurrencyField(min=0)
                    }),
                    ('q_num_siblings', {
                        'text': "How many siblings do you have?",
                        'field': models.IntegerField(min=0, max=20),
                    }),
                    ('q_comment', {
                        'text': "Please give us feedback on the experiment:",
                        'field': models.LongStringField(max_length=500)
                    }),
                ]
            }
        ]
    },
)

# now dynamically create the Player class from the survey definitions
# we can also pass additional (non-survey) fields via `other_fields`
Player = create_player_model_for_survey('otreeutils_example2.models', SURVEY_DEFINITIONS, other_fields={
    'treatment': models.IntegerField()
})

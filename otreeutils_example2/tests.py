import random

from . import pages, models
from ._builtin import Bot


def rand_val_from_choices(choices):
    return random.choice([k for k, _ in choices])


def rand_val_from_likert():
    return random.randint(1, len(models.likert_5_labels))


class PlayerBot(Bot):
    def play_round(self):
        yield (pages.SurveyIntro, )

        yield (pages.SurveyPage1, {
            'q_age': random.randint(18, 100),
            'q_gender': rand_val_from_choices(models.GENDER_CHOICES),
        })

        yield (pages.SurveyPage2, {
            'q_otree_surveys': rand_val_from_likert(),
            'q_just_likert': rand_val_from_likert(),
        })

        yield (pages.SurveyPage3, {
            'q_student': rand_val_from_choices(models.YESNO_CHOICES),
            'q_field_of_study': rand_val_from_choices([('', None), ('Sociology', None), ('Psychology', None)]),
            'q_otree_years': random.randint(0, 10),
        })

        likert_table_rows = (
            'tasty',
            'spicy',
            'cold',
            'satiable'
        )

        likert_table_data = {'q_pizza_' + k: rand_val_from_likert() for k in likert_table_rows}
        yield (pages.SurveyPage4, likert_table_data)

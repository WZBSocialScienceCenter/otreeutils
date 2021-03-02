import random

from . import pages, models
from ._builtin import Bot


def rand_val_from_choices(choices):
    return random.choice([k for k, _ in choices])


class PlayerBot(Bot):
    def play_round(self):
        yield (pages.SurveyIntro, )

        yield (pages.SurveyPage1, {
            'q_age': random.randint(18, 100),
            'q_gender': rand_val_from_choices(models.GENDER_CHOICES),
        })

        yield (pages.SurveyPage2, {
            'q_otree_surveys': random.randint(1, len(models.likert_5_labels)),
            'q_just_likert': random.randint(1, len(models.likert_5_labels)),
            'q_likert_htmllabels': random.randint(1, len(models.likert_5_labels_html)),
            'q_likert_centered': random.randint(-2, len(models.likert_5_labels) - 3),
            'q_likert_labeled': random.choice(models.likert_5point_values),
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

        likert_table_rows2 = (
            'tasty',
            'spicy'
        )

        likert_table_data = {'q_pizza_' + k: random.randint(1, len(models.likert_5_labels)) for k in likert_table_rows}
        likert_table_data2 = {'q_hotdog_' + k: random.choice(models.likert_5point_values) for k in likert_table_rows2}
        likert_table_data.update(likert_table_data2)
        yield (pages.SurveyPage4, likert_table_data)

        yield (pages.SurveyPage5, {
            'q_treatment_%d' % self.player.treatment: rand_val_from_choices(models.YESNO_CHOICES)
        })

        p6_data = {'q_uses_ebay': rand_val_from_choices(models.YESNO_CHOICES)}
        if p6_data['q_uses_ebay'] == 'yes':
            p6_data.update({
                'q_ebay_member_years': random.randint(1, 10),
                'q_ebay_sales_per_week': rand_val_from_choices(models.EBAY_ITEMS_PER_WEEK)
            })
        yield (pages.SurveyPage6, p6_data)

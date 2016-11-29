from django import forms

from otree.api import BasePlayer, Page

from .pages import ExtendedPage


def create_player_model_for_survey(module, survey_definitions, base_cls=None):
    if base_cls is None:
        base_cls = BasePlayer

    model_attrs = {
        '__module__': module,
        '_survey_defs': survey_definitions,
    }

    # collect fields
    for survey_page in survey_definitions:
        for field_name, qdef in survey_page['survey_fields']:
            model_attrs[field_name] = qdef['field']

    # dynamically create model
    model_cls = type('Player', (base_cls, _SurveyModelMixin), model_attrs)

    return model_cls


# def generate_pages_for_survey_player(player_cls, module, base_cls=None, base_template='otreeutils/SurveyPage.html'):
#     if base_cls is None:
#         base_cls = otree.views.abstract.PlayerUpdateView
#
#     survey_definitions = player_cls.get_survey_definitions()
#     pages = []
#     for i, survey_page in enumerate(survey_definitions):
#         attrs = {
#             '__module__': module,
#             'template_name': base_template
#         }
#         attrs.update(survey_page)
#
#         page_cls = type('SurveyPage%d' % (i+1), (_SurveyPageMixin, ), attrs)
#
#         pages.append(page_cls)
#
#     return pages
#

class _SurveyModelMixin(object):
    @classmethod
    def get_survey_definitions(cls):
        return cls._survey_defs


# class _SurveyPageMixin(otree.views.abstract.PlayerUpdateView):
#     pass

class SurveyPage(ExtendedPage):
    template_name = 'otreeutils/SurveyPage.html'
    form_fields = []
    field_labels = {}

    @classmethod
    def setup_survey(cls, player_cls, page_idx):
        survey_defs = player_cls.get_survey_definitions()[page_idx]
        cls.form_model = player_cls
        cls.page_title = survey_defs['page_title']

        for field_name, qdef in survey_defs['survey_fields']:
            cls.field_labels[field_name] = qdef['text']
            cls.form_fields.append(field_name)

    def get_context_data(self, **kwargs):
        ctx = super(SurveyPage, self).get_context_data(**kwargs)

        form = kwargs['form']

        for field_name, field in form.fields.items():
            field.label = self.field_labels[field_name]

        ctx.update({
           'survey_form': form,
        })

        return ctx
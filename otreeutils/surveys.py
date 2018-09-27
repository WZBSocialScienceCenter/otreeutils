"""
Survey extensions that allows to define survey questions with a simple data structure and then automatically creates
the necessary model fields and pages.

Sept. 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

from otree.api import BasePlayer

from .pages import ExtendedPage


def create_player_model_for_survey(module, survey_definitions, base_cls=None):
    """
    Dynamically create a player model in module <module> with a survey definitions and a base player class.
    Parameter survey_definitions is a list, where each list item is a survey definition for a single page.
    Each survey definition for a single page consists of list of field name, question definition tuples.
    Each question definition has a "field" (oTree model field class) and a "text" (field label).

    Returns the dynamically created player model with the respective fields (class attributes).
    """
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


class _SurveyModelMixin(object):
    """Little mix-in for dynamically generated survey model classes"""
    @classmethod
    def get_survey_definitions(cls):
        return cls._survey_defs


def setup_survey_pages(form_model, survey_pages):
    """
    Helper function to set up a list of survey pages with a common form model
    (a dynamically generated survey model class).
    """
    for i, page in enumerate(survey_pages):
        page.setup_survey(form_model, i)   # call setup function with model class and page index


class SurveyPage(ExtendedPage):
    """
    Common base class for survey pages.
    Displays a form for the survey questions that were defined for this page.
    """
    template_name = 'otreeutils/SurveyPage.html'
    field_labels = {}

    @classmethod
    def setup_survey(cls, player_cls, page_idx):
        """Setup a survey page using model class <player_cls> and survey definitions for page <page_idx>."""
        survey_defs = player_cls.get_survey_definitions()[page_idx]
        cls.form_model = player_cls
        cls.page_title = survey_defs['page_title']

        cls.form_fields = []
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
"""
Survey extensions that allows to define survey questions with a simple data structure and then automatically creates
the necessary model fields and pages.

March 2019, Markus Konrad <markus.konrad@wzb.eu>
"""

from functools import partial
from collections import OrderedDict

from otree.api import BasePlayer, widgets, models

from .pages import ExtendedPage


def generate_likert_field(labels, widget=None):
    """
    Return a function which generates a new `IntegerField` with a Likert scale between 1 and `len(labels)`. Use
    `widget` as selection widget (default is `RadioSelectHorizontal`).

    Example with a 4-point Likert scale:

    ```
    likert_4_field = generate_likert_field(["Strongly disagree", "Disagree",  "Agree", "Strongly agree"])

    class Player(BasePlayer):
        q1 = likert_4_field()
    ```
    """
    if not widget:
        widget = widgets.RadioSelectHorizontal

    choices = list(zip(range(1, len(labels) + 1), labels))

    return partial(models.IntegerField, widget=widget, choices=choices)


def generate_likert_table(labels, questions, form_name=None, help_texts=None, widget=None, use_likert_scale=True,
                          make_label_tag=False, **kwargs):
    """
    Generate a table with Likert scales between 1 and `len(labels)` in each row for questions supplied with
    `questions` as list of tuples (field name, field label).
    Optionally provide `help_texts` which is a list of help texts for each question (hence must be of same length
    as `questions`.
    If `make_label_tag` is True, then each label is surrounded by a <label>...</label> tag, otherwise it's not.
    Optionally set `widget` (default is `RadioSelect`).
    """
    if not help_texts:
        help_texts = [''] * len(questions)

    if not widget:
        widget = widgets.RadioSelect

    if len(help_texts) != len(questions):
        raise ValueError('Number of questions must be equal to number of help texts.')

    if use_likert_scale:
        field_generator = generate_likert_field(labels, widget=widget)
        header_labels = labels
    else:
        field_generator = partial(models.StringField, choices=labels, widget=widget or widgets.RadioSelectHorizontal)
        header_labels = [t[1] for t in labels]

    fields = []
    for (field_name, field_label), help_text in zip(questions, help_texts):
        fields.append((field_name, {
            'help_text': help_text,
            'label': field_label,
            'make_label_tag': make_label_tag,
            'field': field_generator(),
        }))

    form_def = {'form_name': form_name, 'fields': fields, 'render_type': 'table', 'header_labels': header_labels}
    form_def.update(dict(**kwargs))

    return form_def


def create_player_model_for_survey(module, survey_definitions, other_fields=None):
    """
    Dynamically create a player model in module <module> with a survey definitions and a base player class.
    Parameter survey_definitions is a list, where each list item is a survey definition for a single page.
    Each survey definition for a single page consists of list of field name, question definition tuples.
    Each question definition has a "field" (oTree model field class) and a "text" (field label).

    Returns the dynamically created player model with the respective fields (class attributes).
    """
    if not isinstance(survey_definitions, tuple):
        raise ValueError('`survey_definitions` must be a tuple')

    if other_fields is None:
        other_fields = {}
    else:
        if not isinstance(other_fields, dict):
            raise ValueError('`other_fields` must be a dict with field name to field object mapping')

    model_attrs = {
        '__module__': module,
        '_survey_defs': survey_definitions,
    }

    # collect fields
    def add_field(field_name, qdef):
        if field_name in model_attrs:
            raise ValueError('duplicate field name: `%s`' % field_name)
        model_attrs[field_name] = qdef['field']

    for survey_page in survey_definitions:
        for fielddef in survey_page['survey_fields']:
            if isinstance(fielddef, dict):
                for field_name, qdef in fielddef['fields']:
                    add_field(field_name, qdef)
            else:
                add_field(*fielddef)

    # add optional fields
    model_attrs.update(other_fields)

    # dynamically create model
    model_cls = type('Player', (BasePlayer, _SurveyModelMixin), model_attrs)

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
    FORM_OPTS_DEFAULT = {
        'render_type': 'standard',
        'form_help_initial': '',
        'form_help_final': '',
        # configuration options for likert tables
        'table_repeat_header_each_n_rows': 0,    # set to integer N > 0 to repeat the table header after every N rows
        'table_row_header_width_pct': 25,    # leftmost column width (table row header) in percent
        'table_cols_equal_width': True,      # adjust form columns so that they have equal width
        'table_rows_equal_height': True,     # adjust form rows so that they have equal height
        'table_rows_alternate': True,        # alternate form rows between "odd" and "even" CSS classes (alternates background colors)
        'table_rows_highlight': True,        # highlight form rows on mouse-over
        'table_rows_randomize': False,       # randomize form rows
        'table_cells_highlight': True,       # highlight form cells on mouse-over
        'table_cells_clickable': True,       # make form cells clickable for selection (otherwise only the small radio buttons can be clicked)
    }
    template_name = 'otreeutils/SurveyPage.html'
    field_labels = {}
    field_help_text = {}
    field_help_text_below = {}
    field_make_label_tag = {}
    field_input_prefix = {}
    field_input_suffix = {}
    field_widget_attrs = {}
    field_condition_javascript = {}
    field_forms = {}
    forms_opts = {}
    form_label_suffix = ':'

    @classmethod
    def setup_survey(cls, player_cls, page_idx):
        """Setup a survey page using model class <player_cls> and survey definitions for page <page_idx>."""
        survey_defs = player_cls.get_survey_definitions()[page_idx]
        cls.form_model = player_cls
        cls.page_title = survey_defs['page_title']
        cls.form_label_suffix = survey_defs.get('form_label_suffix', '')

        cls.field_labels = {}
        cls.field_help_text = {}
        cls.field_help_text_below = {}
        cls.field_input_prefix = {}
        cls.field_input_suffix = {}
        cls.field_widget_attrs = {}
        cls.field_condition_javascript = {}
        cls.field_forms = {}
        cls.forms_opts = {}
        cls.form_fields = []

        def add_field(cls_, form_name, field_name, qdef):
            cls_.field_labels[field_name] = qdef.get('text', qdef.get('label', ''))
            cls_.field_help_text[field_name] = qdef.get('help_text', '')
            cls_.field_help_text_below[field_name] = qdef.get('help_text_below', False)
            cls_.field_make_label_tag[field_name] = qdef.get('make_label_tag', False)
            cls_.field_input_prefix[field_name] = qdef.get('input_prefix', '')
            cls_.field_input_suffix[field_name] = qdef.get('input_suffix', '')
            cls_.field_widget_attrs[field_name] = qdef.get('widget_attrs', {})
            cls_.field_condition_javascript[field_name] = qdef.get('condition_javascript', '')
            cls_.form_fields.append(field_name)
            cls_.field_forms[field_name] = form_name

        form_idx = 0
        form_name = None
        survey_defs_form_opts = {k: v for k, v in survey_defs.items() if k.startswith('form_')}
        for fielddef in survey_defs['survey_fields']:
            form_name_default = 'form%d_%d' % (page_idx, form_idx)

            if isinstance(fielddef, dict):
                form_name = fielddef.get('form_name', None) or form_name_default
                if form_name in cls.forms_opts.keys():
                    raise ValueError('form with name `%s` already exists in survey form options definition' % form_name)
                cls.forms_opts[form_name] = cls.FORM_OPTS_DEFAULT.copy()
                cls.forms_opts[form_name].update({k: v for k, v in fielddef.items()
                                                  if k not in ('fields', 'form_name')})

                for field_name, qdef in fielddef['fields']:
                    add_field(cls, form_name, field_name, qdef)

                form_idx += 1
            else:
                if form_name is None:
                    form_name = form_name_default
                    if form_name in cls.forms_opts.keys():
                        raise ValueError('form with name `%s` already exists in survey form options definition'
                                         % form_name)

                cls.forms_opts[form_name] = cls.FORM_OPTS_DEFAULT.copy()
                cls.forms_opts[form_name].update(survey_defs_form_opts)
                add_field(cls, form_name, *fielddef)

    def get_context_data(self, **kwargs):
        ctx = super(SurveyPage, self).get_context_data(**kwargs)

        form = kwargs['form']
        form.label_suffix = self.form_label_suffix

        survey_forms = OrderedDict()
        for field_name, field in form.fields.items():
            if field_name in self.form_fields:
                form_name = self.field_forms[field_name]

                field.label = self.field_labels[field_name]
                field.help_text = {  # abusing the help text attribute here for arbitrary field options
                    'help_text': self.field_help_text[field_name],
                    'help_text_below': self.field_help_text_below[field_name],
                    'make_label_tag': self.field_make_label_tag[field_name],
                    'input_prefix': self.field_input_prefix[field_name],
                    'input_suffix': self.field_input_suffix[field_name],
                    'condition_javascript': self.field_condition_javascript[field_name],
                }

                field.widget.attrs.update(self.field_widget_attrs[field_name])

                if form_name not in survey_forms:
                    survey_forms[form_name] = {'fields': [], 'form_opts': self.forms_opts.get(form_name, {})}

                survey_forms[form_name]['fields'].append(field_name)

        ctx.update({
            'base_form': form,
            'survey_forms': survey_forms,
        })

        return ctx

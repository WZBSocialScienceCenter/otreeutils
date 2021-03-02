"""
oTree page extensions.

March 2021, Markus Konrad <markus.konrad@wzb.eu>
"""


import settings

from django import forms
from django.utils.translation import ugettext as _

from otree.api import Page, WaitPage

APPS_DEBUG = getattr(settings, 'APPS_DEBUG', False)


class AllGroupsWaitPage(WaitPage):
    """A wait page that waits for all groups to arrive."""
    wait_for_all_groups = True


class ExtendedPage(Page):
    """Base page class with extended functionality."""
    page_title = ''
    custom_name_in_url = None
    timer_warning_text = None
    timeout_warning_seconds = None    # set this to enable a timeout warning -- no form submission, just a warning
    timeout_warning_message = 'Please hurry up, the time is over!'
    debug = APPS_DEBUG
    debug_fill_forms_randomly = False

    def __init__(self, **kwargs):
        super(ExtendedPage, self).__init__(**kwargs)
        from django.conf import settings

        if 'otreeutils' not in settings.INSTALLED_APPS:
            raise RuntimeError('otreeutils is missing from the INSTALLED_APPS list in your oTree settings '
                               'file (settings.py); please refer to '
                               'https://github.com/WZBSocialScienceCenter/otreeutils#installation-and-setup '
                               'for more help')

    @classmethod
    def url_pattern(cls, name_in_url):
        if cls.custom_name_in_url:
            return r'^p/(?P<participant_code>\w+)/{}/{}/(?P<page_index>\d+)/$'.format(
                name_in_url,
                cls.custom_name_in_url,
            )
        else:
            return super(ExtendedPage, cls).url_pattern(name_in_url)

    @classmethod
    def get_url(cls, participant_code, name_in_url, page_index):
        if cls.custom_name_in_url:
            return r'/p/{pcode}/{name_in_url}/{custom_name_in_url}/{page_index}/'.format(
                pcode=participant_code, name_in_url=name_in_url,
                custom_name_in_url=cls.custom_name_in_url, page_index=page_index
            )
        else:
            return super(ExtendedPage, cls).get_url(participant_code, name_in_url, page_index)

    # @classmethod
    # def url_name(cls):
    #     if cls.custom_name_in_url:
    #         return cls.custom_name_in_url.replace('.', '-')
    #     else:
    #         return super().url_name()

    @classmethod
    def has_timeout_warning(cls):
        return cls.timeout_warning_seconds is not None and cls.timeout_warning_seconds > 0

    def get_template_names(self):
        if self.__class__ is ExtendedPage:
            return ['otreeutils/ExtendedPage.html']
        else:
            return super(ExtendedPage, self).get_template_names()

    def get_page_title(self):
        """Override this method for a dynamic page title"""
        return self.page_title

    def get_context_data(self, **kwargs):
        ctx = super(ExtendedPage, self).get_context_data(**kwargs)
        default_timer_warning_text = getattr(self, 'timer_text', _("Time left to complete this page:"))
        ctx.update({
            'page_title': self.get_page_title(),
            'timer_warning_text': self.timer_warning_text or default_timer_warning_text,
            'timeout_warning_seconds': self.timeout_warning_seconds,
            'timeout_warning_message': self.timeout_warning_message,
            'debug': int(self.debug),   # allows to retrieve a debug state in the templates
            'debug_fill_forms_randomly': int(self.debug and self.debug_fill_forms_randomly)
        })

        return ctx


class UnderstandingQuestionsPage(ExtendedPage):
    """
    A page base class to implement understanding questions.
    Displays questions as defined in "questions" list.
    Optionally record the number of unsuccessful attempts for solving the questions.
    """
    default_hint = 'This is wrong. Please reconsider.'
    default_hint_empty = 'Please fill out this answer.'
    questions = []  # define the understanding questions here. add dicts with the following keys: "question", "options", "correct"
    set_correct_answers = True         # useful for skipping pages during development
    debug_fill_forms_randomly = False  # not used -- use set_correct_answers
    template_name = 'otreeutils/UnderstandingQuestionsPage.html'   # reset to None to use your own template that extends this one
    form_field_n_wrong_attempts = None   # optionally record number of wrong attempts in this field (set form_model then, too!)
    form_fields = []   # no need to change this
    form_model = None

    def get_questions(self):
        """Override this method to return a dynamic list of questions"""
        return self.questions

    def get_form_fields(self):
        if self.form_model:
            form_fields = super(UnderstandingQuestionsPage, self).get_form_fields()

            if self.form_field_n_wrong_attempts:  # update form fields
                form_fields.append(self.form_field_n_wrong_attempts)

            return form_fields
        else:
            return None

    def vars_for_template(self):
        """Sets variables for template: Question form and additional data"""
        # create question form
        form = _UnderstandingQuestionsForm()

        # add questions to form
        questions = self.get_questions()
        for q_idx, q_def in enumerate(questions):
            answer_field = forms.ChoiceField(label=q_def['question'],
                                             choices=_choices_for_field(q_def['options']))
            correct_val_field = forms.CharField(initial=q_def['correct'],
                                                widget=forms.HiddenInput)
            hint_field = forms.CharField(initial=q_def.get('hint', self.default_hint),
                                         widget=forms.HiddenInput)
            form.add_field('q_input_%d' % q_idx, answer_field)
            form.add_field('q_correct_%d' % q_idx, correct_val_field)
            form.add_field('q_hint_%d' % q_idx, hint_field)

        # optionally add field with number of wrong attempts
        if self.form_model and self.form_field_n_wrong_attempts:
            form.add_field(self.form_field_n_wrong_attempts, forms.CharField(initial=0, widget=forms.HiddenInput))

        return {
            'questions_form': form,
            'n_questions': len(questions),
            'hint_empty': self.default_hint_empty,
            'form_field_n_wrong_attempts': self.form_field_n_wrong_attempts or '',
            'set_correct_answers': str(self.set_correct_answers and self.debug).lower(),
        }


def _choices_for_field(opts, add_empty=True):
    """Create a list of tuples for choices in a form field."""
    if add_empty:
        choices = [('', '---')]
    else:
        choices = []

    choices.extend([(o, str(o)) for o in opts])

    return choices


class _UnderstandingQuestionsForm(forms.Form):
    def add_field(self, name, field):
        self.fields[name] = field

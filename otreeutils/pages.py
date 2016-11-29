import settings

from django import forms

from otree.api import Page, WaitPage

APPS_DEBUG = getattr(settings, 'APPS_DEBUG', False)
DEBUG_FOR_JS = str(APPS_DEBUG).lower()


class AllGroupsWaitPage(WaitPage):
    wait_for_all_groups = True


class ExtendedPage(Page):
    timeout_warning_seconds = None
    timeout_warning_message = 'Please hurry up, the time is over!'

    @classmethod
    def has_timeout(cls):
        return super(ExtendedPage, cls).has_timeout() \
               or (cls.timeout_warning_seconds is not None and cls.timeout_warning_seconds > 0)

    def get_context_data(self, **kwargs):
        ctx = super(ExtendedPage, self).get_context_data(**kwargs)

        ctx.update({
            'timeout_warning_seconds': self.timeout_warning_seconds,
            'timeout_warning_message': self.timeout_warning_message,
            'debug': DEBUG_FOR_JS,
        })

        return ctx


class UnderstandingQuestionsPage(ExtendedPage):
    page_title = ''
    default_hint = 'This is wrong. Please reconsider.'
    default_hint_empty = 'Please fill out this answer.'
    questions = []
    set_correct_answers = APPS_DEBUG   # useful for skipping pages during development
    template_name = 'otreeutils/UnderstandingQuestionsPage.html'
    form_field_n_wrong_attempts = None
    form_fields = []
    form_model = None

    def get_form_fields(self):
        if self.form_model:
            form_fields = super().get_form_fields()

            if self.form_field_n_wrong_attempts:
                form_fields.append(self.form_field_n_wrong_attempts)

            return form_fields
        else:
            return None

    def vars_for_template(self):
        form = _UnderstandingQuestionsForm()

        for q_idx, q_def in enumerate(self.questions):
            answer_field = forms.ChoiceField(label=q_def['question'],
                                             choices=_choices_for_field(q_def['options']))
            correct_val_field = forms.CharField(initial=q_def['correct'],
                                                widget=forms.HiddenInput)
            hint_field = forms.CharField(initial=q_def.get('hint', self.default_hint),
                                         widget=forms.HiddenInput)
            form.add_field('q_input_%d' % q_idx, answer_field)
            form.add_field('q_correct_%d' % q_idx, correct_val_field)
            form.add_field('q_hint_%d' % q_idx, hint_field)

        if self.form_model and self.form_field_n_wrong_attempts:
            form.add_field(self.form_field_n_wrong_attempts, forms.CharField(initial=0, widget=forms.HiddenInput))

        return {
            'page_title': self.page_title,
            'questions_form': form,
            'n_questions': len(self.questions),
            'hint_empty': self.default_hint_empty,
            'form_field_n_wrong_attempts': self.form_field_n_wrong_attempts or '',
            'set_correct_answers': str(self.set_correct_answers).lower(),
        }


def _choices_for_field(opts, add_empty=True):
    if add_empty:
        choices = [('', '---')]
    else:
        choices = []

    choices.extend([(o, str(o)) for o in opts])

    return choices


class _UnderstandingQuestionsForm(forms.Form):
    def add_field(self, name, field):
        self.fields[name] = field
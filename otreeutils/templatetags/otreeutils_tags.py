from django.template.defaulttags import register


@register.filter
def get_form_field(form, field):
    return form[field]

"""
Custom URLs as explained in https://otree.readthedocs.io/en/latest/misc/django.html#adding-custom-pages-urls

This adds an URL for exporting all data (including the custom data models) as JSON.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

from django.conf.urls import url
from otree.urls import urlpatterns

from . import views


# define patterns with name, URL pattern and view class
patterns_conf = {
    'SessionData': (r"^SessionData/(?P<code>[a-z0-9]+)/$", views.SessionDataExtension),
    'ExportApp': (r"^ExportApp/(?P<app_name>[\w.]+)/$", views.ExportAppExtension),
    'ExportIndex': (r"^export/$", views.ExportIndexExtension),
}

# exclude oTree's original patterns with the same names
urlpatterns = [pttrn for pttrn in urlpatterns if pttrn.name not in patterns_conf.keys()]

# add the patterns
for name, (pttrn, viewclass) in patterns_conf.items():
    urlpatterns.append(url(pttrn, viewclass.as_view(), name=name))

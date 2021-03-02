"""
Custom URLs that add hooks to session data monitor extensions.

Feb. 2021, Markus Konrad <markus.konrad@wzb.eu>
"""

from django.conf.urls import url
from otree.urls import urlpatterns

from . import views


# define patterns with name, URL pattern and view class
patterns_conf = {
    'SessionData': (r"^SessionData/(?P<code>[a-z0-9]+)/$", views.SessionDataExtension),
    'SessionDataAjax': (r"^session_data/(?P<code>[a-z0-9]+)/$", views.SessionDataAjaxExtension),
}

# exclude oTree's original patterns with the same names
urlpatterns = [pttrn for pttrn in urlpatterns if pttrn.name not in patterns_conf.keys()]

# add the patterns
for name, (pttrn, viewclass) in patterns_conf.items():
    urlpatterns.append(url(pttrn, viewclass.as_view(), name=name))

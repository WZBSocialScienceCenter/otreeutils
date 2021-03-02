"""
oTree extension to write own shell scripts.

This is uses a lot of code copied from the "otree_startup" package, which is part of "otree-core" (see
https://github.com/oTree-org/otree-core).

March 2021, Markus Konrad <markus.konrad@wzb.eu>
"""

import os
import sys
import logging
import json

# code to setup the oTree/Django environment (locate and load settings module, setup django)

from otree_startup import configure_settings, do_django_setup


logger = logging.getLogger(__name__)

if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
DJANGO_SETTINGS_MODULE = os.environ['DJANGO_SETTINGS_MODULE']

configure_settings(DJANGO_SETTINGS_MODULE)
do_django_setup()


from .admin_extensions.views import get_hierarchical_data_for_apps


def save_data_as_json_file(data, path, **kwargs):
    from django.core.serializers.json import DjangoJSONEncoder

    with open(path, 'w') as f:
        json.dump(data, f, cls=DjangoJSONEncoder, **kwargs)

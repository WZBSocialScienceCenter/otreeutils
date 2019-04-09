"""
oTree extension to write own shell scripts.

This is uses a lot of code copied from the "otree_startup" package, which is part of "otree-core" (see
https://github.com/oTree-org/otree-core).

March 2019, Markus Konrad <markus.konrad@wzb.eu>
"""

import os
import sys
import logging
import json
from collections import OrderedDict

# code to setup the oTree/Django environment (locate and load settings module, setup django)

from otree_startup import configure_settings, ImportSettingsError, do_django_setup


logger = logging.getLogger(__name__)

if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
DJANGO_SETTINGS_MODULE = os.environ['DJANGO_SETTINGS_MODULE']

try:
    configure_settings(DJANGO_SETTINGS_MODULE)
except ImportSettingsError:
    if os.path.isfile('{}.py'.format(DJANGO_SETTINGS_MODULE)):
        raise
    else:
        msg = (
            "Cannot find oTree settings. "
            "Please 'cd' to your oTree project folder, "
            "which contains a settings.py file."
        )
        logger.warning(msg)

do_django_setup()


from .admin_extensions.views import get_hierarchical_data_for_apps


def save_data_as_json_file(data, path, **kwargs):
    from django.core.serializers.json import DjangoJSONEncoder

    with open(path, 'w') as f:
        json.dump(data, f, cls=DjangoJSONEncoder, **kwargs)

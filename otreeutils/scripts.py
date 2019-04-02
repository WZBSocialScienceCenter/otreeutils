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


def get_hierarchical_data_for_apps(apps):
    """
    Return a hierarchical data structure consisting of nested OrderedDicts for all data collected for apps listed
    in `apps`. The format of the returned data structure is:

    ```
    {
        <session_1_code>: {
            'code': ...,
            'label': ...,
            # more session data
            # ...
            '__apps': {  # list of apps as requested in `apps` argument
                <app_1_name>: [                  # list of subsessions in app 1 played in session 1
                    {
                        'round_number': 1,
                        # more subsession data
                        # ...
                        '__group': [                 # list of groups in subsession 1 of app 1 played in session 1
                            {
                                'id_in_subsession': 1,
                                # more group data
                                # ...
                                '__player': [            # list of players in group 1 in subsession 1 of app 1 played in session 1
                                    {
                                        "id_in_group": 1,
                                        # more player data
                                        # ...
                                        '__participant': {   # reference to participant for this player
                                            "id_in_session": 1,
                                            "code": "5ilq0fad",
                                            # more participant data
                                            # ...
                                        },
                                        '__custom_model': [  # some optional custom model data connected to this player (could also be connected to group or subsession)
                                            # custom model data
                                        ]
                                    }, # more players in this group
                                ]
                            }, # more groups in this session
                        ]
                    }, # more subsessions (rounds) in this app
                ]
            },  # more apps in this session
        },
        <session_2_code>: { # similar to above },
        # ...
    }
    ```
    """
    from .admin_extensions.views import ExportAppExtension

    combined = OrderedDict()

    for app in apps:
        sessions = ExportAppExtension.get_hierarchical_data_for_app(app)

        for sess in sessions:
            sesscode = sess['code']
            if sesscode not in combined.keys():
                combined[sesscode] = OrderedDict([(k, v) for k, v in sess.items() if k != '__subsession'])
                combined[sesscode]['__apps'] = OrderedDict()

            combined[sesscode]['__apps'][app] = sess['__subsession']

    return combined


def save_data_as_json_file(data, path, **kwargs):
    from django.core.serializers.json import DjangoJSONEncoder

    with open(path, 'w') as f:
        json.dump(data, f, cls=DjangoJSONEncoder, **kwargs)

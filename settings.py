import importlib.util
from os import environ

# CHANGE THIS IN YOUR OWN EXPERIMENTS
SECRET_KEY = '7d+8)6q47+xw77=%l7%79en-vpor5tg7f$=d-21+^#js*nwrum'

# List of example experiments

SESSION_CONFIGS = [
    {
        'name': 'otreeutils_example1',
        'display_name': 'otreeutils example 1 (Understanding questions, timeout warnings, custom page URLs)',
        'num_demo_participants': 1,   # doesn't matter
        'app_sequence': ['otreeutils_example1'],
    },
    {
        'name': 'otreeutils_example2',
        'display_name': 'otreeutils example 2 (Surveys)',
        'num_demo_participants': 4,  # every second player gets treatment 2
        'app_sequence': ['otreeutils_example2'],
    },
    {   # the following experiments are only available when you install otreeutils as `pip install otreeutils[admin]`
        'name': 'otreeutils_example3_market',
        'display_name': 'otreeutils example 3 (Custom data models: Market)',
        'num_demo_participants': 3,  # at least two
        'app_sequence': ['otreeutils_example3_market'],
    },
    {
        'name': 'otreeutils_example4_market_and_survey',
        'display_name': 'otreeutils example 4 (Market and survey)',
        'num_demo_participants': 3,  # at least two
        'app_sequence': ['otreeutils_example3_market', 'otreeutils_example2'],
    }
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ROOMS = [
    dict(
        name='econ101',
        display_name='Econ 101 class',
        participant_label_file='_rooms/econ101.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
otreeutils examples
"""


# the environment variable OTREE_PRODUCTION controls whether Django runs in
# DEBUG mode. If OTREE_PRODUCTION==1, then DEBUG=False

if environ.get('OTREE_PRODUCTION') not in {None, '', '0'}:
    DEBUG = False
    APPS_DEBUG = False
else:
    DEBUG = True
    APPS_DEBUG = True   # will set a debug variable to true in the template files

# if an app is included in SESSION_CONFIGS, you don't need to list it here
INSTALLED_APPS = [
    'otree',
    'otreeutils'    # this is important -- otherwise otreeutils' templates and static files won't be accessible
]


# custom URL and WebSockets configuration
# this is important -- otherwise otreeutils' admin extensions won't be activated

if importlib.util.find_spec('pandas'):
    ROOT_URLCONF = 'otreeutils_example3_market.urls'
    CHANNEL_ROUTING = 'otreeutils_example3_market.routing.channel_routing'

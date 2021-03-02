"""
otreeutils setuptools based setup module
"""

import os

from setuptools import setup, find_packages

__title__ = 'otreeutils'
__version__ = '0.10.0'
__author__ = 'Markus Konrad'
__license__ = 'Apache License 2.0'

here = os.path.abspath(os.path.dirname(__file__))

GITHUB_URL = 'https://github.com/WZBSocialScienceCenter/otreeutils'

DEPS_BASE = ['otree>=3.3,<4']

DEPS_EXTRA = {
    'admin': ['pandas>=1.0,<1.3'],
    'develop': ['tox>=3.21.0,<3.22', 'twine>=3.1.0,<3.2']
}

DEPS_EXTRA['all'] = []
for k, deps in DEPS_EXTRA.items():
    if k != 'all':
        DEPS_EXTRA['all'].extend(deps)


# Get the long description from the README file
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name=__title__,
    version=__version__,
    description='Facilitate oTree experiment implementation with extensions for custom data models, surveys, understanding questions, timeout warnings and more.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url=GITHUB_URL,
    project_urls={
        'Bug Reports': GITHUB_URL + '/issues',
        'Source': GITHUB_URL,
    },

    author=__author__,
    author_email='markus.konrad@wzb.eu',

    license=__license__,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',

        'Environment :: Web Environment',

        'Framework :: Django',

        'License :: OSI Approved :: Apache Software License',

        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],

    keywords='otree experiments social science finance economics development',

    packages=find_packages(exclude=['otreeutils_example*']),
    include_package_data=True,

    install_requires=DEPS_BASE,
    extras_require=DEPS_EXTRA
)

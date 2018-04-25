"""
otreeutils setuptools based setup module
"""

import os

from setuptools import setup

import otreeutils


GITHUB_URL = 'https://github.com/WZBSocialScienceCenter/tmtoolkit'

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(here, 'README.md')) as f:
    long_description = f.read()


setup(
    name=otreeutils.__title__,
    version=otreeutils.__version__,

    long_description=long_description,
    long_description_content_type='text/markdown',
    url=GITHUB_URL,
    project_urls={
        'Bug Reports': GITHUB_URL + '/issues',
        'Source': GITHUB_URL,
    },

    author=otreeutils.__author__,
    author_email='markus.konrad@wzb.eu',

    license=otreeutils.__license__,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',

        'Environment :: Web Environment',

        'Framework :: Django',
        'Framework :: Django :: 1.8',

        'License :: OSI Approved :: Apache Software License',

        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],

    keywords='otree experiments social science finance economics development',

    packages=['otreeutils'],
    include_package_data=True,

    install_requires=['otree-core'],
)

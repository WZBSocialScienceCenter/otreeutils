"""
otreeutils setuptools based setup module
"""

from setuptools import setup


setup(
    name='otreeutils',
    version='0.1.1',

    description='A package with common oTree utilities',
    long_description="""This repository contains the package otreeutils. It features a set of common helper / utility
functions and classes often needed when developing experiments with oTree.""",

    url='https://github.com/WZBSocialScienceCenter/otreeutils',

    author='Markus Konrad',
    author_email='markus.konrad@wzb.eu',

    license='Apache 2.0',

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

    keywords='otree experiments social science development',

    packages=['otreeutils'],
    include_package_data=True,

    install_requires=['otree-core'],
)

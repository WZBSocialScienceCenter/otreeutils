# Changes


## v0.7.0 – 2019-??-??

* corrections for use of survey module in several apps
* option to specify form label suffix
* alternating row colors and hover for likert table


## v0.6.0 – 2019-02-28

* added new features to `otreeutils.surveys`:
    * `generate_likert_field` to easily create Likert scale fields from given labels
    * `generate_likert_table` to easily create a table of Likert scale inputs
    * ability to add `help_text` for each question field as HTML
    * ability to split questions into several forms
    * easier survey forms styling via CSS due to more structured HTML output  

## v0.5.1 – 2019-02-18

* fixed problem with missing sub-package `otreeutils.admin_extensions`

## v0.5.0 – 2018-10-02

* modified admin extensions to use pandas for data joins, removes limitation in live data viewer
* fixed issue with tests for example 1 and 2
* added example 3: market with custom data models

## v0.4.1 – 2018-09-28

* fixed template error in `admin/SessionDataExtension.html`

## v0.4.0 – 2018-09-27

* added admin extensions:
    * live session data with custom data models
    * app data export with custom data models in CSV, Excel and JSON formats
* dropped support for oTree v1.x
* fixed some minor compat. issues with latest oTree version

## v0.3.0 – 2018-04-25

* made compatible with oTree v2.0
* updated setuptools configuration
* added this changelog

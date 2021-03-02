# Changes


## v0.10.0 (for oTree v3.3.x) - upcoming

* added compatibility for oTree v3.3.x -- dropped support for older oTree versions
    * better integration in session data monitor
    * provide default `custom_export()` function for apps with linked custom data models
* `surveys` module:
    * made `generate_likert_field()` more flexible with parameters `field`, `choices_values` and `html_labels`
    * added option to pass parameters to `generate_likert_field()` for `generate_likert_table()`
* adapted examples to show new features
* fixed bug in `otreeutils_example3_market` example experiment, where amount of fruit in offers was not decreased after sales
* check if otreeutils is listed in `INSTALLED_APPS`
* make dependency to pandas optional (only installed with `admin_extensions` option)
* integrated `tox` for testing

## v0.9.2 (for oTree v2.1.x) – 2019-09-23

* `surveys` module:
    * added missing "change" triggers when checkboxes are selected in Likert table via clicking/touching the table cell
    * added a check to require the `survey_definitions` argument to be a tuple in `create_player_model_for_survey`

## v0.9.1 (for oTree v2.1.x) – 2019-06-13

* `surveys` module:
    * added option `table_repeat_header_each_n_rows` to `generate_likert_table()`
    * fixed problem where form options like `form_help_initial` were ignored

## v0.9.0 (for oTree v2.1.x) – 2019-05-28

* `surveys` module:
    * add several options to `generate_likert_table()` to adjust display and behavior of Likert tables
    * allow non-survey form fields on survey pages

## v0.8.0 – 2019-05-15

* pages derived from `ExtendedPage` may set `debug_fill_forms_randomly` to `True` so that when visiting the page, its form is filled in with random values (helpful during developement process)
* `surveys` module: all columns in a Likert table now have the same width. The width of row header (first column) is 25% by default and can be changed via `table_row_header_width_pct`

## v0.7.1 – 2019-05-07

* `surveys` module: field labels can now contain HTML (HTML is not escaped and will be rendered)

## v0.7.0 – 2019-04-09

* added class attribute `custom_name_in_url` for `ExtendedPage`: allows to set a custom URL for a page (instead of default class name)
* several improvements in the `surveys` module:
    * added `other_fields` parameter to `create_player_model_for_survey` to allow for additional (non-survey) fields
    * corrections when using surveys module in several apps on the same server instance
    * added option to specify conditional field display via JavaScript
    * added option to specify form label suffix
    * added option to specify field widget HTML attributes
    * added option to use custom choices (`use_likert_scale=False`) in `generate_likert_table`
    * alternating row colors and hover for likert table
* added new `scripts` module:
    * properly set up your command-line scripts to work with oTree by importing the module
    * export of hierarchical data structures from collected data 


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

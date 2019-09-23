# otreeutils

September 2019, Markus Konrad <markus.konrad@wzb.eu> / [Berlin Social Science Center](https://wzb.eu)

## A package with common oTree utilities

This repository contains the package `otreeutils`. It features a set of common helper / utility functions and classes often needed when developing experiments with [oTree](http://www.otree.org/). So far, this covers the following use cases:

* Extensions to oTree's admin interface for [using custom data models](https://datascience.blog.wzb.eu/2016/10/31/using-custom-data-models-in-otree/), which include:
    * Live session data view shows data from custom models
    * Export page allows download of complete data with data from custom models
    * Export page allows download in nested JSON format
* Displaying and validating understanding questions
* Easier creation of surveys:
    * define all survey questions in a single data structure, let `otreeutils` create the required `Player` fields
    * create a table of Likert scale inputs ("Likert matrix")
    * create single Likert scale fields from given labels
    * easy survey forms styling via CSS due to cleanly structured HTML output
    * make survey forms with conditional inputs  
* Displaying warnings to participants when a timeout occurs on a page (no automatic form submission after timeout)
* More convenient development process by optional automatic fill-in of forms (saves you from clicking through many inputs during development)  
* Setting custom URLs for pages (instead of default: the page's class name)

**Compatibility note:** This package is compatible with oTree v2.x. (It has been tested with oTree v2.1.36 but any other 2.x version should work. If you want to use this package with oTree v1.x, you should use otreeutils v0.3.1, which is the last version to support oTree 1.) 

The package is [available on PyPI](https://pypi.org/project/otreeutils/) and can be installed
via `pip install otreeutils`.

## Citation

If you used *otreeutils* in your published research, please cite it as follows:

[Konrad, M. (2018). oTree: Implementing experiments with dynamically determined data quantity. *Journal of Behavioral and Experimental Finance.*](https://doi.org/10.1016/j.jbef.2018.10.006)


## Examples

The repository contains three example apps which show the respective features and how they can be used in own experiments:

* `otreeutils_example1` -- Understanding questions and timeout warnings
* `otreeutils_example2` -- Surveys
* `otreeutils_example3_market` -- Market: An example showing custom data models to collect a dynamically determined data quantity. Shows how otreeutils' admin extensions allow live data view and data export for these requirements. Companion code for [Konrad 2018](https://doi.org/10.1016/j.jbef.2018.10.006). See [its dedicated README page](https://github.com/WZBSocialScienceCenter/otreeutils/tree/master/otreeutils_example3_market). 

## Limitations

The admin interface extensions have still a limitation: Data export with all data from custom models is only possible with per app download option, not with the "all apps" option.

## Requirements

This package requires oTree v2.x and [pandas](http://pandas.pydata.org/). The requirements will be installed along with otreeutils when using `pip` (see below). 

## Installation and setup

In order to use otreeutils in your experiment implementation, you only need to do the following things:

1. Either install the package from [PyPI](https://pypi.python.org/pypi/otreeutils) via
   *pip* (`pip install otreeutils`) or download/clone this github repository and copy
   the `otreeutils` folder to your oTree experiment directory.
2. Edit your `settings.py` so that you add "otreeutils" to your `INSTALLED_APPS` list. **Don't forget this, otherwise the required templates and static files cannot be loaded correctly!**


## API overview

It's best to have a look at the (documented) examples to see how to use the API.

### `otreeutils.pages` module

#### `ExtendedPage` class

A common page extension to oTree's default `Page` class.
 All other page classes in `otreeutils` extend this class. Allows to define a custom page URL via `custom_name_in_url`, timeout warnings, a page title and provides a template variable `debug` with which you can toggle debug code in your templates / JavaScript parts.

The template variable `debug` (integer – 0 or 1) is toggled using an additional `APPS_DEBUG` variable in `settings.py`. See the `settings.py` of this repository. This is quite useful for example in order to fill in the correct questions on a page with understanding questions automatically in a debug session (so that it is easier to click through the pages).

There is also a page variable `debug_fill_forms_randomly`, which can be set for any page derived from the `ExtendedPage` class (i.e. also for survey pages -- see below). If you set this variable to `True`, then all form inputs on the page are automatically filled in with random values once you visit the page. This happens when you run the experiment in "debug mode", i.e. when `APPS_DEBUG` is set to `True`. By default, `debug_fill_forms_randomly` is set to `False`. You can enable this feature for a given page like this:

```python
from otreeutils.pages import ExtendedPage

class MyPage(ExtendedPage):
    debug_fill_forms_randomly = True
```

This saves time when you click through an experiment with many complex forms.

#### `UnderstandingQuestionsPage` class

Base class to implement understanding questions. A participant must complete all questions in order to proceed. You can display hints. Use it as follows:

```python
from otreeutils.pages import UnderstandingQuestionsPage

class SomeUnderstandingQuestions(UnderstandingQuestionsPage):
    page_title = 'Set a page title'
    questions = [
        {
            'question': 'What is π?',
            'options': [1.2345, 3.14159],
            'correct': 3.14159,
            'hint': 'You can have a look at Wikipedia!'   # this is optional
        },
        # ...
    ]
```

By default, the performance of the participant is not recorded, but you can optionally provide a `form_model` and set a field in `form_field_n_wrong_attempts` which defines in which field the number of wrong attempts is written.

If you set `APPS_DEBUG` to `True`, the correct answers will already be filled in order to skip swiftly through pages during development.


### `otreeutils.surveys` module

#### `create_player_model_for_survey` function

This function allows to dynamically create a `Player` model class for a survey. It can be used as follows in `models.py`.

At first you define your questions per page in a survey definitions data structure, for example like this:

```python
from otreeutils.surveys import create_player_model_for_survey


GENDER_CHOICES = (
    ('female', 'Female'),
    ('male', 'Male'),
    ('no_answer', 'Prefer not to answer'),
)


SURVEY_DEFINITIONS = (
    {
        'page_title': 'Survey Questions - Page 1',
        'survey_fields': [
            ('q1_a', {   # field name (which will also end up in your "Player" class and hence in your output data)
                'text': 'How old are you?',   # survey question
                'field': models.PositiveIntegerField(min=18, max=100),  # the same as in normal oTree model field definitions
            }),
            ('q1_b', {
                'text': 'Please tell us your gender.',
                'field': models.CharField(choices=GENDER_CHOICES),
            }),
            # ... more questions
        ]
    },
    # ... more pages
)
```

Now you dynamically create the `Player` class by passing the name of the module for which it will be created (should be the `models` module of your app) and the survey definitions:

```python
Player = create_player_model_for_survey('otreeutils_example2.models', SURVEY_DEFINITIONS)
```

The attributes (model fields, etc.) will be automatically created. When you run `otree resetdb`, you will see that the fields `q1_a`, `q1_b`, etc. will be generated in the database.

You may also add extra (non-survey) fields to your `Player` class, by passing a dict to the optional `other_fields` parameter:

```python
Player = create_player_model_for_survey('otreeutils_example2.models', SURVEY_DEFINITIONS, other_fields={
    'treatment': models.IntegerField()
})
```

##### Likert score inputs via `generate_likert_field` and `generate_likert_table` functions

The function `generate_likert_field` allows you to easily generate fields for a given Likert scale and can be used inside a survey definitions data structure:

```python
from otreeutils.surveys import generate_likert_field

likert_5_labels = (
    'Strongly disagree',            # value: 1
    'Disagree',                     # value: 2
    'Neither agree nor disagree',   # ...
    'Agree',
    'Strongly agree'                  # value: 5
)

likert_5point_field = generate_likert_field(likert_5_labels)
```

The object `likert_5point_field` is now a *function* to generate new fields of the specified Likert scale:

```python
# ...

SURVEY_DEFINITIONS = (
    {
        'page_title': 'A Likert 5-point scale example',
        'survey_fields': [
            ('q_otree_surveys', {  # most of the time, you'd add a "help_text" for a Likert scale question. You can use HTML:
                'help_text': """
                    <p>Consider this quote:</p>
                    <blockquote>
                        "oTree is great to make surveys, too."
                    </blockquote>
                    <p>What do you think?</p>
                """,
                'field': likert_5point_field(),   # don't forget the parentheses at the end!
            }),
            ('q_just_likert', {
                 'label': 'Another Likert scale input:',  # optional, no HTML
                 'field': likert_5point_field(),  # don't forget the parentheses at the end!
            }),
        ]
    },
    # ... more pages
)
```

The function `generate_likert_table` allows you to easily generate a table of Likert scale inputs like a matrix with the Likert scale increments in the columns and your questions in the rows:

```python
# ...

SURVEY_DEFINITIONS = (
    {
        'page_title': 'A Likert scale table example',
        'survey_fields': [
            # create a table of Likert scale choices
            # we use the same 5-point scale a before and specify four rows for the table,
            # each with a tuple (field name, label)
            generate_likert_table(likert_5_labels,
                                  [
                                      ('q_pizza_tasty', 'Tasty'),
                                      ('q_pizza_spicy', 'Spicy'),
                                      ('q_pizza_cold', 'Too cold'),
                                      ('q_pizza_satiable', 'Satiable'),
                                  ],
                                  form_help_initial='<p>How was your latest Pizza?</p>',  # HTML to be placed on top of form
                                  form_help_final='<p>Thank you!</p>'                     # HTML to be placed below form
            )
        ]
    },
    # ... more pages
)
```

There are several additional parameters that you can pass to `generate_likert_table()` which will control the display and behavior of the table:

- `table_repeat_header_each_n_rows=<integer>`: set to integer N > 0 to repeat the table header after every N rows
- `table_cols_equal_width=<True/False>`: adjust form columns so that they have equal width
- `table_row_header_width_pct=<number>`: if form columns should have equal width, this specifies the width of the first column (the table row header) in percent (default: 25)
- `table_rows_equal_height=<True/False>`: adjust form rows so that they have equal height
- `table_rows_alternate=<True/False>`: alternate form rows between "odd" and "even" CSS classes (alternates background colors)
- `table_rows_randomize=<True/False>`: randomize form rows
- `table_rows_highlight=<True/False>`: highlight form rows on mouse-over
- `table_cells_highlight=<True/False>`: highlight form cells on mouse-over
- `table_cells_clickable=<True/False>`: make form cells clickable for selection (otherwise only the small radio buttons can be clicked)

#### More options for surveys

To implement advanced features such as conditional input display, have a look at the example app `otreeutils_example2`.

#### `SurveyPage` class

You can then create the survey pages which will contain the questions for the respective pages as defined before in `SURVEY_DEFINITIONS`:
 
**Please note:** Unfortunately, it was not possible for me to create the page classes dynamically, so you have to define them manually here. At least the overhead is minimal, because you don't need to define any additional attributes. However, this way you *can* also specify additional attributes, set a custom template, etc.
 
```python
# (in pages.py)

from otreeutils.surveys import SurveyPage, setup_survey_pages


class SurveyPage1(SurveyPage):
    pass
class SurveyPage2(SurveyPage):
    pass
# more pages ...

# Create a list of survey pages.
# The order is important! The survey questions are taken in the same order
# from the SURVEY_DEFINITIONS in models.py

survey_pages = [
    SurveyPage1,
    SurveyPage2,
    # more pages ...
]
```

Since each `SurveyPage` is derived from the `ExtendedPage` class, you can also enable the automatic fill-in feature. This means that all form inputs on the page are automatically filled in with random values once you visit the page. That happens when you run the experiment in "debug mode", i.e. when `APPS_DEBUG` is set to `True`. By default, `debug_fill_forms_randomly` is set to `False`. You can enable this feature for a given survey page like this:

```python
class SurveyPage3(SurveyPage):
    debug_fill_forms_randomly = True
```

This saves time when you click through an experiment with many survey fields.

#### `setup_survey_pages` function

Now all survey pages need to be set up. The `Player` class will be passed to all survey pages and the questions for each page will be set according to their order. 

```python
# Common setup for all pages (will set the questions per page)
setup_survey_pages(models.Player, survey_pages)
```

Finally, we can set the `page_sequence` in order to use our survey pages:

```python
page_sequence = [
    SurveyIntro,  # define some pages that come before the survey
    # ...
]

# add the survey pages to the page sequence list
page_sequence.extend(survey_pages)

# we could add more pages after the survey here
# ...
```

**Have a look into the example implementations provided as `otreeutils_example1` (understanding questions, simple page extensions), `otreeutils_example2` (surveys) and `otreeutils_example3_market` (custom data models).**  


### `otreeutils.scripts` module

This module allows creating scripts that interface with oTree from the command line. Importing `otreeutils.scripts` makes sure that everything is correctly set up and the settings are loaded. An example might be a script which exports data from the current sessions for specific apps as JSON file:

```python
import sys

from otreeutils import scripts   # this is the most import line and must be included at the beginning


if len(sys.argv) != 2:
    print('call this script with a single argument: python %s <output.json>' % sys.argv[0])
    exit(1)

output_file = sys.argv[1]

apps = ['intro',
        'my_app',
        'outro']

print('loading data...')

# get the data as hierarchical data structure. this is esp. useful if you use
# custom data models
combined = scripts.get_hierarchical_data_for_apps(apps)

print('writing data to file', output_file)

scripts.save_data_as_json_file(combined, output_file, indent=2)

print('done.')
```

### Custom data models and admin extensions

If you implement custom data models and want to use otreeutils' admin extensions you additionally need to follow these steps:

#### 1. Add configuration class to custom models

For each of the custom models that you want to include in the live data view or extended data export, you have to define a subclass called `CustomModelConf` like this:

```python
from otree.db.models import Model, ForeignKey   # import base Model class and ForeignKey

# ...

class FruitOffer(Model):
    amount = models.IntegerField(label='Amount', min=0, initial=0)

    # ... more fields here ...

    seller = ForeignKey(Player)


    class CustomModelConf:
        """
        Configuration for otreeutils admin extensions.
        """
        data_view = {    # define this attribute if you want to include this model in the live data view
            'exclude_fields': ['seller'],
            'link_with': 'seller'
        }
        export_data = {  # define this attribute if you want to include this model in the data export
            'exclude_fields': ['seller_id'],
            'link_with': 'seller'
        }

``` 

#### 2. Add a custom urls module

In your experiment app, add a file `urls.py` and simply include the custom URL patters from otreeutils as follows:

```python
from otreeutils.admin_extensions.urls import urlpatterns

# add more custom URL rules here if necessary
# ...
```

#### 3. Add a custom routing module

In your experiment app, add a file `routing.py` and simply include the custom channel routing patters from otreeutils as follows:

```python
from otreeutils.admin_extensions.routing import channel_routing

# add more custom channel routing rules here if necessary
# ...
```

#### 4. Update `settings.py` to load the custom URLs and channel routes

Add these lines to your `settings.py`:

```python
ROOT_URLCONF = '<APP_PACKAGE>.urls'
CHANNEL_ROUTING = '<APP_PACKAGE>.routing.channel_routing'
```

Instead of `<APP_PACKAGE>` write your app's package name (e.g. "market" if your app is named "market").

**And don't forget to edit your settings.py so that you add "otreeutils" to your INSTALLED_APPS list!**

That's it! When you visit the admin pages, they won't really look different, however, the live data view will now support your custom models and in the data export view you can download the data *including* the custom models' data, **when you select the download per app. So far, the "all-apps" download option will not include the custom models' data.**

See also the [market example experiment](https://github.com/WZBSocialScienceCenter/otree_example_market) that uses custom data models.

## License

Apache License 2.0. See LICENSE file.

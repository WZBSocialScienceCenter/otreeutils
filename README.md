# otreeutils

November 2016, Markus Konrad <markus.konrad@wzb.eu> / [Berlin Social Science Center](https://wzb.eu)

## A package with common oTree utilities

This repository contains the package `otreeutils`. It features a set of common helper / utility functions and classes often needed when developing experiments with [oTree](http://www.otree.org/). So far, this covers the following use cases:

* Displaying and validating understanding questions
* Easier creation of surveys
* Displaying warnings to participants when a timeout occurs on a page (no automatic form submission after timeout)

**Compatibility note:** This package has been tested with oTree v1.0.12 and v1.1.8 but should work with at least any oTree 1.x version. 

This package is [available on PyPI](https://pypi.python.org/pypi/otreeutils) and can be installed
via `pip install otreeutils`.

## Examples

The repository contains two example apps which show the respective features and how they can be used in own experiments:

* `otreeutils_example1` -- Understanding questions and timeout warnings
* `otreeutils_example2` -- Surveys

## Installation and setup

In order to use *otreeutils* in your experiment implementation, you only need to do two things:

1. Either install the package from [PyPI](https://pypi.python.org/pypi/otreeutils) via
   *pip* (`pip install otreeutils`) or download/clone this github repository and copy
   the `otreeutils` folder to your oTree experiment directory
2. Edit your `settings.py` so that you add "otreeutils" to your `INSTALLED_APPS` list

## API overview

It's best to have a look at the (documented) examples to see how to use the API.

### `otreeutils.pages` module

#### `ExtendedPage` class

A common page extension to oTree's default `Page` class.
 All other page classes in `otreeutils` extend this class. Allows to define timeout warnings, a page title and provides a template variable `debug` with which you can toggle debug code in your templates / JavaScript parts.

The template variable `debug` is toggled using an additional `APPS_DEBUG` variable in `settings.py`. See the `settings.py` of this repository. This is quite useful for example in order to fill in the correct questions on a page with understanding questions automatically in a debug session (so that it is easier to click through the pages). 

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

At first you define your questions per page, for example like this:

```python
from otreeutils.surveys import create_player_model_for_survey


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
```

Now you dynamically create the `Player` class by passing the name of the module for which it will be created (should be the `models` module of your app) and the survey definitions:

```python
Player = create_player_model_for_survey('otreeutils_example2.models', SURVEY_DEFINITIONS)
```

The attributes (model fields, etc.) will be automatically created. When you run `otree resetdb`, you will see that the fields `q1_a`, `q1_b`, etc. will be generated in the database.

#### `SurveyPage` class

You can then create the survey pages which will contain the questions for the respective pages as defined before in `SURVEY_DEFINITIONS`:
 
**Please note:** Unfortunately, it was not possible for me to create the page classes dynamically, so you have to define them manually here. At least the overhead is minimal, because you don't need to define any additional attributes.
 
```python
# (in views.py)

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

## License

Apache License 2.0. See LICENSE file.

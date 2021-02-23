"""
Example script to output *all* data for given list of apps as hierarchical data structure in JSON format.

Feb. 2020, Markus Konrad <markus.konrad@wzb.eu>
"""

import sys

from otreeutils import scripts   # this is the most import line and must be included at the beginning


if len(sys.argv) != 2:
    print('call this script with a single argument: python %s <output.json>' % sys.argv[0])
    exit(1)

output_file = sys.argv[1]

apps = ['otreeutils_example1',
        'otreeutils_example2',
        'otreeutils_example3_market']

print('loading data...')

# get the data as hierarchical data structure. this is esp. useful if you use
# custom data models
combined = scripts.get_hierarchical_data_for_apps(apps)

print('writing data to file', output_file)

scripts.save_data_as_json_file(combined, output_file, indent=2)

print('done.')

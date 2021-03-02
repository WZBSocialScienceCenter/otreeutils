__title__ = 'otreeutils'
__version__ = '0.10.0'
__author__ = 'Markus Konrad'
__license__ = 'Apache License 2.0'

try:
    import pandas as pd
    from . import admin_extensions   # only import admin_extensions when pandas is available
except ImportError: pass

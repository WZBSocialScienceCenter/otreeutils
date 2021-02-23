"""
Admin backend extensions provided by otreeutils.

Feb. 2021, Markus Konrad <markus.konrad@wzb.eu>
"""


def custom_export(players):
    """
    Default function for custom data export with linked custom models.
    """
    from .views import get_rows_for_custom_export

    if not players:
        yield []
    else:
        app_name = players[0]._meta.app_config.name

        yield from get_rows_for_custom_export(app_name)

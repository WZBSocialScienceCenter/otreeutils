

def custom_export(players):
    from .views import get_rows_for_custom_export

    if not players:
        yield []
    else:
        app_name = players[0]._meta.app_config.name

        yield from get_rows_for_custom_export(app_name)

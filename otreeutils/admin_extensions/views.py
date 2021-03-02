"""
Custom admin views.

Override existing oTree admin views for custom data live view and custom data export.

Feb. 2021, Markus Konrad <markus.konrad@wzb.eu>
"""

import json
from collections import OrderedDict, defaultdict

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from otree.views.admin import SessionData, SessionDataAjax
from otree import export
from otree.common import get_models_module
from otree.db.models import Model
from otree.models.participant import Participant
from otree.models.session import Session
import pandas as pd
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 180)


#%% helper functions


def _rows_per_key_from_queryset(qs, key):
    """Make a dict with `row[key] -> [rows with same key]` mapping (rows is a list)."""
    res = defaultdict(list)

    for row in qs.values():
        res[row[key]].append(row)

    return res


def _set_of_ids_from_rows_per_key(rows, idfield):
    return set(x[idfield] for r in rows.values() for x in r)


def _odict_from_row(row, columns, is_obj=False):
    """Create an OrderedDict from a dict `row` using the columns in the order of `columns`."""
    return OrderedDict((c, export.sanitize_for_csv(getattr(row, c) if is_obj else row[c])) for c in columns)


def flatten_list(l):
    f = []
    for items in l:
        f.extend(items)

    return f


def sanitize_pdvalue_for_live_update(x):
    if pd.isna(x):
        return ''
    else:
        x_ = export.sanitize_for_live_update(x)

        # this is necessary because pandas transforms int columns with NA values to float columns:
        if x_.endswith('.0') and isinstance(x, (float, int)):
            x_ = x_[:x_.rindex('.')]
        return x_


def sanitize_pdvalue_for_csv(x):
    if pd.isna(x):
        return ''
    else:
        x_ = str(export.sanitize_for_csv(x))

        # this is necessary because pandas transforms int columns with NA values to float columns:
        if x_.endswith('.0') and isinstance(x, (float, int)):
            x_ = x_[:x_.rindex('.')]
        return x_


#%% data export functions


def get_hierarchical_data_for_apps(apps):
    """
    Return a hierarchical data structure consisting of nested OrderedDicts for all data collected for apps listed
    in `apps`. The format of the returned data structure is:

    ```
    {
        <session_1_code>: {
            'code': ...,
            'label': ...,
            # more session data
            # ...
            '__apps': {  # list of apps as requested in `apps` argument
                <app_1_name>: [                  # list of subsessions in app 1 played in session 1
                    {
                        'round_number': 1,
                        # more subsession data
                        # ...
                        '__group': [                 # list of groups in subsession 1 of app 1 played in session 1
                            {
                                'id_in_subsession': 1,
                                # more group data
                                # ...
                                '__player': [            # list of players in group 1 in subsession 1 of app 1 played in session 1
                                    {
                                        "id_in_group": 1,
                                        # more player data
                                        # ...
                                        '__participant': {   # reference to participant for this player
                                            "id_in_session": 1,
                                            "code": "5ilq0fad",
                                            # more participant data
                                            # ...
                                        },
                                        '__custom_model': [  # some optional custom model data connected to this player (could also be connected to group or subsession)
                                            # custom model data
                                        ]
                                    }, # more players in this group
                                ]
                            }, # more groups in this session
                        ]
                    }, # more subsessions (rounds) in this app
                ]
            },  # more apps in this session
        },
        <session_2_code>: { # similar to above },
        # ...
    }
    ```
    """

    combined = OrderedDict()

    for app in apps:
        sessions = get_hierarchical_data_for_app(app)

        for sess in sessions:
            sesscode = sess['code']
            if sesscode not in combined.keys():
                combined[sesscode] = OrderedDict([(k, v) for k, v in sess.items() if k != '__subsession'])
                combined[sesscode]['__apps'] = OrderedDict()

            combined[sesscode]['__apps'][app] = sess['__subsession']

    return combined


def get_hierarchical_data_for_app(app_name, return_columns=False):
    """
    Generate hierarchical structured data for app `app_name`, optionally returning flattened field names.
    """

    models_module = get_models_module(app_name)

    # get the standard models
    Player = models_module.Player
    Group = models_module.Group
    Subsession = models_module.Subsession

    # get the custom models configuration
    custom_models_conf = get_custom_models_conf(models_module, for_action='export_data')

    # build standard models' columns
    columns_for_models = {m.__name__.lower(): export.get_fields_for_csv(m)
                          for m in [Player, Group, Subsession, Participant, Session]}

    # build custom models' columns
    columns_for_custom_models = get_custom_models_columns(custom_models_conf, for_action='export_data')

    custom_models_links = get_links_between_std_and_custom_models(custom_models_conf, for_action='export_data')
    std_models_select_related = defaultdict(list)
    for smodel_class, cmodels_links in custom_models_links.items():
        smodel_lwr = smodel_class.__name__.lower()
        for cmodel_class, _ in cmodels_links:
            std_models_select_related[smodel_lwr].append(cmodel_class.__name__.lower())

    # create lists of IDs that will be used for the export
    participant_ids = set(Player.objects.values_list('participant_id', flat=True))
    session_ids = set(Subsession.objects.values_list('session_id', flat=True))

    # create standard model querysets
    qs_participant = Participant.objects.filter(id__in=participant_ids)
    qs_player = Player.objects.filter(session_id__in=session_ids)\
        .order_by('id')\
        .select_related(*std_models_select_related.get('player', [])).values()
    qs_group = Group.objects.filter(session_id__in=session_ids)\
        .select_related(*std_models_select_related.get('group', []))
    qs_subsession = Subsession.objects.filter(session_id__in=session_ids)\
        .select_related(*std_models_select_related.get('subsession', []))

    # create prefetch dictionaries from querysets that map IDs to subsets of the data

    prefetch_filter_ids_for_custom_models = {}   # stores IDs per standard oTree model to be used for
                                                 # custom data prefetching

    # session ID -> subsession rows for this session
    prefetch_subsess = _rows_per_key_from_queryset(qs_subsession, 'session_id')
    prefetch_filter_ids_for_custom_models['subsession'] = _set_of_ids_from_rows_per_key(prefetch_subsess, 'id')

    # subsession ID -> group rows for this subsession
    prefetch_group = _rows_per_key_from_queryset(qs_group, 'subsession_id')
    prefetch_filter_ids_for_custom_models['group'] = _set_of_ids_from_rows_per_key(prefetch_group, 'id')

    # group ID -> player rows for this group
    prefetch_player = _rows_per_key_from_queryset(qs_player, 'group_id')
    prefetch_filter_ids_for_custom_models['player'] = _set_of_ids_from_rows_per_key(prefetch_player, 'id')

    # prefetch dict for custom data models
    prefetch_custom = defaultdict(dict)   # standard oTree model name -> custom model name -> data rows
    for smodel, cmodel_links in custom_models_links.items():  # per oTree std. model
        smodel_name_lwr = smodel.__name__.lower()

        # IDs that occur for that model
        filter_ids = prefetch_filter_ids_for_custom_models[smodel_name_lwr]

        # iterate per custom model
        for model, link_field_name in cmodel_links:
            # prefetch custom model objects that are linked to these oTree std. model IDs
            filter_kwargs = {link_field_name + '__in': filter_ids}
            custom_qs = model.objects.filter(**filter_kwargs).values()

            # store to the dict
            m = model.__name__.lower()
            prefetch_custom[smodel_name_lwr][m] = _rows_per_key_from_queryset(custom_qs, link_field_name)

    # build the final nested data structure
    output_nested = []
    ordered_columns_per_model = OrderedDict()
    # 1. each session
    for sess in Session.objects.filter(id__in=session_ids).values():
        sess_cols = columns_for_models['session']
        if 'session' not in ordered_columns_per_model:
            ordered_columns_per_model['session'] = sess_cols

        out_sess = _odict_from_row(sess, sess_cols)

        # 1.1. each subsession in the session
        out_sess['__subsession'] = []
        for subsess in prefetch_subsess[sess['id']]:
            subsess_cols = columns_for_models['subsession']
            if 'subsession' not in ordered_columns_per_model:
                ordered_columns_per_model['subsession'] = subsess_cols

            out_subsess = _odict_from_row(subsess, subsess_cols)

            # 1.1.1. each possible custom models connected to this subsession
            subsess_custom_models_rows = prefetch_custom.get('subsession', {})
            for subsess_cmodel_name, subsess_cmodel_rows in subsess_custom_models_rows.items():
                cmodel_cols = columns_for_custom_models[subsess_cmodel_name]
                if subsess_cmodel_name not in ordered_columns_per_model:
                    ordered_columns_per_model[subsess_cmodel_name] = cmodel_cols

                out_subsess['__' + subsess_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                           for cmodel_row in subsess_cmodel_rows[subsess['id']]]

            # 1.1.2. each group in this subsession
            out_subsess['__group'] = []
            for grp in prefetch_group[subsess['id']]:
                grp_cols = columns_for_models['group']
                if 'group' not in ordered_columns_per_model:
                    ordered_columns_per_model['group'] = grp_cols

                out_grp = _odict_from_row(grp, grp_cols)

                # 1.1.2.1. each possible custom models connected to this group
                grp_custom_models_rows = prefetch_custom.get('group', {})
                for grp_cmodel_name, grp_cmodel_rows in grp_custom_models_rows.items():
                    cmodel_cols = columns_for_custom_models[grp_cmodel_name]
                    if grp_cmodel_name not in ordered_columns_per_model:
                        ordered_columns_per_model[grp_cmodel_name] = cmodel_cols

                    out_grp['__' + grp_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                       for cmodel_row in grp_cmodel_rows[grp['id']]]

                # 1.1.2.2. each player in this group
                out_grp['__player'] = []
                for player in prefetch_player[grp['id']]:
                    # because player.payoff is a property
                    player['payoff'] = player['_payoff']
                    player['role'] = player['_role']

                    player_cols = columns_for_models['player'] + ['participant_id']
                    if 'player' not in ordered_columns_per_model:
                        ordered_columns_per_model['player'] = player_cols

                    out_player = _odict_from_row(player, player_cols)

                    # 1.1.2.2.1. participant object connected to this player
                    participant_obj = qs_participant.get(id=out_player['participant_id'])
                    out_player['__participant'] = _odict_from_row(participant_obj,
                                                                  columns_for_models['participant'],
                                                                  is_obj=True)
                    out_player['__participant']['vars'] = participant_obj.vars

                    # 1.1.2.2.2. each possible custom models connected to this player
                    player_custom_models_rows = prefetch_custom.get('player', {})
                    for player_cmodel_name, player_cmodel_rows in player_custom_models_rows.items():
                        cmodel_cols = columns_for_custom_models[player_cmodel_name]
                        if player_cmodel_name not in ordered_columns_per_model:
                            ordered_columns_per_model[player_cmodel_name] = cmodel_cols

                        out_player['__' + player_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                                 for cmodel_row in player_cmodel_rows[player['id']]]

                    out_grp['__player'].append(out_player)

                out_subsess['__group'].append(out_grp)

            out_sess['__subsession'].append(out_subsess)

        output_nested.append(out_sess)

    # generate column names
    columns_flat = []
    for model_name, model_cols in ordered_columns_per_model.items():
        columns_flat.extend(['.'.join((model_name, c)) for c in model_cols])

    if return_columns:
        return output_nested, columns_flat
    else:
        return output_nested


def get_links_between_std_and_custom_models(custom_models_conf, for_action):
    """
    Identify the links between custom models and standard models using custom models configuration `custom_models_conf`.
    Return as dict with lists:
        standard model class -> list of tuples (custom model class, link field name)
    """

    std_to_custom = defaultdict(list)

    for model_name, conf in custom_models_conf.items():
        model = conf['class']

        # get the name and field instance of the link
        link_field_name = conf[for_action]['link_with']
        link_field = getattr(model, link_field_name)

        # get the related standard oTree model
        rel_model = link_field.field.related_model

        # save to dicts
        std_to_custom[rel_model].append((conf['class'], link_field_name + '_id'))

    return std_to_custom


def get_modelnames_from_links_between_std_and_custom_models_structure(std_to_custom):
    """
    Get model names from output of `get_links_between_std_and_custom_models()`

    Return as dict with lists: standard model name -> list of lowercase custom model names
    """

    modelnames = defaultdict(list)

    for std_model_name, (custom_model_class, _) in std_to_custom.items():
        modelnames[std_model_name.__name__.lower()].append(custom_model_class.__name__.lower())

    return modelnames


def get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                     std_models_colnames, custom_models_colnames):
    """
    Create a dataframe that joins data from standard models in `std_models_querysets` with data from custom models
    via `links_to_custom_models`. Use columns defined in `std_models_colnames` for standard models and
    `custom_models_colnames` for custom models.

    `std_models_querysets` is a list of tuples, with each row containing:
    - the standard oTree model (Subession, Group or Player)
    - the queryset to fetch the data
    - a tuple (left field name, right field name) defining the columns to use for joining the data

    `links_to_custom_models` comes from `get_modelnames_from_links_between_std_and_custom_models_structure()` and is
    a dict with lists: standard model name -> list of lowercase custom model names.

    The first dataframe fetched via `std_models_querysets` defines the base data. Every following dataframe will be
    joined with the base dataframe and result in a new base dataframe to be joined in the next iteration. A left join
    will be performed for each iteration using the model links defined in each `std_models_querysets` row.

    Returns a data frame of joined data. Each column is prefixed by the lowercase model name, e.g. "player.payoff".
    """
    df = None   # base dataframe

    # iterate through each standard model queryset
    for smodel, smodel_qs, (smodel_link_left, smodel_link_right) in std_models_querysets:
        smodel_name = smodel.__name__
        smodel_name_lwr = smodel_name.lower()
        smodel_colnames = std_models_colnames[smodel_name_lwr]

        if 'id' not in smodel_colnames:   # always add the ID field (necessary for joining)
            smodel_colnames += ['id']

        # optionally add field for the right side of the join
        remove_right_link_col = False   # remove it after joining
        if smodel_link_right:
            smodel_link_right_reduced = smodel_link_right[smodel_link_right.rindex('.')+1:]
            if smodel_link_right_reduced not in smodel_colnames:
                remove_right_link_col = True
                smodel_colnames += [smodel_link_right_reduced]

        # special handling for Player's attributes group, payoff and role
        if smodel_name == 'Player':
            if 'payoff' in smodel_colnames:
                smodel_colnames[smodel_colnames.index('payoff')] = '_payoff'
            smodel_colnames = [c for c in smodel_colnames if c not in {'role', 'group'}]

        if not smodel_qs.exists():   # create empty data frame with given column names
            df_smodel = pd.DataFrame(OrderedDict((c, []) for c in smodel_colnames))
        else:                        # create and fill data frame fetching values from the queryset
            df_smodel = pd.DataFrame(list(smodel_qs.values()))[smodel_colnames]

        # special handling for Player's attributes payoff and role
        if smodel_name == 'Player':
            df_smodel.rename(columns={'_payoff': 'payoff'}, inplace=True)
            df_smodel['role'] = [p.role() if p.role else '' for p in smodel_qs]

        # prepend model name to each column
        renamings = dict((c, smodel_name_lwr + '.' + c) for c in df_smodel.columns)
        df_smodel.rename(columns=renamings, inplace=True)

        if df is None:   # first dataframe is used as base dataframe
            assert smodel_link_left is None and smodel_link_right is None
            df = df_smodel
        else:            # perform the left join, use result as new base dataframe for next iteration
            df = pd.merge(df, df_smodel, how='left', left_on=smodel_link_left, right_on=smodel_link_right)

        if smodel in links_to_custom_models:  # we have custom model(s) linked to this standard model
            for cmodel, cmodel_link_field_name in links_to_custom_models[smodel]:
                cmodel_name = cmodel.__name__
                cmodel_name_lwr = cmodel_name.lower()

                # fetch only the needed IDs
                smodel_ids = df_smodel[smodel_name_lwr + '.id'].unique()
                cmodel_qs = cmodel.objects.filter(**{cmodel_link_field_name + '__in': smodel_ids})
                cmodel_colnames = custom_models_colnames[cmodel_name_lwr]

                # optionally add field for the right side of the join
                remove_cmodel_link_field_name = False       # remove it after joining
                if cmodel_link_field_name not in cmodel_colnames:
                    cmodel_colnames += [cmodel_link_field_name]
                    remove_cmodel_link_field_name = True

                if not cmodel_qs.exists():   # create empty data frame with given column names
                    df_cmodel = pd.DataFrame(OrderedDict((c, []) for c in cmodel_colnames))
                else:                        # create and fill data frame fetching values from the queryset
                    df_cmodel = pd.DataFrame(list(cmodel_qs.values()))[cmodel_colnames]

                # prepend model name to each column
                renamings = dict((c, cmodel_name_lwr + '.' + c) for c in df_cmodel.columns)
                df_cmodel.rename(columns=renamings, inplace=True)

                cmodel_link_field_name = cmodel_name_lwr + '.' + cmodel_link_field_name

                # perform the left join, use result as new base dataframe for next iteration
                df = pd.merge(df, df_cmodel, how='left',
                              left_on=smodel_name_lwr + '.id',
                              right_on=cmodel_link_field_name)

                if remove_cmodel_link_field_name:
                    del df[cmodel_link_field_name]

        if remove_right_link_col:
            del df[smodel_link_right]

    return df


def get_custom_models_conf(models_module, for_action):
    """
    Obtain the custom models defined in the models.py module `models_module` of an app for a certain action (`data_view`
    or `export_data`).

    These models must have a subclass `CustomModelConf` with the respective configuration attributes `data_view`
    or `export_data`.

    Returns a dictionary with `model name` -> `model config dict`.
    """
    assert for_action in ('data_view', 'export_data')

    custom_models_conf = {}
    for attr in dir(models_module):
        val = getattr(models_module, attr)
        try:
            if issubclass(val, Model):   # must be a django model
                metaclass = getattr(val, 'CustomModelConf', None)
                if metaclass and hasattr(metaclass, for_action):
                    custom_models_conf[attr] = {
                        'class': val,
                        for_action: getattr(metaclass, for_action)
                    }
        except TypeError:
            pass

    return custom_models_conf


def get_field_names_for_custom_model(model, conf, use_attname=False):
    """
    Obtain fields for a custom model `model`, depending on its configuration `conf`.
    If `use_attname` is True, use the `attname` property of the field, else the `name` property ("attname" has a "_id"
    suffix for ForeignKeys).
    """
    if 'fields' in conf:
        fields = conf['fields']
    else:
        fields = [f.attname if use_attname else f.name for f in model._meta.fields]

    exclude = set(conf.get('exclude_fields', []))

    return [f for f in fields if f not in exclude]


def get_custom_models_columns(custom_model_conf, for_action):
    """
    Obtain columns (fields) for each custom model in `custom_model_conf`.
    """

    columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf.get(for_action, {}),
                                                                         use_attname=True)
                          for name, conf in custom_model_conf.items()}

    return columns_for_models


def flatten_model_colnames(model_colnames):
    """
    From a dict that maps model name to a list of field names, generate a list with string elements `<module>.<field>`.
    """
    flat_colnames = []
    for modelname, colnames in model_colnames.items():
        flat_colnames.extend([modelname + '.' + c for c in colnames])

    return flat_colnames


def combine_column_names(std_models_colnames, custom_models_colnames, drop_columns=('group.id_in_subsession',)):
    """
    Combine column (or: field) names from standard models `std_models_colnames` and
    custom models `custom_models_colnames` to a list with all column names.
    """
    all_colnames = flatten_model_colnames({'player': std_models_colnames['player']}) \
                   + flatten_model_colnames(custom_models_colnames) \
                   + flatten_model_colnames({m: std_models_colnames[m] for m in std_models_colnames.keys()
                                             if m != 'player'})
    return [c for c in all_colnames if c not in drop_columns]


def get_custom_models_conf_per_app(session):
    """
    Get the custom models configuration dict for all apps in running in `session`.
    """

    custom_models_conf_per_app = {}
    for app_name in session.config['app_sequence']:
        models_module = get_models_module(app_name)
        conf = get_custom_models_conf(models_module, for_action='data_view')
        if conf:
            custom_models_conf_per_app[app_name] = conf

    return custom_models_conf_per_app


def get_rows_for_data_tab(session):
    """
    Overridden function from `otree.export` module to provide data rows for the session data monitor.
    """
    for app_name in session.config['app_sequence']:
        yield from get_rows_for_data_tab_app(session, app_name)


def get_rows_for_data_tab_app(session, app_name):
    """
    Overridden function from `otree.export` module to provide data rows for the session data monitor for a specific app.
    """

    models_module = get_models_module(app_name)
    Player = models_module.Player
    Group = models_module.Group
    Subsession = models_module.Subsession

    pfields, gfields, sfields = export.get_fields_for_data_tab(app_name)

    # find out column names for standard models
    std_models_colnames = dict(zip(('player', 'group', 'subsession'), (pfields, gfields, sfields)))

    # get custom model configuration, if there is any
    custom_models_conf = get_custom_models_conf(models_module, for_action='data_view')

    # find out column names for custom models
    custom_models_colnames = get_custom_models_columns(custom_models_conf, for_action='data_view')

    # identify links between standard and custom models
    links_to_custom_models = get_links_between_std_and_custom_models(custom_models_conf, for_action='data_view')

    # all displayed columns in their order
    all_colnames = combine_column_names(std_models_colnames, custom_models_colnames)

    # iterate through the subsessions (i.e. rounds)
    for subsess_id in Subsession.objects.filter(session=session).values('id'):
        subsess_id = subsess_id['id']
        # pre-filter querysets to get only data of this subsession
        filter_in_subsess = dict(subsession_id__in=[subsess_id])

        # define querysets for standard models and their links for merging as left index, right index
        # the order is important!
        std_models_querysets = (
            (Subsession, Subsession.objects.filter(id=subsess_id), (None, None)),
            (Group, Group.objects.filter(**filter_in_subsess), ('subsession.id', 'group.subsession_id')),
            (Player, Player.objects.filter(**filter_in_subsess), ('group.id', 'player.group_id')),
        )

        # create a dataframe for this subsession's complete data incl. custom models data
        df = get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                              std_models_colnames, custom_models_colnames)

        # sanitize each value
        df = df.applymap(sanitize_pdvalue_for_live_update)\
            .rename(columns={'group.id_in_subsession': 'player.group'})[all_colnames]

        yield df.to_dict(orient='split')['data']


def get_rows_for_custom_export(app_name):
    """
    Provide data rows for custom export function of an app. Used in default custom export function
    `otreeutils.admin_extensions.custom_export`.
    """

    models_module = get_models_module(app_name)
    Player = models_module.Player
    Group = models_module.Group
    Subsession = models_module.Subsession

    # find out column names for standard models
    std_models_colnames = {m.__name__.lower(): export.get_fields_for_csv(m)
                           for m in (Session, Subsession, Group, Player, Participant)}
    std_models_colnames['player'].append('participant_id')

    # get custom model configuration, if there is any
    custom_models_conf = get_custom_models_conf(models_module, for_action='data_view')

    # find out column names for custom models
    custom_models_colnames = get_custom_models_columns(custom_models_conf, for_action='data_view')

    # identify links between standard and custom models
    links_to_custom_models = get_links_between_std_and_custom_models(custom_models_conf, for_action='data_view')

    # define querysets for standard models and their links for merging as left index, right index
    # the order is important!

    # create lists of IDs that will be used for the export
    participant_ids = set(Player.objects.values_list('participant_id', flat=True))
    session_ids = set(Subsession.objects.values_list('session_id', flat=True))

    filter_in_sess = {'session_id__in': session_ids}

    std_models_querysets = (
        (Session, Session.objects.filter(id__in=session_ids), (None, None)),
        (Subsession, Subsession.objects.filter(**filter_in_sess), ('session.id', 'subsession.session_id')),
        (Group, Group.objects.filter(**filter_in_sess), ('subsession.id', 'group.subsession_id')),
        (Player, Player.objects.filter(**filter_in_sess), ('group.id', 'player.group_id')),
        (Participant, Participant.objects.filter(id__in=participant_ids), ('player.participant_id', 'participant.id')),
    )

    # create a dataframe for this subsession's complete data incl. custom models data
    df = get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                          std_models_colnames, custom_models_colnames)

    # sanitize each value
    split_data = df.applymap(sanitize_pdvalue_for_csv).to_dict(orient='split')

    yield split_data['columns']
    for row in split_data['data']:
        yield row


class SessionDataExtension(SessionData):
    """
    Extension to oTree's live session data viewer.
    """
    def vars_for_template(self):
        session = self.session

        custom_models_conf_per_app = get_custom_models_conf_per_app(session)
        if not custom_models_conf_per_app:   # no custom models -> use default oTree method
            return super(SessionDataExtension, self).vars_for_template()

        tables = []
        field_headers = {}
        app_names_by_subsession = []
        round_numbers_by_subsession = []
        for app_name in session.config['app_sequence']:
            models_module = get_models_module(app_name)
            num_rounds = models_module.Subsession.objects.filter(
                session=session
            ).count()

            custom_models_conf = get_custom_models_conf(models_module, for_action='data_view')

            # find out column names for custom models
            custom_models_colnames = get_custom_models_columns(custom_models_conf, for_action='data_view')

            pfields, gfields, sfields = export.get_fields_for_data_tab(app_name)
            gfields = [c for c in gfields if c != 'id_in_subsession']
            std_models_colnames = dict(zip(('player', 'group', 'subsession'), (pfields, gfields, sfields)))

            # all displayed columns in their order
            field_headers[app_name] = combine_column_names(std_models_colnames, custom_models_colnames)

            for round_number in range(1, num_rounds + 1):
                table = dict(pfields=pfields, cfields=custom_models_colnames, gfields=gfields, sfields=sfields)
                tables.append(table)

                app_names_by_subsession.append(app_name)
                round_numbers_by_subsession.append(round_number)

        return dict(
            tables=tables,
            field_headers_json=json.dumps(field_headers),
            app_names_by_subsession=app_names_by_subsession,
            round_numbers_by_subsession=round_numbers_by_subsession,
        )

    def get_template_names(self):
        if get_custom_models_conf_per_app(self.session):
            return ['otreeutils/admin/SessionDataExtension.html']
        else:   # no custom models -> use default oTree template
            return ['otree/admin/SessionData.html']


class SessionDataAjaxExtension(SessionDataAjax):
    """
    Extension to oTree's live session data viewer: Asynchronous JSON data provider.
    """

    def get(self, request, code):
        session = get_object_or_404(Session, code=code)

        if get_custom_models_conf_per_app(session):
            rows = list(get_rows_for_data_tab(session))
            return JsonResponse(rows, safe=False)
        else:     # no custom models -> use default oTree method
            return super(SessionDataAjaxExtension, self).get(request, code)

"""
Custom admin views.

Override existing oTree admin views for custom data live view and custom data export.

Sept. 2018, Markus Konrad <markus.konrad@wzb.eu>
"""


from collections import OrderedDict, defaultdict
from importlib import import_module

from django.http import JsonResponse

from otree.views.admin import SessionData
from otree.views.export import ExportIndex, ExportApp, get_export_response
from otree.export import sanitize_for_live_update, get_field_names_for_live_update, _export_xlsx,\
    get_field_names_for_csv, sanitize_for_csv
from otree.common_internal import get_models_module
from otree.db.models import Model
from otree.models.participant import Participant
from otree.models.session import Session
import pandas as pd


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
        sessions = ExportAppExtension.get_hierarchical_data_for_app(app)

        for sess in sessions:
            sesscode = sess['code']
            if sesscode not in combined.keys():
                combined[sesscode] = OrderedDict([(k, v) for k, v in sess.items() if k != '__subsession'])
                combined[sesscode]['__apps'] = OrderedDict()

            combined[sesscode]['__apps'][app] = sess['__subsession']

    return combined



def sanitize_pdvalue_for_live_update(x):
    if pd.isna(x):
        return ''
    else:
        x_ = sanitize_for_live_update(x)

        # this is necessary because pandas transforms int columns with NA values to float columns:
        if x_.endswith('.0') and isinstance(x, (float, int)):
            x_ = x_[:x_.rindex('.')]
        return x_


def sanitize_pdvalue_for_csv(x):
    if pd.isna(x):
        return ''
    else:
        x_ = str(sanitize_for_csv(x))

        # this is necessary because pandas transforms int columns with NA values to float columns:
        if x_.endswith('.0') and isinstance(x, (float, int)):
            x_ = x_[:x_.rindex('.')]
        return x_


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

        # special handling for Player's attributes payoff and role
        if smodel_name == 'Player':
            smodel_colnames[smodel_colnames.index('payoff')] = '_payoff'
            smodel_colnames = [c for c in smodel_colnames if c != 'role']

        if not smodel_qs.exists():   # create empty data frame with given column names
            df_smodel = pd.DataFrame(OrderedDict((c, []) for c in smodel_colnames))
        else:                        # create and fill data frame fetching values from the queryset
            df_smodel = pd.DataFrame(list(smodel_qs.values()))[smodel_colnames]

        # special handling for Player's attributes payoff and role
        if smodel_name == 'Player':
            df_smodel.rename(columns={'_payoff': 'payoff'}, inplace=True)
            df_smodel['role'] = [p.role() for p in smodel_qs]

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
    return OrderedDict((c, sanitize_for_csv(getattr(row, c) if is_obj else row[c])) for c in columns)


class SessionDataExtension(SessionData):
    """
    Extension to oTree's live session data viewer.
    """

    @staticmethod
    def custom_columns_builder(custom_model_conf):
        """
        Obtain columns (fields) for each custom model in `custom_model_conf`.
        """

        columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf['data_view'],
                                                                             use_attname=True)
                              for name, conf in custom_model_conf.items()}

        return columns_for_models

    def get_context_data(self, **kwargs):
        """
        Load and return data for live data view. This overrides the same method from `SessionData` and is customized
        to merge the data from standard models with custom models' data.
        It outputs the data in a different format, which is a "long" format: The subsessions (rounds) and
        data for players in each round in vertical orientation along with possible custom data output.
        """
        session = self.session

        subsession_data = OrderedDict()          # app name -> list of data frames (one per subsession)
        all_std_models = defaultdict(list)       # model name -> list of column names for standard models
        all_custom_models = defaultdict(list)    # model name -> list of column names for custom models

        # go through all subsessions
        # each subsession might come from a different app
        for subsession in session.get_subsessions():
            # get model classes
            models_module = import_module(subsession.__module__)

            Subsession = models_module.Subsession
            Group = models_module.Group
            Player = models_module.Player

            # get custom model configuration, if there is any
            custom_models_conf = get_custom_models_conf(models_module, for_action='data_view')
            custom_models_names = list(custom_models_conf.keys())

            # identify links between standard and custom models
            links_to_custom_models = get_links_between_std_and_custom_models(custom_models_conf, for_action='data_view')

            # find out column names for standard models
            std_models_colnames = {m.__name__.lower(): get_field_names_for_live_update(m)
                                   for m in (Subsession, Group, Player)}

            # find out column names for custom models
            custom_models_colnames = self.custom_columns_builder(custom_models_conf)

            # pre-filter querysets to get only data of this subsession
            filter_in_subsess = dict(subsession_id__in=[subsession.pk])

            # define querysets for standard models and their links for merging as left index, right index
            # the order is important!
            std_models_querysets = (
                (Subsession, Subsession.objects.filter(id=subsession.pk), (None, None)),
                (Group, Group.objects.filter(**filter_in_subsess), ('subsession.id', 'group.subsession_id')),
                (Player, Player.objects.filter(**filter_in_subsess), ('group.id', 'player.group_id')),
            )

            # create a dataframe for this subsession's complete data incl. custom models data
            df = get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                                  std_models_colnames, custom_models_colnames)

            # sanitize each value
            df = df.applymap(sanitize_pdvalue_for_live_update)

            # add data to subsession data structure
            app_label = subsession._meta.app_label
            if app_label not in subsession_data:
                subsession_data[app_label] = []

                for m in custom_models_names:
                    m_label = app_label + '.' + m
                    all_custom_models[m_label] = [c for c in df.columns if c.startswith(m.lower() + '.')]

                for m, cols in std_models_colnames.items():
                    m_lwr = m.lower()
                    for c in cols:
                        if c not in all_std_models[m_lwr]:
                            all_std_models[m_lwr].append(c)

            subsession_data[app_label].append(df)

        # generate lists of headers and field names ...
        model_headers = []
        field_names = []
        field_names_json = []  # field names for JSON response
        field_names_df = []    # field names for lookup in data frame

        # ... for standard models first
        for m in ['Subsession', 'Group', 'Player']:
            m_lwr = m.lower()
            cols = all_std_models[m_lwr]
            model_headers.append((m, len(cols)))

            if m == 'Player':
                cols = ['payoff' if c == '_payoff' else c for c in cols]

            field_names.extend(cols)
            field_names_json.extend([m + '.' + c for c in cols])
            field_names_df.extend([m.lower() + '.' + c for c in cols])

        # ... and then for custom data models
        for m_label, cols in all_custom_models.items():
            model_headers.append((m_label, len(cols)))
            field_names.extend([c[c.rfind('.')+1:] for c in cols])
            field_names_json.extend([m_label + '.' + c for c in cols])
            field_names_df.extend(cols)

        # set generic header name
        subsess_headers = [('Collected data', len(field_names))]

        # put data into rows
        rows = []
        for app_label, list_of_dfs in subsession_data.items():
            for df in list_of_dfs:
                coldata = []
                n_df_rows = len(df)
                for f in field_names_df:
                    if f in df.columns:
                        coldata.append(df[f].values.tolist())
                    else:
                        coldata.append([''] * n_df_rows)

                rows.extend(zip(*coldata))

        # create JSON response data
        self.context_json = []
        for i, row in enumerate(rows, start=1):
            d_row = OrderedDict()
            d_row['participant_label'] = '#{}'.format(i)   # it has nothing to do with participant IDs any more
            for t, v in zip(field_names_json, row):
                d_row[t] = v
            self.context_json.append(d_row)

        context = super(SessionData, self).get_context_data(**kwargs)   # calls `get_context_data()` from
                                                                        # AdminSessionPageMixin
        context.update({
            'subsession_headers': subsess_headers,
            'model_headers': model_headers,
            'field_headers': field_names,
            'rows': rows})

        return context

    def get_template_names(self):
        return ['otree/admin/SessionData.html']    # use own template


class ExportIndexExtension(ExportIndex):
    """
    Extension class for data export index page.
    """

    template_name = 'otreeutils/admin/ExportIndexExtension.html'    # use own template

    def get_context_data(self, **kwargs):
        """
        Generate data for the template.

        Override oTree's get_context_data() to add links to custom data export.
        """

        # call super class method
        context = super().get_context_data(**kwargs)

        collected_apps = set()
        app_info = []
        for session in Session.objects.all():
            for app_name in session.config['app_sequence']:
                if app_name in collected_apps:
                    continue

                # try to find out if an app uses otreeutils' admin_extensions
                try:
                    app_module = import_module(app_name)
                except:
                    app_module = None

                uses_otreeutils_export = False
                if app_module and hasattr(app_module, 'urls') and hasattr(app_module.urls, 'urlpatterns'):
                    for pttrn in app_module.urls.urlpatterns:
                        if pttrn.name == 'ExportApp' and pttrn.lookup_str.startswith('otreeutils.admin_extensions'):
                            uses_otreeutils_export = True
                            break

                app_info.append((app_name, uses_otreeutils_export))
                collected_apps.add(app_name)

        # add app_info for custom template
        assert 'app_info' not in context
        context['app_info'] = app_info

        return context


class ExportAppExtension(ExportApp):
    """
    Extension to oTree's data export to allow for full data export with custom data models.
    """

    @staticmethod
    def custom_columns_builder(custom_model_conf):
        """
        Obtain columns (fields) for each custom model in `custom_model_conf`.
        """
        columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf['export_data'],
                                                                             use_attname=True)
                              for name, conf in custom_model_conf.items()}

        return columns_for_models

    @classmethod
    def get_dataframe_for_app(cls, app_name):
        """
        Generate data rows for app `app_name`, also adding rows of custom data models.
        """

        models_module = get_models_module(app_name)

        # get the standard models
        Player = models_module.Player
        Group = models_module.Group
        Subsession = models_module.Subsession

        # get custom model configuration, if there is any
        custom_models_conf = get_custom_models_conf(models_module, for_action='export_data')

        # identify links between standard and custom models
        links_to_custom_models = get_links_between_std_and_custom_models(custom_models_conf, for_action='export_data')

        # find out column names for standard models
        std_models_colnames = {m.__name__.lower(): get_field_names_for_csv(m)
                               for m in (Session, Subsession, Group, Player, Participant)}
        std_models_colnames['player'].append('participant_id')

        # find out column names for custom models
        custom_models_colnames = cls.custom_columns_builder(custom_models_conf)

        # create lists of IDs that will be used for the export
        participant_ids = set(Player.objects.values_list('participant_id', flat=True))
        session_ids = set(Subsession.objects.values_list('session_id', flat=True))

        filter_in_sess = {'session_id__in': session_ids}

        std_models_querysets = (
            (Session, Session.objects.filter(id__in=session_ids), (None, None)),
            (Subsession, Subsession.objects.filter(**filter_in_sess), ('session.id', 'subsession.session_id')),
            (Group, Group.objects.filter(**filter_in_sess), ('subsession.id', 'group.subsession_id')),
            (Player, Player.objects.filter(**filter_in_sess), ('group.id', 'player.group_id')),
            (Participant, Participant.objects.filter(id__in=participant_ids), ('player.participant_id',
                                                                                    'participant.id')),
        )

        # create a dataframe for this app's complete data incl. custom models data
        df = get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                              std_models_colnames, custom_models_colnames)

        # sanitize each value
        df = df.applymap(sanitize_pdvalue_for_csv)

        return df


    @classmethod
    def get_hierarchical_data_for_app(cls, app_name, return_columns=False):
        """
        Generate hierarchical structured data for app `app_name`, optionally returning flattened field names.
        """

        models_module = get_models_module(app_name)

        # get the standard models
        Player = models_module.Player
        Group = models_module.Group
        Subsession = models_module.Subsession

        # get the custom models configuration
        custom_models_conf = get_custom_models_conf(models_module, 'export_data')

        # build standard models' columns
        columns_for_models = {m.__name__.lower(): get_field_names_for_csv(m)
                              for m in [Player, Group, Subsession, Participant, Session]}

        # build custom models' columns
        columns_for_custom_models = cls.custom_columns_builder(custom_models_conf)

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

                        player_cols = columns_for_models['player'] + ['participant_id']
                        if 'player' not in ordered_columns_per_model:
                            ordered_columns_per_model['player'] = player_cols

                        out_player = _odict_from_row(player, player_cols)

                        # 1.1.2.2.1. participant object connected to this player
                        participant_obj = qs_participant.get(id=out_player['participant_id'])
                        out_player['__participant'] = _odict_from_row(participant_obj,
                                                                      columns_for_models['participant'],
                                                                      is_obj=True)

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

    def get(self, request, *args, **kwargs):
        """
        Generate response for data download.

        Overrides default oTree method allowing custom data models export and additionally adds JSON export.
        """

        app_name = kwargs['app_name']

        if not request.GET.get('custom'):   # if "custom" is not requested, use the default oTree method
            return super().get(request, *args, **kwargs)

        if request.GET.get('json'):
            data = self.get_hierarchical_data_for_app(app_name)

            return JsonResponse(data, safe=False)  # safe=False is necessary for exporting array structures
        else:
            response, file_extension = get_export_response(request, app_name)

            df = self.get_dataframe_for_app(app_name)

            if file_extension == 'xlsx':
                rows = [df.columns]
                rows.extend(df.values.tolist())
                _export_xlsx(response, rows)
            else:
                df.to_csv(response, index=False)

            return response

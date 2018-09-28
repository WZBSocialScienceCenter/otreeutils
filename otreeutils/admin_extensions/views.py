"""
Custom admin views.

Override existing oTree admin views for custom data live view and custom data export.

Sept. 2018, Markus Konrad <markus.konrad@wzb.eu>
"""


from collections import OrderedDict, defaultdict
from importlib import import_module

from django.http import JsonResponse

from otree.views.admin import SessionData, pretty_name, pretty_round_name
from otree.views.export import ExportIndex, ExportApp, get_export_response
from otree.export import sanitize_for_live_update, get_field_names_for_live_update, get_rows_for_live_update, _export_csv, _export_xlsx,\
    get_field_names_for_csv, sanitize_for_csv
from otree.common_internal import get_models_module
from otree.db.models import Model
from otree.models.participant import Participant
from otree.models.session import Session
import pandas as pd

from otreeutils.common import hierarchical_data_columnwise, columnwise_data_as_rows


def sanitize_pdvalue_for_live_update(x):
    if pd.isna(x):
        return ''
    else:
        return sanitize_for_live_update(x)


def sanitize_pdvalue_for_csv(x):
    if pd.isna(x):
        return ''
    else:
        return sanitize_for_csv(x)


def get_links_between_std_and_custom_models(custom_models_conf, for_action):
    """
    Identify the links between custom models and standard models using custom models configuration `custom_models_conf`.
    Return as dict with lists:
        standard model -> list of tuples (custom model class, link field name)
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
    df = None

    for smodel, smodel_qs, (smodel_link_left, smodel_link_right) in std_models_querysets:
        smodel_name = smodel.__name__
        smodel_name_lwr = smodel_name.lower()
        smodel_colnames = std_models_colnames[smodel_name_lwr]

        if 'id' not in smodel_colnames:
            smodel_colnames += ['id']

        remove_right_link_col = False
        if smodel_link_right and smodel_link_right not in smodel_colnames:
            remove_right_link_col = True
            smodel_colnames += [smodel_link_right[smodel_link_right.rindex('.')+1:]]

        if smodel_name == 'Player':
            smodel_colnames[smodel_colnames.index('payoff')] = '_payoff'
            smodel_colnames = [c for c in smodel_colnames if c != 'role']

        if not smodel_qs.exists():
            df_smodel = pd.DataFrame(OrderedDict((c, []) for c in smodel_colnames))
        else:
            df_smodel = pd.DataFrame(list(smodel_qs.values()))[smodel_colnames]

        if smodel_name == 'Player':
            df_smodel.rename(columns={'_payoff': 'payoff'}, inplace=True)
            df_smodel['role'] = [p.role() for p in smodel_qs]

        renamings = dict((c, smodel_name_lwr + '.' + c) for c in df_smodel.columns)
        df_smodel.rename(columns=renamings, inplace=True)

        if df is None:
            assert smodel_link_left is None and smodel_link_right is None
            df = df_smodel
        else:
            df = pd.merge(df, df_smodel, how='left', left_on=smodel_link_left, right_on=smodel_link_right)

        if smodel in links_to_custom_models:
            for cmodel, cmodel_link_field_name in links_to_custom_models[smodel]:
                cmodel_name = cmodel.__name__
                cmodel_name_lwr = cmodel_name.lower()

                #cmodel_link_field = getattr(cmodel, cmodel_link_field_name)
                #link_set_name = cmodel_link_field_name + '_set'

                smodel_ids = df_smodel[smodel_name_lwr + '.id'].unique()
                cmodel_qs = cmodel.objects.filter(**{cmodel_link_field_name + '__in': smodel_ids})
                cmodel_colnames = custom_models_colnames[cmodel_name_lwr]

                remove_cmodel_link_field_name = False
                if cmodel_link_field_name not in cmodel_colnames:
                    cmodel_colnames += [cmodel_link_field_name]
                    remove_cmodel_link_field_name = True

                if not cmodel_qs.exists():
                    df_cmodel = pd.DataFrame(OrderedDict((c, []) for c in cmodel_colnames))
                else:
                    df_cmodel = pd.DataFrame(list(cmodel_qs.values()))[cmodel_colnames]

                renamings = dict((c, cmodel_name_lwr + '.' + c) for c in df_cmodel.columns)
                df_cmodel.rename(columns=renamings, inplace=True)

                cmodel_link_field_name = cmodel_name_lwr + '.' + cmodel_link_field_name

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


def _odict_from_row(row, columns):
    """Create an OrderedDict from a dict `row` using the columns in the order of `columns`."""
    return OrderedDict((c, sanitize_for_csv(row[c])) for c in columns)


class SessionDataExtension(SessionData):
    """
    Extension to oTree's live session data viewer.
    """

    @staticmethod
    def custom_rows_queryset(models_module, custom_models_names,  **kwargs):
        """
        Queryset to fetch rows from custom models `custom_models_names` in module `models_module`.

        Currently, this only supports custom models linked to the Player model, but overriding this method can add
        support to other linked models.
        """

        base_class = 'Player'
        base_key = 'id_in_group'
        base_model = getattr(models_module, base_class)
        prefetch_related_args = [m.lower() + '_set' for m in custom_models_names]

        # prefetches custom models linked to base_class

        return (base_model.objects\
            .filter(subsession_id=kwargs['subsession'].pk)\
            .prefetch_related(*prefetch_related_args),
            base_class,
            base_key)

    @staticmethod
    def custom_rows_builder(qs, columns_for_custom_models, custom_models_baseclass, custom_models_basekey):
        """
        Build rows for data from queryset `qs` with custom models using columns `columns_for_custom_models`.

        Returns a nested dict with:
        base class key (e.g. player ID) -> custom model name -> list of data rows for that model
        """
        rows = defaultdict(lambda: defaultdict(list))

        for base_instance in qs:  # base_instance is Player if default `custom_rows_queryset()` is used
            key = str(getattr(base_instance, custom_models_basekey))

            # for each custom model and its columns...
            for model_name_lwr, colnames in columns_for_custom_models.items():
                # get the respective data linked to the current base_instance for this custom model
                model_results_set = getattr(base_instance, model_name_lwr + '_set').all()

                # add the custom model data
                for res in model_results_set:
                    row = []
                    for colname in colnames:
                        attr = getattr(res, colname, '')
                        if isinstance(attr, Model):  # use ID if we encounter a foreign key
                            attr = attr.pk

                        row.append(sanitize_for_live_update(attr))

                    rows[key][model_name_lwr].append(row)

        return rows

    @staticmethod
    def custom_columns_builder(custom_model_conf):
        """
        Obtain columns (fields) for each custom model in `custom_model_conf`.
        """

        columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf['data_view'])
                              for name, conf in custom_model_conf.items()}

        return columns_for_models

    @staticmethod
    def combine_rows(subsession_rows, custom_rows, columns_for_models, columns_for_custom_models,
                     custom_models_names_lwr, custom_models_baseclass, custom_models_basekey):
        """
        Combine oTree subsession rows `subsession_rows` with rows from the custom data models `custom_rows`.
        """
        combined_rows = []
        otree_modelnames = ['Player', 'Group', 'Subsession']
        otree_modelnames_lwr = [n.lower() for n in otree_modelnames]
        for row in subsession_rows:
            # find row key
            row_key = None

            i = 0
            for ot_model_name in otree_modelnames:
                model_fields = columns_for_models[ot_model_name.lower()]
                n_fields = len(model_fields)

                if ot_model_name == custom_models_baseclass:
                    try:
                        key_idx = model_fields.index(custom_models_basekey)
                        row_key = row[i + key_idx]
                    except ValueError:  # custom_models_basekey not in model_fields
                        pass

                i += n_fields

            if row_key is None:
                raise ValueError('no row key found (base class: `%s`, key name: `%s`)'
                                 % (custom_models_baseclass, custom_models_basekey))

            combrow = []  # combined row
            n_fields_from_otree_models = 0
            for model_name in ['player'] + custom_models_names_lwr + ['group', 'subsession']:
                if model_name in otree_modelnames_lwr:  # standard oTree model
                    n_fields = len(columns_for_models[model_name])
                    field_idx_start = n_fields_from_otree_models
                    field_idx_end = n_fields_from_otree_models + n_fields

                    # insert values at the correct indices
                    combrow.extend(row[field_idx_start:field_idx_end])
                    n_fields_from_otree_models += n_fields
                else:  # custom model
                    n_fields = len(columns_for_custom_models[model_name])

                    # get all fields and their values of this model
                    custom_vals = custom_rows[row_key][model_name]
                    if custom_vals:
                        assert all(n == n_fields for n in map(len, custom_vals))
                        # for 1:m fields, add several custom values divided by a horizontal line <hr>
                        for col_values in zip(*custom_rows[row_key][model_name]):
                            col_values = [v if v else '&nbsp;' for v in col_values]
                            combrow.append('<hr>'.join(col_values))
                    else:
                        combrow.extend([''] * n_fields)

            combined_rows.append(combrow)

        n_cols_otree_models = sum(map(len, columns_for_models.values()))
        n_cols_custom_models = sum(map(len, columns_for_custom_models.values()))
        assert all(n == n_cols_otree_models + n_cols_custom_models for n in map(len, combined_rows)),\
               'number of fields for at least 1 row is not the sum of oTree model fields and custom model fields'

        return combined_rows

    def get_context_data(self, **kwargs):
        session = self.session

        rows = []

        round_headers = []
        model_headers = []
        field_names = []
        field_names_json = []  # field names for JSON response

        for subsession in session.get_subsessions():
            models_module = import_module(subsession.__module__)

            Subsession = models_module.Subsession
            Group = models_module.Group
            Player = models_module.Player

            custom_models_conf = get_custom_models_conf(models_module, for_action='data_view')
            custom_models_names = list(custom_models_conf.keys())
            custom_models_names_lwr = [n.lower() for n in custom_models_names]

            links_to_custom_models = get_links_between_std_and_custom_models(custom_models_conf, for_action='data_view')

            std_models_colnames = {m.__name__.lower(): get_field_names_for_live_update(m)
                                   for m in (Subsession, Group, Player)}
            custom_models_colnames = self.custom_columns_builder(custom_models_conf)

            filter_in_sess = dict(session_id__in=[session.pk])

            std_models_querysets = (
                (Subsession, Subsession.objects.filter(id=subsession.pk), (None, None)),
                (Group, Group.objects.filter(**filter_in_sess), ('subsession.id', 'group.subsession_id')),
                (Player, Player.objects.filter(**filter_in_sess), ('group.id', 'player.group_id')),
            )

            df = get_dataframe_from_linked_models(std_models_querysets, links_to_custom_models,
                                                  std_models_colnames, custom_models_colnames)
            df = df.applymap(sanitize_pdvalue_for_live_update)
            df_as_list = df.values.tolist()

            if not rows:
                rows = df_as_list
            else:
                for i in range(len(rows)):
                    rows[i].extend(df_as_list[i])

            round_colspan = 0
            for model_name in ['player'] + custom_models_names_lwr + ['group', 'subsession']:
                colspan = sum([c.startswith(model_name + '.') for c in df.columns])
                model_headers.append((model_name.title(), colspan))
                round_colspan += colspan

            round_name = pretty_round_name(subsession._meta.app_label, subsession.round_number)

            round_headers.append((round_name, round_colspan))

            this_round_fields = []
            this_round_fields_json = []
            for model_name in ['Player'] + custom_models_names + ['Group', 'Subsession']:
                column_names = [c[:c.index('.')] for c in df.columns if c.startswith(model_name + '.')]
                this_model_fields = [pretty_name(n) for n in column_names]
                this_model_fields_json = [
                    '{}.{}.{}'.format(round_name, model_name, colname)
                    for colname in column_names
                ]
                this_round_fields.extend(this_model_fields)
                this_round_fields_json.extend(this_model_fields_json)

            field_names.extend(this_round_fields)
            field_names_json.extend(this_round_fields_json)

        # dictionary for json response
        # will be used only if json request  is done

        self.context_json = []
        for i, row in enumerate(rows, start=1):
            d_row = OrderedDict()
            # table always starts with participant 1
            d_row['participant_label'] = '#{}'.format(i)
            for t, v in zip(field_names_json, row):
                d_row[t] = v
            self.context_json.append(d_row)

        context = super(SessionData, self).get_context_data(**kwargs)   # calls `get_context_data()` from
                                                                        # AdminSessionPageMixin
        context.update({
            'subsession_headers': round_headers,
            'model_headers': model_headers,
            'field_headers': field_names,
            'rows': rows})


        return context



    def get_context_data_old(self, **kwargs):
        """
        Main overridden function: Generate the data to be displayed in the live data view.
        """

        def columns_for_any_modelname(modelname):
            cols = columns_for_custom_models.get(modelname, columns_for_models.get(modelname, []))
            if not cols:
                raise ValueError('No fields/columns for model `%s`' % model_name)
            return cols

        session = self.session

        rows = []

        round_headers = []
        model_headers = []
        field_names = []

        # field names for JSON response
        field_names_json = []

        for subsession in session.get_subsessions():
            models_module = import_module(subsession.__module__)
            custom_models_conf = get_custom_models_conf(models_module, 'data_view')
            custom_models_names = list(custom_models_conf.keys())
            custom_models_names_lwr = [n.lower() for n in custom_models_names]

            # can't use subsession._meta.app_config.name, because it won't work
            # if the app is removed from SESSION_CONFIGS after the session is
            # created.
            columns_for_models, subsession_rows = get_rows_for_live_update(subsession)

            # get the columns for the custom models
            columns_for_custom_models = self.custom_columns_builder(custom_models_conf)

            # get the queryset for the custom models
            custom_models_qs, custom_models_baseclass, custom_models_basekey = \
                self.custom_rows_queryset(models_module, custom_models_names, subsession=subsession)

            # build the rows for the custom models
            custom_rows = self.custom_rows_builder(custom_models_qs, columns_for_custom_models,
                                                   custom_models_baseclass, custom_models_basekey)
            # pprint(subsession_rows)
            # pprint(columns_for_custom_models)
            # pprint(custom_rows)

            # combine those rows with the subsession rows
            combined_rows = self.combine_rows(subsession_rows, custom_rows, columns_for_models,
                                              columns_for_custom_models, custom_models_names_lwr,
                                              custom_models_baseclass, custom_models_basekey)

            if not rows:
                rows = combined_rows
            else:
                for i in range(len(rows)):
                    rows[i].extend(combined_rows[i])

            round_colspan = 0
            for model_name in ['player'] + custom_models_names_lwr + ['group', 'subsession']:
                colspan = len(columns_for_any_modelname(model_name))
                model_headers.append((model_name.title(), colspan))
                round_colspan += colspan

            round_name = pretty_round_name(subsession._meta.app_label, subsession.round_number)

            round_headers.append((round_name, round_colspan))

            this_round_fields = []
            this_round_fields_json = []
            for model_name in ['Player'] + custom_models_names + ['Group', 'Subsession']:
                column_names = columns_for_any_modelname(model_name.lower())
                this_model_fields = [pretty_name(n) for n in column_names]
                this_model_fields_json = [
                    '{}.{}.{}'.format(round_name, model_name, colname)
                    for colname in column_names
                ]
                this_round_fields.extend(this_model_fields)
                this_round_fields_json.extend(this_model_fields_json)

            field_names.extend(this_round_fields)
            field_names_json.extend(this_round_fields_json)

        # dictionary for json response
        # will be used only if json request  is done

        self.context_json = []
        for i, row in enumerate(rows, start=1):
            d_row = OrderedDict()
            # table always starts with participant 1
            d_row['participant_label'] = 'P{}'.format(i)
            for t, v in zip(field_names_json, row):
                d_row[t] = v
            self.context_json.append(d_row)

        context = super(SessionData, self).get_context_data(**kwargs)   # calls `get_context_data()` from
                                                                        # AdminSessionPageMixin
        context.update({
            'subsession_headers': round_headers,
            'model_headers': model_headers,
            'field_headers': field_names,
            'rows': rows})
        return context

    def get_template_names(self):
        return ['otreeutils/admin/SessionDataExtension.html']    # use own template


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
    def get_data_rows_for_app(cls, app_name):
        """
        Generate data rows for app `app_name`, also adding rows of custom data models.
        """

        # get the hierarchically structured data and flattened field names
        data, colnames = cls.get_hierarchical_data_for_app(app_name, return_columns=True)

        # turn hierarchical data into column-wise data
        coldata = hierarchical_data_columnwise(data)

        if not coldata:
            return [[]]

        # if there's no data for certain models, then their fields will not be listed in the columns
        # however, we want all columns to be exported, even if they do not contain data

        # make column names matchable
        tmp_coldata = OrderedDict()
        for c, v in coldata.items():
            c = c.replace('__', '')
            n_dots = c.count('.')
            if n_dots > 1:
                last_dot_idx = c.rindex('.')
                cut_idx = c.rindex('.', 0, last_dot_idx)
                c = c[cut_idx+1:]
            elif n_dots == 0:
                c = 'session.' + c

            tmp_coldata[c] = v

        coldata = tmp_coldata

        # create final data by filling all-empty columns with None values
        n_values = len(next(iter(coldata.values())))
        coldata_full = OrderedDict()
        for cname in colnames:
            coldata_full[cname] = coldata.get(cname, [None] * n_values)

        # convert to rowwise data
        data_rowwise = columnwise_data_as_rows(coldata_full, with_header=False)

        # prepend column name header
        rows = [colnames]
        rows.extend(data_rowwise)

        return rows

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

        # identify the links between custom models and standard models
        custom_models_links = defaultdict(list)         # standard model name -> list of tuples
                                                        #                        (custom model class, link field name)
        std_models_select_related = defaultdict(list)   # standard model name -> list of lowercase custom model names
        for model_name, conf in custom_models_conf.items():
            model = conf['class']

            # get the name and field instance of the link
            link_field_name = conf['export_data']['link_with']
            link_field = getattr(model, link_field_name)

            # get the related standard oTree model
            rel_model = link_field.field.related_model

            # save to dicts
            custom_models_links[rel_model.__name__].append((conf['class'], link_field_name + '_id'))
            std_models_select_related[rel_model.__name__.lower()].append(model_name.lower())

        # create lists of IDs that will be used for the export
        participant_ids = Player.objects.values_list('participant_id', flat=True)
        session_ids = Subsession.objects.values_list('session_id', flat=True)

        # create standard model querysets
        qs_player = Player.objects.filter(session_id__in=session_ids)\
            .order_by('id')\
            .select_related(*std_models_select_related.get('player', [])).values()
        qs_group = Group.objects.filter(session_id__in=session_ids)\
            .select_related(*std_models_select_related.get('group', []))
        qs_subsession = Subsession.objects.filter(session_id__in=session_ids)\
            .select_related(*std_models_select_related.get('subsession', []))

        # create prefetch dictionaries from querysets that map IDs to subsets of the data

        prefetch_participants = defaultdict(list)        # session ID -> participant rows
        for row in Participant.objects.filter(id__in=participant_ids).values():
            prefetch_participants[row['session_id']].append(row)

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
        for otree_model_name, custom_modellist_for_otree_model in custom_models_links.items():  # per oTree std. model
            otree_model_name_lwr = otree_model_name.lower()

            # IDs that occur for that model
            filter_ids = prefetch_filter_ids_for_custom_models[otree_model_name_lwr]

            # iterate per custom model
            for model, link_field_name in custom_modellist_for_otree_model:
                # prefetch custom model objects that are linked to these oTree std. model IDs
                filter_kwargs = {link_field_name + '__in': filter_ids}
                custom_qs = model.objects.filter(**filter_kwargs).values()

                # store to the dict
                m = model.__name__.lower()
                prefetch_custom[otree_model_name_lwr][m] = _rows_per_key_from_queryset(custom_qs, link_field_name)

        # build the final nested data structure
        output_nested = []
        ordered_columns_per_model = OrderedDict()
        # 1. each session
        for sess in Session.objects.filter(id__in=session_ids).values():
            sess_cols = columns_for_models['session']
            if 'session' not in ordered_columns_per_model:
                ordered_columns_per_model['session'] = sess_cols

            out_sess = _odict_from_row(sess, sess_cols)

            # 1.1. each participant in the session
            out_sess['__participant'] = []
            for part in prefetch_participants[sess['id']]:
                part_cols = columns_for_models['participant']

                if 'participant' not in ordered_columns_per_model:
                    ordered_columns_per_model['participant'] = part_cols

                out_part = _odict_from_row(part, part_cols)
                out_sess['__participant'].append(out_part)

            # 1.2. each subsession in the session
            out_sess['__subsession'] = []
            for subsess in prefetch_subsess[sess['id']]:
                subsess_cols = columns_for_models['subsession']
                if 'subsession' not in ordered_columns_per_model:
                    ordered_columns_per_model['subsession'] = subsess_cols

                out_subsess = _odict_from_row(subsess, subsess_cols)

                # 1.2.1. each possible custom models connected to this subsession
                subsess_custom_models_rows = prefetch_custom.get('subsession', {})
                for subsess_cmodel_name, subsess_cmodel_rows in subsess_custom_models_rows.items():
                    cmodel_cols = columns_for_custom_models[subsess_cmodel_name]
                    if subsess_cmodel_name not in ordered_columns_per_model:
                        ordered_columns_per_model[subsess_cmodel_name] = cmodel_cols

                    out_subsess['__' + subsess_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                               for cmodel_row in subsess_cmodel_rows[subsess['id']]]

                # 1.2.2. each group in this subsession
                out_subsess['__group'] = []
                for grp in prefetch_group[subsess['id']]:
                    grp_cols = columns_for_models['group']
                    if 'group' not in ordered_columns_per_model:
                        ordered_columns_per_model['group'] = grp_cols

                    out_grp = _odict_from_row(grp, grp_cols)

                    # 1.2.2.1. each possible custom models connected to this group
                    grp_custom_models_rows = prefetch_custom.get('group', {})
                    for grp_cmodel_name, grp_cmodel_rows in grp_custom_models_rows.items():
                        cmodel_cols = columns_for_custom_models[grp_cmodel_name]
                        if grp_cmodel_name not in ordered_columns_per_model:
                            ordered_columns_per_model[grp_cmodel_name] = cmodel_cols

                        out_grp['__' + grp_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                           for cmodel_row in grp_cmodel_rows[grp['id']]]

                    # 1.2.2.2. each player in this group
                    out_grp['__player'] = []
                    for player in prefetch_player[grp['id']]:
                        # because player.payoff is a property
                        player['payoff'] = player['_payoff']

                        player_cols = columns_for_models['player']
                        if 'player' not in ordered_columns_per_model:
                            ordered_columns_per_model['player'] = player_cols

                        out_player = _odict_from_row(player, player_cols)

                        # 1.2.2.2.1. each possible custom models connected to this player
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

            rows = self.get_data_rows_for_app(app_name)

            if file_extension == 'xlsx':
                _export_xlsx(response, rows)
            else:
                _export_csv(response, rows)

            return response

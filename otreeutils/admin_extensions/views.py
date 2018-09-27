from collections import OrderedDict, defaultdict
from importlib import import_module

from django.http import JsonResponse

from otree.views.admin import SessionData, pretty_name, pretty_round_name
from otree.views.export import ExportIndex, ExportApp, get_export_response
from otree.export import sanitize_for_live_update, get_rows_for_live_update, _export_csv, _export_xlsx,\
    get_field_names_for_csv, sanitize_for_csv
from otree.common_internal import get_models_module
from otree.db.models import Model
from otree.models.participant import Participant
from otree.models.session import Session

from otreeutils.common import hierarchical_data_columnwise, columnwise_data_as_rows


def get_custom_models_conf(models_module, for_action):
    assert for_action in ('data_view', 'export_data')

    custom_models_conf = {}
    for attr in dir(models_module):
        val = getattr(models_module, attr)
        try:
            if issubclass(val, Model):
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
    if 'fields' in conf:
        fields = conf['fields']
    else:
        fields = [f.attname if use_attname else f.name for f in model._meta.fields]

    exclude = set(conf.get('exclude_fields', []))

    return [f for f in fields if f not in exclude]


def _rows_per_key_from_queryset(qs, key):
    res = defaultdict(list)

    for row in qs.values():
        res[row[key]].append(row)

    return res


def _set_of_ids_from_rows_per_key(rows, idfield):
    return set(x[idfield] for r in rows.values() for x in r)


def _odict_from_row(row, columns):
    return OrderedDict((c, sanitize_for_csv(row[c])) for c in columns)


class SessionDataExtension(SessionData):
    @staticmethod
    def custom_rows_queryset(models_module, custom_models_names,  **kwargs):
        base_class = 'Player'
        base_key = 'id_in_group'
        base_model = getattr(models_module, base_class)
        prefetch_related_args = [m.lower() + '_set' for m in custom_models_names]

        return (base_model.objects\
            .filter(subsession_id=kwargs['subsession'].pk)\
            .prefetch_related(*prefetch_related_args),
            base_class,
            base_key)

    @staticmethod
    def custom_rows_builder(qs, columns_for_custom_models, custom_models_baseclass, custom_models_basekey):
        rows = defaultdict(lambda: defaultdict(list))

        for base_instance in qs:
            key = str(getattr(base_instance, custom_models_basekey))

            for model_name_lwr, colnames in columns_for_custom_models.items():
                model_results_set = getattr(base_instance, model_name_lwr + '_set').all()

                for res in model_results_set:
                    row = []
                    for colname in colnames:
                        attr = getattr(res, colname, '')
                        if isinstance(attr, Model):
                            attr = attr.pk

                        row.append(sanitize_for_live_update(attr))

                    rows[key][model_name_lwr].append(row)

        return rows

    @staticmethod
    def custom_columns_builder(custom_model_conf):
        columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf['data_view'])
                              for name, conf in custom_model_conf.items()}

        return columns_for_models

    @staticmethod
    def combine_rows(subsession_rows, custom_rows, columns_for_models, columns_for_custom_models,
                     custom_models_names_lwr, custom_models_baseclass, custom_models_basekey):
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
                if model_name in otree_modelnames_lwr:
                    n_fields = len(columns_for_models[model_name])
                    field_idx_start = n_fields_from_otree_models
                    field_idx_end = n_fields_from_otree_models + n_fields
                    combrow.extend(row[field_idx_start:field_idx_end])
                    n_fields_from_otree_models += n_fields
                else:
                    n_fields = len(columns_for_custom_models[model_name])
                    custom_vals = custom_rows[row_key][model_name]
                    if custom_vals:
                        assert all(n == n_fields for n in map(len, custom_vals))
                        for col_values in zip(*custom_rows[row_key][model_name]):
                            col_values = [v if v else '&nbsp;' for v in col_values]
                            combrow.append('<hr>'.join(col_values))
                    else:
                        combrow.extend([''] * n_fields)

            combined_rows.append(combrow)

        n_cols_otree_models = sum(map(len, columns_for_models.values()))
        n_cols_custom_models = sum(map(len, columns_for_custom_models.values()))
        assert all(n == n_cols_otree_models + n_cols_custom_models for n in map(len, combined_rows))

        return combined_rows

    def get_context_data(self, **kwargs):
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

            columns_for_custom_models = self.custom_columns_builder(custom_models_conf)
            custom_models_qs, custom_models_baseclass, custom_models_basekey = \
                self.custom_rows_queryset(models_module, custom_models_names, subsession=subsession)
            custom_rows = self.custom_rows_builder(custom_models_qs, columns_for_custom_models,
                                                   custom_models_baseclass, custom_models_basekey)
            # pprint(subsession_rows)
            # pprint(columns_for_custom_models)
            # pprint(custom_rows)

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
        return ['otreeutils/admin/SessionDataExtension.html']


class ExportIndexExtension(ExportIndex):
    template_name = 'otreeutils/admin/ExportIndexExtension.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        collected_apps = set()
        app_info = []
        for session in Session.objects.all():
            for app_name in session.config['app_sequence']:
                if app_name in collected_apps:
                    continue

                try:
                    app_module = import_module(app_name)
                except:
                    app_module = None

                if app_module and hasattr(app_module, 'urls') and hasattr(app_module.urls, 'urlpatterns'):
                    for pttrn in app_module.urls.urlpatterns:
                        if pttrn.name == 'ExportApp' and pttrn.lookup_str.startswith('otreeutils.admin_extensions'):
                            uses_otreeutils_export = True
                            break
                    else:
                        uses_otreeutils_export = False

                app_info.append((app_name, uses_otreeutils_export))
                collected_apps.add(app_name)

        assert 'app_info' not in context
        context['app_info'] = app_info

        return context


class ExportAppExtension(ExportApp):
    @staticmethod
    def custom_columns_builder(custom_model_conf):
        columns_for_models = {name.lower(): get_field_names_for_custom_model(conf['class'], conf['export_data'],
                                                                             use_attname=True)
                              for name, conf in custom_model_conf.items()}

        return columns_for_models

    @classmethod
    def get_data_rows_for_app(cls, app_name):
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
        models_module = get_models_module(app_name)
        Player = models_module.Player
        Group = models_module.Group
        Subsession = models_module.Subsession

        custom_models_conf = get_custom_models_conf(models_module, 'export_data')

        columns_for_models = {m.__name__.lower(): get_field_names_for_csv(m)
                              for m in [Player, Group, Subsession, Participant, Session]}

        columns_for_custom_models = cls.custom_columns_builder(custom_models_conf)

        custom_models_links = defaultdict(list)
        std_models_select_related = defaultdict(list)
        for model_name, conf in custom_models_conf.items():
            model = conf['class']
            link_field_name = conf['export_data']['link_with']
            link_field = getattr(model, link_field_name)
            rel_model = link_field.field.related_model
            custom_models_links[rel_model.__name__].append((conf['class'], link_field_name + '_id'))
            std_models_select_related[rel_model.__name__.lower()].append(model_name.lower())

        participant_ids = Player.objects.values_list('participant_id', flat=True)
        session_ids = Subsession.objects.values_list('session_id', flat=True)

        qs_player = Player.objects.filter(session_id__in=session_ids)\
            .order_by('id')\
            .select_related(*std_models_select_related.get('player', [])).values()
        qs_group = Group.objects.filter(session_id__in=session_ids)\
            .select_related(*std_models_select_related.get('group', []))
        qs_subsession = Subsession.objects.filter(session_id__in=session_ids)\
            .select_related(*std_models_select_related.get('subsession', []))

        prefetch_participants = defaultdict(list)        # session ID -> participant rows
        for row in Participant.objects.filter(id__in=participant_ids).values():
            prefetch_participants[row['session_id']].append(row)

        prefetch_filter_ids_for_custom_models = {}

        # session ID -> subsession rows for this session
        prefetch_subsess = _rows_per_key_from_queryset(qs_subsession, 'session_id')
        prefetch_filter_ids_for_custom_models['subsession'] = _set_of_ids_from_rows_per_key(prefetch_subsess, 'id')

        # subsession ID -> group rows for this subsession
        prefetch_group = _rows_per_key_from_queryset(qs_group, 'subsession_id')
        prefetch_filter_ids_for_custom_models['group'] = _set_of_ids_from_rows_per_key(prefetch_group, 'id')

        # group ID -> player rows for this group
        prefetch_player = _rows_per_key_from_queryset(qs_player, 'group_id')
        prefetch_filter_ids_for_custom_models['player'] = _set_of_ids_from_rows_per_key(prefetch_player, 'id')

        prefetch_custom = defaultdict(dict)
        for otree_model_name, custom_modellist_for_otree_model in custom_models_links.items():
            otree_model_name_lwr = otree_model_name.lower()
            filter_ids = prefetch_filter_ids_for_custom_models[otree_model_name_lwr]

            for model, link_field_name in custom_modellist_for_otree_model:
                filter_kwargs = {link_field_name + '__in': filter_ids}
                custom_qs = model.objects.filter(**filter_kwargs).values()
                m = model.__name__.lower()
                prefetch_custom[otree_model_name_lwr][m] = _rows_per_key_from_queryset(custom_qs, link_field_name)

        output_nested = []
        ordered_columns_per_model = OrderedDict()
        for sess in Session.objects.filter(id__in=session_ids).values():
            sess_cols = columns_for_models['session']
            if 'session' not in ordered_columns_per_model:
                ordered_columns_per_model['session'] = sess_cols

            out_sess = _odict_from_row(sess, sess_cols)

            out_sess['__participant'] = []
            for part in prefetch_participants[sess['id']]:
                part_cols = columns_for_models['participant']

                if 'participant' not in ordered_columns_per_model:
                    ordered_columns_per_model['participant'] = part_cols

                out_part = _odict_from_row(part, part_cols)
                out_sess['__participant'].append(out_part)

            out_sess['__subsession'] = []
            for subsess in prefetch_subsess[sess['id']]:
                subsess_cols = columns_for_models['subsession']
                if 'subsession' not in ordered_columns_per_model:
                    ordered_columns_per_model['subsession'] = subsess_cols

                out_subsess = _odict_from_row(subsess, subsess_cols)

                subsess_custom_models_rows = prefetch_custom.get('subsession', {})
                for subsess_cmodel_name, subsess_cmodel_rows in subsess_custom_models_rows.items():
                    cmodel_cols = columns_for_custom_models[subsess_cmodel_name]
                    if subsess_cmodel_name not in ordered_columns_per_model:
                        ordered_columns_per_model[subsess_cmodel_name] = cmodel_cols

                    out_subsess['__' + subsess_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                               for cmodel_row in subsess_cmodel_rows[subsess['id']]]
                out_subsess['__group'] = []
                for grp in prefetch_group[subsess['id']]:
                    grp_cols = columns_for_models['group']
                    if 'group' not in ordered_columns_per_model:
                        ordered_columns_per_model['group'] = grp_cols

                    out_grp = _odict_from_row(grp, grp_cols)

                    grp_custom_models_rows = prefetch_custom.get('group', {})
                    for grp_cmodel_name, grp_cmodel_rows in grp_custom_models_rows.items():
                        cmodel_cols = columns_for_custom_models[grp_cmodel_name]
                        if grp_cmodel_name not in ordered_columns_per_model:
                            ordered_columns_per_model[grp_cmodel_name] = cmodel_cols

                        out_grp['__' + grp_cmodel_name] = [_odict_from_row(cmodel_row, cmodel_cols)
                                                           for cmodel_row in grp_cmodel_rows[grp['id']]]
                    out_grp['__player'] = []
                    for player in prefetch_player[grp['id']]:
                        # because player.payoff is a property
                        player['payoff'] = player['_payoff']

                        player_cols = columns_for_models['player']
                        if 'player' not in ordered_columns_per_model:
                            ordered_columns_per_model['player'] = player_cols

                        out_player = _odict_from_row(player, player_cols)

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

        columns_flat = []
        for model_name, model_cols in ordered_columns_per_model.items():
            columns_flat.extend(['.'.join((model_name, c)) for c in model_cols])

        if return_columns:
            return output_nested, columns_flat
        else:
            return output_nested

    def get(self, request, *args, **kwargs):
        app_name = kwargs['app_name']

        if not request.GET.get('custom'):
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

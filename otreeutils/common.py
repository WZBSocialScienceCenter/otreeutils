"""
Common (internal) utility functions.

Sept. 2018, Markus Konrad <markus.konrad@wzb.eu>
"""


from collections import OrderedDict


def hierarchical_data_columnwise(d, prefixes=(), prefixes_glue='.'):
    """
    Recursive function to flatten hierarchical data structure `d` by putting all nested keys and their values in an
    OrderedDict, which will be returned from this function.

    If `d` has a structure like this:
    ```
    [
        {
            'a': 1,
            'b': [
                {
                    'x': 2,
                    'y': 3,
                },
                {
                    'x': 4,
                    'y': 5,
                }
            ],
            'c': [
                {
                    'z': 6,
                }
            ]
        },
        {
            'a': 7,
            'b': [],
            'c': [
                {
                    'z': 8,
                },
                {
                    'z': 9,
                }
            ]
        },
    ]
    ```

    Then the result will be:

    ```
    OrderedDict([
        ('a',   [   1,     1,      1,      7,      7]),
        ('b.x', [   2,     4,   None,   None,   None]),
        ('b.y', [   3,     5,   None,   None,   None]),
        ('c.z', [None,  None,      6,      8,      9])
    ])
    ```

    This can be converted to a rowwise data structure with `columnwise_data_as_rows()`.

    :param d: nested data structure (lists with dicts with lists ...)
    :param prefixes: sequence of key prefixes (used during recursion)
    :param prefixes_glue: glue string to combine prefixes
    :return: OrderedDict with keys and values
    """

    # define key prefix
    prefix_str = prefixes_glue.join(prefixes)
    if prefix_str:  # append glue if we have a prefix at all
        prefix_str += prefixes_glue


    partial_res = []
    for obj in d:
        common_leafs = {}
        subbranches = []
        for k, v in obj.items():
            if isinstance(v, (list, tuple)):   # it goes deeper: v is another list of dicts
                if v:  # ignore empty subbranches
                    new_subbranch = hierarchical_data_columnwise(v, prefixes + (k,), prefixes_glue=prefixes_glue)
                    subbranches.append(new_subbranch)
            else:  # v is a leaf value
                assert prefix_str + k not in common_leafs, 'some element already exists in the leaf data'
                common_leafs[prefix_str + k] = [v]  # will extend this to match the overall value list length

        if not subbranches:  # leafs only
            subbranches.append({})

        for subbranch in subbranches:
            branch_res = OrderedDict()

            for k in obj.keys():
                pk = prefix_str + k
                if pk in common_leafs:
                    branch_res[pk] = common_leafs[pk]
                else:
                    for sk, sv in subbranch.items():
                        if sk.startswith(pk + prefixes_glue):
                            branch_res[sk] = sv

            # find value list length
            branch_val_lengths = set(n for n in map(len, branch_res.values()) if n != 1)
            if subbranch and branch_val_lengths:
                assert len(branch_val_lengths) == 1, 'sub-branches have different lengths'
                n_sub = branch_val_lengths.pop()
            else:
                n_sub = 1

            # extend leaf values to match the value list length
            branch_res_final = OrderedDict()
            for k, v in branch_res.items():
                if len(v) == 1:
                    branch_res_final[k] = v * n_sub
                else:
                    branch_res_final[k] = v

            partial_res.append(branch_res_final)

    # find all keys in the partial results (keep order -- otherwise we could simply use set())
    # these will form the keys of the final results
    res_keys = []
    for b in partial_res:
        for k in b.keys():
            if k not in res_keys:
                res_keys.append(k)

    # form final result: an OrderedDict with keys as columns and its value lists
    res = OrderedDict()
    for branch_res in partial_res:  # go through partial results
        branch_val_lengths = set(map(len, branch_res.values()))
        assert len(branch_val_lengths) == 1, 'sub-branches of partial result have different lengths'
        branch_len = branch_val_lengths.pop()

        for k in res_keys:  # go through all keys in *all* partial results
            if not k in res:   # initialize with empty value list
                res[k] = []

            # if there the key exists in this partial result, add these values
            # otherwise add list of None values of the same length
            res[k].extend(branch_res.get(k, [None] * branch_len))

    return res


def columnwise_data_as_rows(colwise, with_header=True):
    """
    Transform column-wise data (as from `hierarchical_data_columnwise()` to row-wise data, optionally returning a
    "data header" (i.e. keys/column names).

    :param colwise: column-wise data -- dict with keys (column names) and lists of values *with equal length*
    :param with_header: if True, return "data header" (i.e. keys/column names)
    :return: row-wise data (list of tuples) or tuple with (header, row-wise data)
    """
    vals = colwise.values()

    if vals:
        lens = set(map(len, vals))
        if not len(lens) == 1:
            raise ValueError('all values in `colwise` must have the same length.')

    rows = list(zip(*vals))

    if not with_header:
        return rows
    else:
        return list(colwise.keys()), rows

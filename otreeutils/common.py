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
        branch_keys = [k for k, v in obj.items() if isinstance(v, list) and v]
        leaf_keys = [k for k, v in obj.items() if not isinstance(v, list)]
        for k in branch_keys:
            branch_res = hierarchical_data_columnwise(obj[k], prefixes + (k,), prefixes_glue=prefixes_glue)

            branch_val_lengths = set(map(len, branch_res.values()))
            assert len(branch_val_lengths) == 1
            n_sub = branch_val_lengths.pop()

            for l in leaf_keys:
                assert l not in branch_res
                branch_res[prefix_str + l] = [obj[l]] * n_sub

            partial_res.append(branch_res)

        if not branch_keys:  # only leafs -> add all
            #partial_res.append(OrderedDict((prefix_str + k, [v if v else None]) for k, v in obj.items()))
            partial_res.append(OrderedDict((prefix_str + k, [obj[k]]) for k in leaf_keys))

    res_keys = []
    for b in partial_res:
        for k in b.keys():
            if k not in res_keys:
                res_keys.append(k)

    res = OrderedDict()
    for branch_res in partial_res:
        branch_val_lengths = set(map(len, branch_res.values()))
        assert len(branch_val_lengths) == 1
        branch_len = branch_val_lengths.pop()

        for k in res_keys:
            if not k in res:
                res[k] = []

            res[k].extend(branch_res.get(k, [None] * branch_len))

    return res


def columnwise_data_as_rows(colwise, with_header=True):
    rows = list(zip(*colwise.values()))
    if not with_header:
        return rows
    else:
        return rows, list(colwise.keys())

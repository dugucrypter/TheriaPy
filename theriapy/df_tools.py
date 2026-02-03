import pandas as pd


def add_nosort(df1: pd.DataFrame,
               df2: pd.DataFrame,
               include_df2_extras: bool = True,
               numeric_only: bool = True) -> pd.DataFrame:
    """
    Add df2 into df1 without re-sorting labels. Missing rows/cols treated as 0.
    Order: keep df1's index/columns first, then append any new ones from df2.

    Parameters
    ----------
    include_df2_extras : if True, include rows present only in df2 (at the end)
    numeric_only       : if True, only add numeric columns; others are ignored
    """
    # Desired column & index order
    cols = list(df1.columns) + [c for c in df2.columns if c not in df1.columns]
    if include_df2_extras:
        idx = list(df1.index) + [i for i in df2.index if i not in df1.index]
    else:
        idx = list(df1.index)

    if numeric_only:
        df1n = df1.select_dtypes(include="number")
        df2n = df2.select_dtypes(include="number")
        num_cols = [c for c in cols if c in set(df1n.columns).union(df2n.columns)]
        out = (df1n.reindex(index=idx, columns=num_cols, fill_value=0)
                    .add(df2n.reindex(index=idx, columns=num_cols, fill_value=0),
                         fill_value=0))
        return out.reindex(columns=num_cols)
    else:
        return (df1.reindex(index=idx, columns=cols)
                   .add(df2.reindex(index=idx, columns=cols), fill_value=0)
                   .reindex(columns=cols))

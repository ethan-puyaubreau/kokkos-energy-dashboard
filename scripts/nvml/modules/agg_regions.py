import pandas as pd

def aggregate_regions(files):
    dfs = [pd.read_csv(f) for f in files]
    df_concat = pd.concat(dfs, ignore_index=True)
    return df_concat

import pandas as pd
import sys

def group_by_time_window(df, time_col, window_ms):
    df = df.copy()
    df['window'] = (df[time_col] // window_ms) * window_ms
    grouped = df.groupby('window').agg({
        time_col: 'mean',
        **{col: 'mean' for col in df.columns if col != time_col and col != 'window'}
    }).reset_index(drop=True)
    cols = [time_col] + [c for c in grouped.columns if c != time_col]
    return grouped[cols]

def aggregate_csv(files, time_col=None, time_window_ms=20):
    dfs = [pd.read_csv(f) for f in files]
    df_concat = pd.concat(dfs, ignore_index=True)
    if time_col:
        return group_by_time_window(df_concat, time_col, time_window_ms)
    else:
        return df_concat.groupby(df_concat.columns[0]).mean().reset_index()

def aggregate_dat(files):
    dfs = []
    for f in files:
        with open(f, 'r') as file:
            lines = file.readlines()[1:]
        data = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                try:
                    data[key] = float(value.strip())
                except ValueError:
                    print(f"WARNING: Could not convert '{value.strip()}' to float for key '{key}' in file '{f}'. Skipping this value.", file=sys.stderr)
                    continue
        if data:
            dfs.append(pd.DataFrame([data]))
    if not dfs:
        return pd.DataFrame(columns=['stat_name', 'value'])
    df_concat = pd.concat(dfs, ignore_index=True)
    df_mean = df_concat.mean(numeric_only=True).reset_index()
    df_mean.columns = ['stat_name', 'value']
    return df_mean

import os
import pandas as pd
from glob import glob
import numpy as np
import sys

INPUT_DIR = 'input/variorum'
OUTPUT_DIR = 'data/variorum'

PATTERNS = {
    'variorum_relative': '*-variorum-power-relative.csv',
    'variorum_absolute': '*-variorum-power.csv',
    'variorum_gpus': '*-variorum-power-gpus.csv',
    'variorum_kernels': '*-variorum-power-kernels.csv',
    'variorum_stats': '*-variorum-power.dat',
}

OUTPUT_FILES = {
    'variorum_relative': 'variorum_relative.csv',
    'variorum_absolute': 'variorum_absolute.csv',
    'variorum_gpus': 'variorum_gpus.csv',
    'variorum_kernels': 'variorum_kernels.csv',
    'variorum_stats': 'variorum_stats.csv',
}

TIME_WINDOW_MS = 20

def group_by_time_window(df, time_col, window_ms):
    df = df.copy()
    df['window'] = (df[time_col] // window_ms) * window_ms
    grouped = df.groupby('window').agg({
        time_col: 'mean',
        **{col: 'mean' for col in df.columns if col != time_col and col != 'window'}
    }).reset_index(drop=True)
    cols = [time_col] + [c for c in grouped.columns if c != time_col]
    return grouped[cols]

def aggregate_csv(files, time_col=None):
    dfs = [pd.read_csv(f) for f in files]
    df_concat = pd.concat(dfs, ignore_index=True)
    if time_col:
        return group_by_time_window(df_concat, time_col, TIME_WINDOW_MS)
    else:
        return df_concat.groupby(df_concat.columns[0]).mean().reset_index()

def aggregate_gpus_csv(files):
    dfs = [pd.read_csv(f) for f in files]
    df_concat = pd.concat(dfs, ignore_index=True)
    df_concat['timestamp_ms'] = df_concat['timestamp_nanoseconds'] / 1_000_000
    df_concat['window'] = (df_concat['timestamp_ms'] // TIME_WINDOW_MS) * TIME_WINDOW_MS
    grouped = df_concat.groupby(['window', 'device_id']).agg({
        'timestamp_ms': 'mean',
        'power_watts': 'mean'
    }).reset_index()
    return grouped[['timestamp_ms', 'power_watts', 'device_id']]

def aggregate_kernels_csv(files):
    dfs = [pd.read_csv(f) for f in files]
    df_concat = pd.concat(dfs, ignore_index=True)
    df_concat['start_time_ms'] = df_concat['start_time_ns'] / 1_000_000
    df_concat['end_time_ms'] = df_concat['end_time_ns'] / 1_000_000
    df_concat['duration_ms'] = df_concat['duration_ns'] / 1_000_000
    return df_concat[['kernel_id', 'name', 'type', 'start_time_ms', 'end_time_ms', 'duration_ms']]

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

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    found_any = False
    
    for key, pattern in PATTERNS.items():
        files = glob(os.path.join(INPUT_DIR, '**', pattern), recursive=True)
        if not files:
            print(f'WARNING: No files found for {key} in {INPUT_DIR}', file=sys.stderr)
            continue
        found_any = True
        
        df = None
        if key == 'variorum_stats':
            df = aggregate_dat(files)
        elif key == 'variorum_relative':
            df = aggregate_csv(files, time_col='time_relative_ms')
        elif key == 'variorum_absolute':
            df = aggregate_csv(files, time_col='timestamp_system_epoch_ms')
        elif key == 'variorum_gpus':
            df = aggregate_gpus_csv(files)
        elif key == 'variorum_kernels':
            df = aggregate_kernels_csv(files)
        
        if df is not None and not df.empty:
            out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES[key])
            df.to_csv(out_path, index=False)
            print(f'Wrote {out_path} with {len(df)} rows.')
        elif df is not None and df.empty:
            print(f'INFO: No aggregated data for {key}. Output file not created.', file=sys.stderr)
    
    if not found_any:
        print(f'WARNING: No input data found for {INPUT_DIR}. Skipping aggregation.', file=sys.stderr)

if __name__ == '__main__':
    main()
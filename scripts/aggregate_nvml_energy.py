import os
import pandas as pd
from glob import glob
import numpy as np
import sys

INPUT_DIR = 'input/nvml_energy'
OUTPUT_DIR = 'data/nvml_energy'

PATTERNS = {
    'nvml_energy_relative': '*-nvml-energy-relative.csv',
    'nvml_energy_absolute': '*-nvml-energy.csv',
    'nvml_energy_stats': '*-nvml-energy.dat',
}

OUTPUT_FILES = {
    'nvml_energy_relative': 'nvml_energy_relative.csv',
    'nvml_energy_absolute': 'nvml_energy_absolute.csv',
    'nvml_energy_stats': 'nvml_energy_stats.csv',
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
        if key == 'nvml_energy_stats':
            df = aggregate_dat(files)
        elif key == 'nvml_energy_relative':
            df = aggregate_csv(files, time_col='time_relative_ms')
        elif key == 'nvml_energy_absolute':
            df = aggregate_csv(files, time_col='timestamp_system_epoch_ms')

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
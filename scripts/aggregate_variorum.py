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
    'variorum_series': 'variorum_series.csv',
}

TIME_WINDOW_MS = 100

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

def create_variorum_series_from_aggregated(gpus_csv, kernels_csv):
    import pandas as pd
    gpu_data = pd.read_csv(gpus_csv)
    kernel_data = pd.read_csv(kernels_csv)
    kernel_data['col_id'] = kernel_data.apply(
        lambda row: f"{row['name']}__{int(row['start_time_ms'])}_{int(row['end_time_ms'])}", axis=1)
    kernel_instances = kernel_data[['name', 'start_time_ms', 'end_time_ms', 'col_id']]
    result_rows = []
    for _, gpu_row in gpu_data.iterrows():
        timestamp = gpu_row['timestamp_ms']
        power = gpu_row['power_watts']
        row = {'time': timestamp}
        for _, k_row in kernel_instances.iterrows():
            col = k_row['col_id']
            if k_row['start_time_ms'] <= timestamp <= k_row['end_time_ms']:
                row[col] = power
            else:
                row[col] = None
        result_rows.append(row)
    result_df = pd.DataFrame(result_rows)
    if not result_df.empty:
        min_time = result_df['time'].min()
        result_df['time'] = result_df['time'] - min_time
    return result_df

def generate_variorum_series_sql(df, output_dir):
    if df.empty:
        return
    columns = df.columns.tolist()
    time_col = columns[0]
    kernel_cols = columns[1:]
    def clean_col(name):
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in name.replace(' ', '_').replace('[', '_').replace(']', '_').replace('-', '_').replace('.', '_'))
    sql_kernel_cols = [clean_col(k) for k in kernel_cols]
    sql_content = "-- Auto-generated SQL for variorum_series table\n"
    sql_content += "DROP TABLE IF EXISTS variorum_series;\n"
    sql_content += "CREATE TABLE variorum_series (\n"
    sql_content += "    time_ms DECIMAL(18,3) NOT NULL"
    for col in sql_kernel_cols:
        sql_content += f",\n    {col} DECIMAL(12,6)"
    sql_content += "\n);\n\n"
    sql_content += f"\\COPY variorum_series FROM '/csv_data/variorum/variorum_series.csv' WITH (FORMAT csv, HEADER true);\n\n"
    where_clause = ' OR '.join([f"{col} != 0" for col in sql_kernel_cols])
    sql_content += f"-- Select only rows where at least one kernel column is nonzero\n"
    sql_content += f"SELECT * FROM variorum_series WHERE {where_clause};\n\n"
    sql_content += "-- Fonction dynamique pour sélectionner toutes les lignes où au moins une colonne kernel est différente de 0\n"
    sql_content += "CREATE OR REPLACE FUNCTION select_variorum_nonzero()\n"
    sql_content += "RETURNS SETOF variorum_series AS $$\n"
    sql_content += "DECLARE\n"
    sql_content += "    col_list text;\n"
    sql_content += "    dyn_sql text;\n"
    sql_content += "BEGIN\n"
    sql_content += "    SELECT string_agg(format('%I != 0', column_name), ' OR ')\n"
    sql_content += "    INTO col_list\n"
    sql_content += "    FROM information_schema.columns\n"
    sql_content += "    WHERE table_name = 'variorum_series'\n"
    sql_content += "      AND column_name != 'time_ms';\n"
    sql_content += "    dyn_sql := format('SELECT * FROM variorum_series WHERE %s', col_list);\n"
    sql_content += "    RETURN QUERY EXECUTE dyn_sql;\n"
    sql_content += "END;\n"
    sql_content += "$$ LANGUAGE plpgsql;\n\n"
    sql_content += "-- Utilisation :\n-- SELECT * FROM select_variorum_nonzero();\n"
    sql_path = os.path.join(output_dir, 'variorum_series.sql')
    with open(sql_path, 'w') as f:
        f.write(sql_content)
    print(f'Generated SQL schema: {sql_path}')

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    found_any = False
    gpu_files = []
    kernel_files = []
    for key, pattern in PATTERNS.items():
        files = glob(os.path.join(INPUT_DIR, '**', pattern), recursive=True)
        if not files:
            print(f'WARNING: No files found for {key} in {INPUT_DIR}', file=sys.stderr)
            continue
        found_any = True
        if key == 'variorum_gpus':
            gpu_files = files
        elif key == 'variorum_kernels':
            kernel_files = files
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
    gpus_csv = os.path.join(OUTPUT_DIR, OUTPUT_FILES['variorum_gpus'])
    kernels_csv = os.path.join(OUTPUT_DIR, OUTPUT_FILES['variorum_kernels'])
    if os.path.exists(gpus_csv) and os.path.exists(kernels_csv):
        print("Creating variorum time series from aggregated files...")
        series_df = create_variorum_series_from_aggregated(gpus_csv, kernels_csv)
        if not series_df.empty:
            series_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES['variorum_series'])
            series_df.to_csv(series_path, index=False)
            print(f'Wrote {series_path} with {len(series_df)} rows.')
            generate_variorum_series_sql(series_df, OUTPUT_DIR)
        else:
            print('INFO: No time series data generated.', file=sys.stderr)
    else:
        print('WARNING: Cannot create time series - missing GPU or kernel data.', file=sys.stderr)
    if not found_any:
        print(f'WARNING: No input data found for {INPUT_DIR}. Skipping aggregation.', file=sys.stderr)

if __name__ == '__main__':
    main()
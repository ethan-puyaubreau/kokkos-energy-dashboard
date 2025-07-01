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
        if time_col in df_concat.columns:
            return group_by_time_window(df_concat, time_col, TIME_WINDOW_MS)
        elif 'timestamp_nanoseconds' in df_concat.columns:
            print(f"INFO: Using timestamp_nanoseconds instead of {time_col}")
            df_concat['timestamp_ms'] = df_concat['timestamp_nanoseconds'] / 1_000_000
            return group_by_time_window(df_concat, 'timestamp_ms', TIME_WINDOW_MS)
        else:
            print(f"ERROR: No timestamp column found. Available: {df_concat.columns.tolist()}")
            return pd.DataFrame()
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
                    print(f"WARNING: Cannot convert '{value.strip()}' to float for '{key}' in {f}", file=sys.stderr)
                    continue
        if data:
            dfs.append(pd.DataFrame([data]))
    
    if not dfs:
        return pd.DataFrame(columns=['stat_name', 'value'])
    df_concat = pd.concat(dfs, ignore_index=True)
    df_mean = df_concat.mean(numeric_only=True).reset_index()
    df_mean.columns = ['stat_name', 'value']
    return df_mean

def create_correlation_csv(power_files, region_file):
    regions_df = pd.read_csv(region_file)
    dfs = [pd.read_csv(f) for f in power_files]
    power_df = pd.concat(dfs, ignore_index=True)

    if 'timestamp_system_epoch_ms' in power_df.columns:
        power_df['timestamp_ns'] = (power_df['timestamp_system_epoch_ms'] * 1_000_000).astype('int64')
    elif 'timestamp_nanoseconds' in power_df.columns:
        power_df['timestamp_ns'] = power_df['timestamp_nanoseconds'].astype('int64')
    else:
        print("ERROR: No timestamp column found in power data")
        return pd.DataFrame()

    if 'variorum_power_watts' in power_df.columns:
        power_df['power_watts'] = power_df['variorum_power_watts']
    else:
        power_cols = [col for col in power_df.columns if 'power' in col.lower() and 'watts' in col.lower()]
        if power_cols:
            power_df['power_watts'] = power_df[power_cols[0]]
        else:
            print("ERROR: No power column found in data")
            return pd.DataFrame()

    if 'start_time_ns' not in regions_df.columns:
        print("ERROR: start_time_ns column not found in regions data")
        return pd.DataFrame()
    if 'end_time_ns' not in regions_df.columns:
        print("ERROR: end_time_ns column not found in regions data")
        return pd.DataFrame()

    regions_df['start_time_ns'] = regions_df['start_time_ns'].astype('int64')
    regions_df['end_time_ns'] = regions_df['end_time_ns'].astype('int64')

    region_counts = {}
    unique_region_names = []
    for _, row in regions_df.iterrows():
        base_name = row['name']
        if base_name not in region_counts:
            region_counts[base_name] = 0
        region_counts[base_name] += 1
        unique_name = f"{base_name}_{region_counts[base_name]}"
        unique_region_names.append(unique_name)
    
    regions_df['unique_name'] = unique_region_names

    correlation_data = []
    
    for idx, row in power_df.iterrows():
        timestamp = row['timestamp_ns']
        power_val = row['power_watts']
        
        active_regions = regions_df[
            (regions_df['start_time_ns'] <= timestamp) &
            (regions_df['end_time_ns'] >= timestamp)
        ]
        
        if len(active_regions) > 0:
            region_name = active_regions.iloc[0]['unique_name']
        else:
            region_name = "Unknown Region"
        
        correlation_data.append({
            'timestamp_nanoseconds': int(timestamp),
            'power_watts': power_val,
            'region_name': region_name
        })
    
    return pd.DataFrame(correlation_data)

def create_series_from_correlation(correlation_df):
    if correlation_df.empty:
        return pd.DataFrame()
    
    unique_regions = sorted(correlation_df['region_name'].unique())
    unique_times = sorted(correlation_df['timestamp_nanoseconds'].unique())
    unique_times = [int(t) for t in unique_times]

    result_df = pd.DataFrame({'time_ns': unique_times})
    
    for region in unique_regions:
        result_df[region] = None
    
    for idx, row in correlation_df.iterrows():
        timestamp = int(row['timestamp_nanoseconds'])
        region = row['region_name']
        power = row['power_watts']
        
        time_idx = result_df[result_df['time_ns'] == timestamp].index
        if len(time_idx) == 1:
            result_df.at[time_idx[0], region] = power
    
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
    sql_content += "    time_ns DECIMAL(18,3) NOT NULL"
    for col in sql_kernel_cols:
        sql_content += f",\n    {col} DECIMAL(12,6)"
    sql_content += "\n);\n\n"
    sql_content += f"\\COPY variorum_series FROM '/csv_data/variorum/variorum_series.csv' WITH (FORMAT csv, HEADER true);\n\n"
    where_clause = ' OR '.join([f"{col} IS NOT NULL" for col in sql_kernel_cols])
    sql_content += f"SELECT * FROM variorum_series WHERE {where_clause};\n\n"
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
    sql_content += "      AND column_name != 'time';\n"
    sql_content += "    dyn_sql := format('SELECT * FROM variorum_series WHERE %s', col_list);\n"
    sql_content += "    RETURN QUERY EXECUTE dyn_sql;\n"
    sql_content += "END;\n"
    sql_content += "$$ LANGUAGE plpgsql;\n\n"
    sql_path = os.path.join(output_dir, 'variorum_series.sql')
    with open(sql_path, 'w') as f:
        f.write(sql_content)
    print(f'Generated SQL schema: {sql_path}')

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
            df = aggregate_csv(files, time_col='timestamp_nanoseconds')
            if df.empty:
                df = aggregate_csv(files, time_col='timestamp_system_epoch_ms')
        elif key == 'variorum_gpus':
            df = aggregate_gpus_csv(files)
        elif key == 'variorum_kernels':
            df = aggregate_kernels_csv(files)
        
        if df is not None and not df.empty:
            out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES[key])
            df.to_csv(out_path, index=False)
            print(f'Wrote {out_path} with {len(df)} rows')
        elif df is not None and df.empty:
            print(f'INFO: No aggregated data for {key}', file=sys.stderr)
    
    if not found_any:
        print(f'WARNING: No input data found in {INPUT_DIR}', file=sys.stderr)

    power_files = glob(os.path.join(INPUT_DIR, '**', '*variorum-power.csv'), recursive=True)
    region_files = glob(os.path.join(INPUT_DIR, '**', '*regions.csv'), recursive=True)
    
    if power_files and region_files:
        print("Processing power and region correlation...")
        
        correlation_df = create_correlation_csv(power_files, region_files[0])
        if not correlation_df.empty:
            correlation_path = os.path.join(OUTPUT_DIR, 'correlation.csv')
            correlation_df.to_csv(correlation_path, index=False)
            print(f'Created correlation file: {correlation_path}')
            
            series_df = create_series_from_correlation(correlation_df)
            if not series_df.empty:
                series_path = os.path.join(OUTPUT_DIR, 'variorum_series.csv')
                series_df.to_csv(series_path, index=False)
                print(f'Created series file: {series_path}')
                
                sql_path = os.path.join(OUTPUT_DIR, 'variorum_series.sql')
                with open(sql_path, 'w') as f:
                    columns = series_df.columns.tolist()
                    
                    f.write("DROP TABLE IF EXISTS variorum_series;\n")
                    f.write("CREATE TABLE variorum_series (\n")
                    
                    column_definitions = []
                    for col in columns:
                        if col == 'time_ns':
                            column_definitions.append("    time_ns BIGINT")
                        else:
                            safe_col = col.replace(' ', '_').replace('-', '_').replace('.', '_')
                            column_definitions.append(f'    "{safe_col}" DOUBLE PRECISION')
                    
                    f.write(",\n".join(column_definitions))
                    f.write("\n);\n\n")
                    
                    f.write("\\COPY variorum_series FROM '/csv_data/variorum/variorum_series.csv' WITH (FORMAT csv, HEADER true);\n\n")
                    
                    f.write("CREATE OR REPLACE FUNCTION select_variorum_nonzero()\n")
                    f.write("RETURNS SETOF variorum_series AS $$\n")
                    f.write("DECLARE\n")
                    f.write("    col_list text;\n")
                    f.write("    dyn_sql text;\n")
                    f.write("BEGIN\n")
                    f.write("    SELECT string_agg(format('%I != 0', column_name), ' OR ')\n")
                    f.write("    INTO col_list\n")
                    f.write("    FROM information_schema.columns\n")
                    f.write("    WHERE table_name = 'variorum_series'\n")
                    f.write("      AND column_name != 'time_ns';\n")
                    f.write("    dyn_sql := format('SELECT * FROM variorum_series WHERE %s', col_list);\n")
                    f.write("    RETURN QUERY EXECUTE dyn_sql;\n")
                    f.write("END;\n")
                    f.write("$$ LANGUAGE plpgsql;\n")
                
                print(f'Created SQL file: {sql_path}')
            else:
                print("ERROR: Failed to create series data")
        else:
            print("ERROR: Failed to create correlation data")
    else:
        if not power_files:
            print("WARNING: No power files found for series generation")
        if not region_files:
            print("WARNING: No region files found for series generation")

if __name__ == '__main__':
    main()
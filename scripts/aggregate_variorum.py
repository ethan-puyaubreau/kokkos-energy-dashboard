import os
import pandas as pd
from glob import glob
import numpy as np
import sys

INPUT_DIR = 'input/variorum'
OUTPUT_DIR = 'data/variorum'
TIME_WINDOW_MS = 20

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
    'variorum_regions': 'variorum_regions.csv'
}

def load_and_concat_csvs(files):
    """Load and concatenate CSV files with error handling."""
    if not files:
        return pd.DataFrame()
    try:
        dfs = [pd.read_csv(f) for f in files]
        return pd.concat(dfs, ignore_index=True)
    except Exception as e:
        print(f"ERROR: Failed to load CSV files: {e}", file=sys.stderr)
        return pd.DataFrame()

def validate_columns(df, required_cols, context="data"):
    """Validate required columns exist in DataFrame."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"ERROR: Missing columns {missing} in {context}")
        return False
    return True

def convert_ns_to_ms(df, ns_cols):
    """Convert nanosecond columns to millisecond columns."""
    for ns_col in ns_cols:
        if ns_col in df.columns:
            ms_col = ns_col.replace('_ns', '_ms')
            df[ms_col] = df[ns_col] / 1_000_000
    return df

def group_by_time_window(df, time_col, window_ms):
    """Group data by time windows and aggregate."""
    df = df.copy()
    df['window'] = (df[time_col] // window_ms) * window_ms
    grouped = df.groupby('window').agg({
        time_col: 'mean',
        **{col: 'mean' for col in df.columns if col not in [time_col, 'window']}
    }).reset_index(drop=True)
    cols = [time_col] + [c for c in grouped.columns if c != time_col]
    return grouped[cols]

def process_timestamp_column(df, preferred_col):
    """Process timestamp columns with fallback logic."""
    if preferred_col in df.columns:
        return df, preferred_col
    elif 'timestamp_nanoseconds' in df.columns:
        print(f"INFO: Using timestamp_nanoseconds instead of {preferred_col}")
        df['timestamp_ms'] = df['timestamp_nanoseconds'] / 1_000_000
        return df, 'timestamp_ms'
    else:
        print(f"ERROR: No timestamp column found. Available: {df.columns.tolist()}")
        return df, None

def aggregate_standard_csv(files, time_col=None):
    """Standard CSV aggregation with optional time grouping."""
    df = load_and_concat_csvs(files)
    if df.empty:
        return df
    
    if time_col:
        df, actual_time_col = process_timestamp_column(df, time_col)
        if actual_time_col:
            return group_by_time_window(df, actual_time_col, TIME_WINDOW_MS)
        return pd.DataFrame()
    else:
        return df.groupby(df.columns[0]).mean().reset_index()

def aggregate_gpus_data(files):
    """Aggregate GPU power data with device grouping."""
    df = load_and_concat_csvs(files)
    if df.empty or not validate_columns(df, ['timestamp_nanoseconds', 'power_watts'], "GPU data"):
        return pd.DataFrame()
    
    df['timestamp_ms'] = df['timestamp_nanoseconds'] / 1_000_000
    df['window'] = (df['timestamp_ms'] // TIME_WINDOW_MS) * TIME_WINDOW_MS
    grouped = df.groupby(['window', 'device_id']).agg({
        'timestamp_ms': 'mean',
        'power_watts': 'mean'
    }).reset_index()
    return grouped[['timestamp_ms', 'power_watts', 'device_id']]

def aggregate_kernels_data(files):
    """Aggregate kernel timing data."""
    df = load_and_concat_csvs(files)
    if df.empty:
        return df
    
    ns_cols = ['start_time_ns', 'end_time_ns', 'duration_ns']
    if not validate_columns(df, ns_cols, "kernel data"):
        return pd.DataFrame()
    
    df = convert_ns_to_ms(df, ns_cols)
    return df[['kernel_id', 'name', 'type', 'start_time_ms', 'end_time_ms', 'duration_ms']]

def aggregate_stats_data(files):
    """Aggregate statistics from .dat files."""
    dfs = []
    for f in files:
        try:
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
        except Exception as e:
            print(f"WARNING: Failed to process {f}: {e}", file=sys.stderr)
    
    if not dfs:
        return pd.DataFrame(columns=['stat_name', 'value'])
    
    df_concat = pd.concat(dfs, ignore_index=True)
    df_mean = df_concat.mean(numeric_only=True).reset_index()
    df_mean.columns = ['stat_name', 'value']
    return df_mean

def aggregate_regions_data(files):
    """Aggregate region timing data."""
    df = load_and_concat_csvs(files)
    if df.empty:
        return df
    
    required_cols = ['start_time_ns', 'end_time_ns', 'name']
    if not validate_columns(df, required_cols, "region data"):
        return pd.DataFrame()
    
    df = convert_ns_to_ms(df, ['start_time_ns', 'end_time_ns'])
    return df[['name', 'start_time_ms', 'end_time_ms']]

def prepare_power_data(power_files):
    """Prepare power data with timestamp and power column standardization."""
    df = load_and_concat_csvs(power_files)
    if df.empty:
        return pd.DataFrame()

    # Standardize timestamp column
    if 'timestamp_system_epoch_ms' in df.columns:
        df['timestamp_ns'] = (df['timestamp_system_epoch_ms'] * 1_000_000).astype('int64')
    elif 'timestamp_nanoseconds' in df.columns:
        df['timestamp_ns'] = df['timestamp_nanoseconds'].astype('int64')
    else:
        print("ERROR: No timestamp column found in power data")
        return pd.DataFrame()

    # Standardize power column
    if 'variorum_power_watts' in df.columns:
        df['power_watts'] = df['variorum_power_watts']
    else:
        power_cols = [col for col in df.columns if 'power' in col.lower() and 'watts' in col.lower()]
        if power_cols:
            df['power_watts'] = df[power_cols[0]]
        else:
            print("ERROR: No power column found in data")
            return pd.DataFrame()

    return df

def prepare_regions_data(region_file):
    """Prepare regions data with unique naming."""
    try:
        regions_df = pd.read_csv(region_file)
    except Exception as e:
        print(f"ERROR: Failed to read region file {region_file}: {e}")
        return pd.DataFrame()

    required_cols = ['start_time_ns', 'end_time_ns', 'name', 'duration_ns']
    if not validate_columns(regions_df, required_cols, "regions data"):
        return pd.DataFrame()

    regions_df['start_time_ns'] = regions_df['start_time_ns'].astype('int64')
    regions_df['end_time_ns'] = regions_df['end_time_ns'].astype('int64')
    regions_df['duration_ns'] = regions_df['duration_ns'].astype('int64')

    # Create unique region names
    region_counts = {}
    unique_region_names = []
    for _, row in regions_df.iterrows():
        base_name = row['name']
        region_counts[base_name] = region_counts.get(base_name, 0) + 1
        unique_name = f"{base_name}_{region_counts[base_name]}"
        unique_region_names.append(unique_name)
    
    regions_df['unique_name'] = unique_region_names
    return regions_df

def create_correlation_data(power_files, region_file):
    """Create correlation between power data and regions."""
    power_df = prepare_power_data(power_files)
    regions_df = prepare_regions_data(region_file)
    
    if power_df.empty or regions_df.empty:
        return pd.DataFrame()

    correlation_data = []
    for _, row in power_df.iterrows():
        timestamp = row['timestamp_ns']
        power_val = row['power_watts']
        
        active_regions = regions_df[
            (regions_df['start_time_ns'] <= timestamp) &
            (regions_df['end_time_ns'] >= timestamp)
        ]
        
        region_name = active_regions.iloc[0]['unique_name'] if len(active_regions) > 0 else "Unknown Region"
        
        correlation_data.append({
            'timestamp_nanoseconds': int(timestamp),
            'power_watts': power_val,
            'region_name': region_name
        })
    
    return pd.DataFrame(correlation_data)

def create_time_series_data(correlation_df):
    """Create time series data with regions as columns."""
    if correlation_df.empty:
        return pd.DataFrame()
    
    unique_regions = sorted(correlation_df['region_name'].unique())
    unique_times = sorted([int(t) for t in correlation_df['timestamp_nanoseconds'].unique()])

    result_df = pd.DataFrame({'time_ns': unique_times})
    for region in unique_regions:
        result_df[region] = None
    
    for _, row in correlation_df.iterrows():
        timestamp = int(row['timestamp_nanoseconds'])
        region = row['region_name']
        power = row['power_watts']
        
        time_idx = result_df[result_df['time_ns'] == timestamp].index
        if len(time_idx) == 1:
            result_df.at[time_idx[0], region] = power
    
    return result_df

def generate_sql_schema(series_df, output_dir):
    """Generate SQL schema for time series data."""
    if series_df.empty:
        return
    
    sql_path = os.path.join(output_dir, 'variorum_series.sql')
    columns = series_df.columns.tolist()
    
    with open(sql_path, 'w') as f:
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

def process_standard_aggregation():
    """Process standard file aggregation patterns."""
    aggregation_map = {
        'variorum_stats': aggregate_stats_data,
        'variorum_relative': lambda files: aggregate_standard_csv(files, 'time_relative_ms'),
        'variorum_absolute': lambda files: aggregate_standard_csv(files, 'timestamp_nanoseconds').pipe(
    lambda df: df if not df.empty else aggregate_standard_csv(files, 'timestamp_system_epoch_ms')
),
        'variorum_gpus': aggregate_gpus_data,
        'variorum_kernels': aggregate_kernels_data,
    }
    
    found_any = False
    for key, pattern in PATTERNS.items():
        files = glob(os.path.join(INPUT_DIR, '**', pattern), recursive=True)
        if not files:
            print(f'WARNING: No files found for {key} in {INPUT_DIR}', file=sys.stderr)
            continue
        
        found_any = True
        df = aggregation_map[key](files)
        
        if not df.empty:
            out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES[key])
            df.to_csv(out_path, index=False)
            print(f'Wrote {out_path} with {len(df)} rows')
        else:
            print(f'INFO: No aggregated data for {key}', file=sys.stderr)
    
    return found_any

def process_regions_aggregation():
    """Process region file aggregation."""
    region_files = glob(os.path.join(INPUT_DIR, '**', '*regions.csv'), recursive=True)
    if region_files:
        print("Creating region CSV...")
        df = aggregate_regions_data(region_files)
        if not df.empty:
            out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES['variorum_regions'])
            df.to_csv(out_path, index=False)
            print(f'Wrote {out_path} with {len(df)} rows')

def process_correlation_and_series():
    """Process power-region correlation and time series generation."""
    power_files = glob(os.path.join(INPUT_DIR, '**', '*variorum-power.csv'), recursive=True)
    region_files = glob(os.path.join(INPUT_DIR, '**', '*regions.csv'), recursive=True)
    
    if not power_files:
        print("WARNING: No power files found for series generation")
        return
    if not region_files:
        print("WARNING: No region files found for series generation")
        return

    print("Processing power and region correlation...")
    
    correlation_df = create_correlation_data(power_files, region_files[0])
    if correlation_df.empty:
        print("ERROR: Failed to create correlation data")
        return

    correlation_path = os.path.join(OUTPUT_DIR, 'correlation.csv')
    correlation_df.to_csv(correlation_path, index=False)
    print(f'Created correlation file: {correlation_path}')
    
    series_df = create_time_series_data(correlation_df)
    if series_df.empty:
        print("ERROR: Failed to create series data")
        return

    series_path = os.path.join(OUTPUT_DIR, 'variorum_series.csv')
    series_df.to_csv(series_path, index=False)
    print(f'Created series file: {series_path}')
    
    generate_sql_schema(series_df, OUTPUT_DIR)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    found_any = process_standard_aggregation()
    process_regions_aggregation()
    
    if not found_any:
        print(f'WARNING: No input data found in {INPUT_DIR}', file=sys.stderr)
    
    process_correlation_and_series()

if __name__ == '__main__':
    main()
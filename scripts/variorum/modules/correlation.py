import os
import pandas as pd
from modules.utils import load_and_concat_csvs, validate_columns

def prepare_power_data(power_files):
    df = load_and_concat_csvs(power_files)
    if df.empty:
        return pd.DataFrame()
    if 'timestamp_system_epoch_ms' in df.columns:
        df['timestamp_ns'] = (df['timestamp_system_epoch_ms'] * 1_000_000).astype('int64')
    elif 'timestamp_nanoseconds' in df.columns:
        df['timestamp_ns'] = df['timestamp_nanoseconds'].astype('int64')
    else:
        print("ERROR: No timestamp column found in power data")
        return pd.DataFrame()
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
    power_df = prepare_power_data(power_files)
    regions_df = prepare_regions_data(region_file)
    if power_df.empty or regions_df.empty:
        return pd.DataFrame()
    correlation_data = []
    for _, row in power_df.iterrows():
        timestamp = row['timestamp_ns']
        power_val = row['power_watts']
        active_regions = regions_df[(regions_df['start_time_ns'] <= timestamp) & (regions_df['end_time_ns'] >= timestamp)]
        region_name = active_regions.iloc[0]['unique_name'] if len(active_regions) > 0 else "Unknown Region"
        correlation_data.append({
            'timestamp_nanoseconds': int(timestamp),
            'power_watts': power_val,
            'region_name': region_name
        })
    return pd.DataFrame(correlation_data)

def create_time_series_data(correlation_df):
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

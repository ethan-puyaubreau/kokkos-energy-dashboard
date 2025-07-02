import os
import pandas as pd

def create_correlation_data(power_files, region_file):
    power_relative_file = None
    for f in power_files:
        if 'relative' in f:
            power_relative_file = f
            break
    
    if not power_relative_file:
        print("ERROR: No relative power file found for correlation")
        return pd.DataFrame()
    
    power_df = pd.read_csv(power_relative_file)
    regions_df = pd.read_csv(region_file)
    
    name_counts = {}
    unique_names = []
    for _, row in regions_df.iterrows():
        name = row['name']
        if name in name_counts:
            name_counts[name] += 1
            unique_name = f"{name}_{name_counts[name]}"
        else:
            name_counts[name] = 1
            unique_name = f"{name}_1"
        unique_names.append(unique_name)
    
    regions_df['unique_name'] = unique_names
    correlation_data = []
    
    for _, row in power_df.iterrows():
        timestamp_ms = row['time_relative_ms']
        timestamp_ns = timestamp_ms * 1_000_000
        power = row['power_watts']
        
        active_regions = regions_df[(regions_df['start_time_ns'] <= timestamp_ns) & (regions_df['end_time_ns'] >= timestamp_ns)]
        region_name = active_regions.iloc[0]['unique_name'] if len(active_regions) > 0 else 'Unknown Region'
        
        correlation_data.append({
            'timestamp_nanoseconds': timestamp_ns,
            'power_watts': power,
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

def generate_sql_schema(series_df, output_dir, table_name='nvml_series'):
    if series_df.empty:
        return
    sql_path = os.path.join(output_dir, f'{table_name}.sql')
    columns = series_df.columns.tolist()
    with open(sql_path, 'w') as f:
        f.write(f"DROP TABLE IF EXISTS {table_name};\n")
        f.write(f"CREATE TABLE {table_name} (\n")
        column_definitions = []
        for col in columns:
            if col == 'time_ns':
                column_definitions.append("    time_ns BIGINT")
            else:
                safe_col = col.replace(' ', '_').replace('-', '_').replace('.', '_')
                column_definitions.append(f'    "{safe_col}" DOUBLE PRECISION')
        f.write(",\n".join(column_definitions))
        f.write("\n);\n\n")
        f.write(f"\\COPY {table_name} FROM '/csv_data/nvml_power/{table_name}.csv' WITH (FORMAT csv, HEADER true);\n\n")
        f.write(f"CREATE OR REPLACE FUNCTION select_{table_name}_nonzero()\n")
        f.write(f"RETURNS SETOF {table_name} AS $$\n")
        f.write("DECLARE\n")
        f.write("    col_list text;\n")
        f.write("    dyn_sql text;\n")
        f.write("BEGIN\n")
        f.write("    SELECT string_agg(format('%I != 0', column_name), ' OR ')\n")
        f.write(f"    INTO col_list\n")
        f.write(f"    FROM information_schema.columns WHERE table_name = '{table_name}';\n")
        f.write("    dyn_sql := format('SELECT * FROM " + table_name + " WHERE %s', col_list);\n")
        f.write("    RETURN QUERY EXECUTE dyn_sql;\n")
        f.write("END;\n")
        f.write("$$ LANGUAGE plpgsql;\n")

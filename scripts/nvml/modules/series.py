import pandas as pd

def create_power_series(power_files, region_file):
    power_df = pd.read_csv(power_files[0])
    regions_df = pd.read_csv(region_file)
    series = []
    for _, row in power_df.iterrows():
        timestamp = int(row['timestamp_system_epoch_ms'])
        power = row['nvml_power_watts']
        active_regions = regions_df[(regions_df['start_time_ns'] <= timestamp*1_000_000) & (regions_df['end_time_ns'] >= timestamp*1_000_000)]
        region_name = active_regions.iloc[0]['name'] if len(active_regions) > 0 else 'Unknown Region'
        series.append({'time_ms': timestamp, region_name: power})
    df = pd.DataFrame(series)
    df = df.groupby('time_ms').first().reset_index()
    df = df.pivot_table(index='time_ms', values=df.columns[1:], aggfunc='first').reset_index()
    return df

import pandas as pd

def create_energy_series(energy_files, region_file):
    energy_df = pd.read_csv(energy_files[0])
    regions_df = pd.read_csv(region_file)
    series = []
    for _, row in energy_df.iterrows():
        timestamp = int(row['timestamp_system_epoch_ms'])
        energy = row['nvml_joules_energy']
        active_regions = regions_df[(regions_df['start_time_ns'] <= timestamp*1_000_000) & (regions_df['end_time_ns'] >= timestamp*1_000_000)]
        region_name = active_regions.iloc[0]['name'] if len(active_regions) > 0 else 'Unknown Region'
        series.append({'time_ms': timestamp, region_name: energy})
    df = pd.DataFrame(series)
    df = df.groupby('time_ms').first().reset_index()
    df = df.pivot_table(index='time_ms', values=df.columns[1:], aggfunc='first').reset_index()
    return df

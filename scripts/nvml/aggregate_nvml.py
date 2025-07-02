import os
import sys
from glob import glob
from modules.agg_relative import aggregate_relative
from modules.agg_absolute import aggregate_absolute
from modules.agg_stats import aggregate_stats
from modules.agg_regions import aggregate_regions
from modules.series import create_power_series
from modules.correlation import create_correlation_data, create_time_series_data, generate_sql_schema

INPUT_DIR = 'input/nvml_power'
OUTPUT_DIR = 'data/nvml_power'

PATTERNS = {
    'nvml_relative': '*-nvml-power-relative.csv',
    'nvml_absolute': '*-nvml-power.csv',
    'nvml_stats': '*-nvml-power.dat',
    'nvml_regions': '*-nvml-regions.csv',
}

OUTPUT_FILES = {
    'nvml_relative': 'nvml_relative.csv',
    'nvml_absolute': 'nvml_absolute.csv',
    'nvml_stats': 'nvml_stats.csv',
    'nvml_regions': 'nvml_regions.csv',
}

def process_series():
    power_files = glob(os.path.join(INPUT_DIR, '**', '*-nvml-power*.csv'), recursive=True)
    region_files = glob(os.path.join(INPUT_DIR, '**', '*-nvml-regions.csv'), recursive=True)
    if not power_files or not region_files:
        print('WARNING: Missing files for nvml series generation')
        return
    print('Processing NVML power series by region...')
    correlation_df = create_correlation_data(power_files, region_files[0])
    if correlation_df.empty:
        print('ERROR: Failed to create NVML correlation data')
        return
    correlation_path = os.path.join(OUTPUT_DIR, 'nvml_correlation.csv')
    correlation_df.to_csv(correlation_path, index=False)
    print(f'Created NVML correlation file: {correlation_path}')
    series_df = create_time_series_data(correlation_df)
    if series_df.empty:
        print('ERROR: Failed to create NVML series data')
        return
    out_path = os.path.join(OUTPUT_DIR, 'nvml_series.csv')
    series_df.to_csv(out_path, index=False)
    print(f'Created NVML series file: {out_path}')
    generate_sql_schema(series_df, OUTPUT_DIR, table_name='nvml_series')

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    found_any = False
    for key, pattern in PATTERNS.items():
        files = glob(os.path.join(INPUT_DIR, '**', pattern), recursive=True)
        if not files:
            print(f'WARNING: No files found for {key}', file=sys.stderr)
            continue
        found_any = True
        if key == 'nvml_stats':
            df = aggregate_stats(files)
        elif key == 'nvml_relative':
            df = aggregate_relative(files)
        elif key == 'nvml_absolute':
            df = aggregate_absolute(files)
        elif key == 'nvml_regions':
            df = aggregate_regions(files)
        else:
            continue
        out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES[key])
        df.to_csv(out_path, index=False)
        print(f'Wrote {out_path}')
    if not found_any:
        print('WARNING: No input data found for nvml_power. Skipping aggregation.', file=sys.stderr)
    process_series()

if __name__ == '__main__':
    main()
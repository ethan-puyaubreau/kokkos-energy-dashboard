import os
import sys
from glob import glob
from modules.agg_relative import aggregate_relative
from modules.agg_absolute import aggregate_absolute
from modules.agg_stats import aggregate_stats
from modules.agg_regions import aggregate_regions
from modules.series import create_energy_series
from modules.correlation import create_correlation_data, create_time_series_data, generate_sql_schema

INPUT_DIR = 'input/nvml_energy'
OUTPUT_DIR = 'data/nvml_energy'

PATTERNS = {
    'nvml_energy_relative': '*-nvml-energy-relative.csv',
    'nvml_energy_absolute': '*-nvml-energy.csv',
    'nvml_energy_stats': '*-nvml-energy.dat',
    'nvml_energy_regions': '*-nvml-regions.csv',
}

OUTPUT_FILES = {
    'nvml_energy_relative': 'nvml_energy_relative.csv',
    'nvml_energy_absolute': 'nvml_energy_absolute.csv',
    'nvml_energy_stats': 'nvml_energy_stats.csv',
    'nvml_energy_regions': 'nvml_energy_regions.csv',
}

def process_series():
    energy_files = glob(os.path.join(INPUT_DIR, '**', '*-nvml-energy*.csv'), recursive=True)
    region_files = glob(os.path.join(INPUT_DIR, '**', '*-nvml-regions.csv'), recursive=True)
    if not energy_files or not region_files:
        print('WARNING: Missing files for nvml_energy series generation')
        return
    print('Processing NVML energy series by region...')
    correlation_df = create_correlation_data(energy_files, region_files[0])
    if correlation_df.empty:
        print('ERROR: Failed to create NVML energy correlation data')
        return
    correlation_path = os.path.join(OUTPUT_DIR, 'nvml_energy_correlation.csv')
    correlation_df.to_csv(correlation_path, index=False)
    print(f'Created NVML energy correlation file: {correlation_path}')
    series_df = create_time_series_data(correlation_df)
    if series_df.empty:
        print('ERROR: Failed to create NVML energy series data')
        return
    out_path = os.path.join(OUTPUT_DIR, 'nvml_energy_series.csv')
    series_df.to_csv(out_path, index=False)
    print(f'Created NVML energy series file: {out_path}')
    generate_sql_schema(series_df, OUTPUT_DIR, table_name='nvml_energy_series')

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
            df = aggregate_stats(files)
        elif key == 'nvml_energy_relative':
            df = aggregate_relative(files)
        elif key == 'nvml_energy_absolute':
            df = aggregate_absolute(files)
        elif key == 'nvml_energy_regions':
            df = aggregate_regions(files)
        if df is not None and not df.empty:
            out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILES[key])
            df.to_csv(out_path, index=False)
            print(f'Wrote {out_path} with {len(df)} rows.')
        elif df is not None and df.empty:
            print(f'INFO: No aggregated data for {key}. Output file not created.', file=sys.stderr)
    if not found_any:
        print(f'WARNING: No input data found for {INPUT_DIR}. Skipping aggregation.', file=sys.stderr)
    process_series()

if __name__ == '__main__':
    main()
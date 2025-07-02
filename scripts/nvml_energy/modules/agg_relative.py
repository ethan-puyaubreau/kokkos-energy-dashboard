from .utils import aggregate_csv

TIME_WINDOW_MS = 20

def aggregate_relative(files):
    return aggregate_csv(files, time_col='time_relative_ms', time_window_ms=TIME_WINDOW_MS)

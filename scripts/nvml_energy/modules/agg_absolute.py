from .utils import aggregate_csv

TIME_WINDOW_MS = 20

def aggregate_absolute(files):
    return aggregate_csv(files, time_col='timestamp_system_epoch_ms', time_window_ms=TIME_WINDOW_MS)

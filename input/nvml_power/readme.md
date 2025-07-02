Input folder for NVML Tool (Power Variant)

# Data Format:

`nvml-power-relative.csv` :
```
time_relative_ms,power_watts,energy_relative_joules
```

`nvml-power.csv` :
```
timestamp_system_epoch_ms,nvml_power_watts,nvml_integrated_energy_joules
```

`nvml-power.dat` :
```
# NVML Power Profiler Results
execution_time_seconds: value
total_integrated_energy_joules: value
final_power_watts: value
average_power_watts: value
min_power_watts: value
max_power_watts: value
average_measured_power_watts: value
num_power_measurements: value
```

`nvml-regions.csv` :
```
name,start_time_ns,end_time_ns,duration_ns
```

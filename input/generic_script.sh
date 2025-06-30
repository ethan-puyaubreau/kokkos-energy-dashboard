#!/bin/bash

# --- Configuration ---
NUM_ITERATIONS=1
COMMAND="YOUR KOKKOS PROGRAM COMMAND HERE"

# --- NVML Libraries ---
NVML_ENERGY_LIB="PATH TO KOKKOS NVML ENERGY LIBRARY HERE"
NVML_POWER_LIB="PATH TO KOKKOS NVML POWER LIBRARY HERE"

# --- Variorum Library ---
VARIORUM_ENERGY_LIB="PATH TO KOKKOS VARIORUM ENERGY LIBRARY HERE"
VARIORUM_DIR="YOUR VARIORUM INSTALL PATH HERE"

HOSTNAME=$(hostname)
OUTPUT_DIR_PREFIX="energy_bench"

run_nvml_energy() {
    for i in $(seq 1 $NUM_ITERATIONS); do
        BATCH_DIR="${OUTPUT_DIR_PREFIX}_nvml_energy_${i}"
        mkdir -p "$BATCH_DIR"
        echo "Running NVML Energy iteration $i... out of $NUM_ITERATIONS"
        KOKKOS_TOOLS_LIBS="$NVML_ENERGY_LIB" $COMMAND
        shopt -s nullglob
        mv ${HOSTNAME}* "$BATCH_DIR/" 2>/dev/null
        mkdir -p ./nvml_energy/
        mv ${BATCH_DIR} ./nvml_energy/ 2>/dev/null
        shopt -u nullglob
    done
}

run_nvml_power() {
    for i in $(seq 1 $NUM_ITERATIONS); do
        BATCH_DIR="${OUTPUT_DIR_PREFIX}_nvml_power_${i}"
        mkdir -p "$BATCH_DIR"
        echo "Running NVML Power iteration $i... out of $NUM_ITERATIONS"
        KOKKOS_TOOLS_LIBS="$NVML_POWER_LIB" $COMMAND
        shopt -s nullglob
        mv ${HOSTNAME}* "$BATCH_DIR/" 2>/dev/null
        mkdir -p ./nvml_power/
        mv ${BATCH_DIR} ./nvml_power/ 2>/dev/null
        shopt -u nullglob
    done
}

run_variorum_power() {
    for i in $(seq 1 $NUM_ITERATIONS); do
        BATCH_DIR="${OUTPUT_DIR_PREFIX}_variorum_power_${i}"
        mkdir -p "$BATCH_DIR"
        echo "Running Variorum Power iteration $i... out of $NUM_ITERATIONS"
        LD_LIBRARY_PATH="$VARIORUM_DIR/lib:$LD_LIBRARY_PATH" KOKKOS_TOOLS_LIBS="$VARIORUM_ENERGY_LIB" $COMMAND
        shopt -s nullglob
        mv ${HOSTNAME}* "$BATCH_DIR/" 2>/dev/null
        mkdir -p ./variorum/
        mv ${BATCH_DIR} ./variorum/ 2>/dev/null
        shopt -u nullglob
    done
}

echo "Starting EnergyBench runs..."
run_nvml_energy
run_nvml_power
run_variorum_power
echo "All EnergyBench runs completed."
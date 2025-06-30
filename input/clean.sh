#!/bin/bash

find . -type f ! -name 'readme.md' ! -name 'clean.sh' ! -name 'generic_script.sh' -exec rm -f {} \;
find . -type d ! -name 'nvml_power' ! -name 'nvml_energy' ! -name 'variorum' -exec rm -rf {} \;
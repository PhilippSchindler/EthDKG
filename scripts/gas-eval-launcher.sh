#!/bin/bash

cd "$(dirname "$0")"
unbuffer python -c "from ethdkg.eval_gas_costs import run_all; run_all([$1])" 2>&1 | tee ../logs/gas-costs.log


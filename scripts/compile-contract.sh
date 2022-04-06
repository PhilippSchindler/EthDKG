#!/bin/bash

cd "$(dirname "$0")"
cd ..

bin/solc --abi --bin --optimize --overwrite --output-dir contracts/bin contracts/$1.sol


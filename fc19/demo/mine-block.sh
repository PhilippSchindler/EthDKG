#!/bin/bash
curl localhost:8545 -X POST --data '{"jsonrpc": "2.0", "method": "evm_mine"}'

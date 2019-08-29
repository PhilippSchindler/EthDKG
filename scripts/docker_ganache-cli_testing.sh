#!/bin/bash

docker run                            \
  -p 127.0.0.1:7545:7545              \
  -it trufflesuite/ganache-cli:latest \
	--blockTime 1000000               \
	--gasLimit 8000000                \
	--deterministic                   \
	--accounts 20                     \
	--port 7545                       \
	--keepAliveTimeout 100000


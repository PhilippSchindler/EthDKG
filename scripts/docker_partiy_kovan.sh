#!/bin/bash

docker run -it -p 8545:8545 parity/parity:stable \
	--chain kovan   		\
    --warp


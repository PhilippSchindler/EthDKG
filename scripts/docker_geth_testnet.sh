#!/bin/bash

docker run -it -p 8545:8545 ethereum/client-go \
	--testnet 				\
	--syncmode light 		\
	--rpc 					\
	--unlock 0,1,2,3,4,5 	\
	--allow-insecure-unlock \
	--password <(echo -n)


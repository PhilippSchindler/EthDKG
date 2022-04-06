#!/bin/bash

ganache-cli 			 		\
	--blockTime 1000000  		\
	--gasLimit 10000000			\
	--deterministic				\
	--accounts 30 				\
	--port 7545		  	 		\
	--keepAliveTimeout 100000   #\
#    --hardfork istanbul


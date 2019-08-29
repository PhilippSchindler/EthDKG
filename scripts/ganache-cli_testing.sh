#!/bin/bash

ganache-cli 			 		\
	--blockTime 1000000  		\
	--gasLimit 8000000			\
	--deterministic				\
	--accounts 20 				\
	--port 7545		  	 		\
	--keepAliveTimeout 100000


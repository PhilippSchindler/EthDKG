#!/bin/bash

ganache-cli 			 		\
	--blockTime 100000			\
	--gasLimit 16000000			\
	--deterministic				\
	--accounts 320 				\
	--port 7545		  	 		\
	--keepAliveTimeout 100000



#!/bin/bash
geth --testnet --syncmode light --rpc --unlock 0,1,2,3,4,5 --allow-insecure-unlock --password <(echo -n)

#!/bin/bash
geth --testnet --syncmode light --rpc --unlock 0 --allow-insecure-unlock --password <(echo -n)

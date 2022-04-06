#!/bin/bash
geth --rinkeby --syncmode light --rpc --unlock 0 --allow-insecure-unlock --password <(echo -n)

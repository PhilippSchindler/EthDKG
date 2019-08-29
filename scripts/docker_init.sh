#!/bin/bash

cd "$(dirname "$0")"
cd ..

# download ganache-cli container for local testing and running testcase
docker pull trufflesuite/ganache-cli:latest

# download geth container for running the DKG protocol on the Ethereum testnet or mainnet
docker pull ethereum/client-go

# building our ethdkg contrainer
docker build --build-arg UID=1000 --build-arg GID=1000 -f Dockerfile -t ethdkg:latest .
# docker network create --subnet=172.18.0.0/16 --driver bridge ethdkgnet
docker network ls
docker images 

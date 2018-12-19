# EthDKG: An Ethereum-based Distributed Key Generation Protocol

First, check out our corresponding 
[paper](paper/Distributed\ Key\ Generation\ with\ Ethereum\ Smart\ Contracts.pdf),
to appear on Cryptology ePrint Archive (within the next few days).

Then follow the instructions below to get familiar with the implementation.

## Getting started

We provided a docker container (see instruction below) for running the DKG protocol.
The docker container can be used to execute the provided testcases as well as the CLI client application.

It is probably a good idea to read through our paper before going through the instructions below.

### Running the Testcases

In the `./client` folder we provide testcases for different scenarios.  
To execute the testcases perform the following steps:

1. start the docker container (automatically starts a ganache-cli instance)  
   `docker run -p 127.0.0.1:8545:8545 -it ethdkg`
2. using an additional terminal window, connect to docker container to get a shell inside  
   `docker ps`  
   `docker exec -it <CONTAINER ID> /bin/bash`  
3. within the container shell, switch to the `/ethdkg/client` directory
4. run `pytest -p no:cacheprovider` to execute all tests, (be patient, some tests might take a while)

### Running the DKG Client Application

The CLI client application `dkg.py` is located in the `./client` folder.  
Try running `python3 dkg.py --help` for information more infos on the CLI interface.

To test the DKG protocol with e.g. 4 clients perform the following steps:

1. open 6 terminal windows  
   (1 for each client, 1 for ganache-cli, 1 for deployment & invoking further commands)
2. in terminal 1, start the docker container to get a shell  
   `docker run -p 127.0.0.1:8545:8545 -it ethdkg /bin/bash`
3. in terminal 2-6, connect to the docker container  
   `docker ps`  
   `docker exec -it <CONTAINER ID> /bin/bash`
4. in terminal 1, start the ganache instance
   (ensure that that ganache has at least as many accounts as the number of participants in the DKG protocol, the default of 10 works for up to 10 clients)  
   `ganache-cli --host 0.0.0.0 --verbose`
5. in terminal 2, deploy the DKG smart contract  
   `python3 dkg.py deploy`
6. in terminals 3, 4 and 5, start a DKG client using ethereum account 0, 1 and 2 respecitively;  
   use the contract address you get from step 5 as common adress  
   `python3 dkg.py run 0 <contract address>`  
   `python3 dkg.py run 1 <contract address>`  
   `python3 dkg.py run 2 <contract address>`  
7. in terminal 6, repeat step 6 for ethereum account 3 or test the handling of failures and dispute using either of the following command to simulate adversarial behavior:
   * Abort the protocol after registration  
   `python3 dkg.py run 3 <contract address> --abort-after-registration`
   * Send invalid shares to node with id 1  
   `python3 dkg.py run 3 <contract address> --send-invalid-shares 1`  
   (you can also specify more that one id)

Now the DKG clients automatically execute the protocol.
When the protocol phase changes (e.g. from *registration* to *key sharing*) the DKG client application automatically waits for the next phase to start.

To continue operation, one needs to tell ganache-cli to mine blocks -- in the default configuration new blocks are only produced when when a transaction is received.
To instruct ganache to mine e.g. 10 new blocks you can use the helper function we provide in the `utils.py` package:  
`python3 -c 'import utils; utils.mine_blocks(10)'`

As an alternative (in step 4.) you can also start ganache-cli such that it automatically produces a block e.g. every 15 seconds using the following command:  
`ganache-cli --host 0.0.0.0 --blockTime 15 --verbose`  
You need to make sure that you quickly start the client application after deployment of the contract.
Registration is only possible within time window of 20 blocks after the contract is deployed.
This setting be adjusted in the DKG contract itself `./contracts/DKG.sol` and is set relative short to enable faster testing.

## Docker Basics

### Installation

Follow the instruction on <https://docs.docker.com/install/linux/docker-ce/ubuntu/> to install docker.

### Build Container

From root folder of reposity run:  
`docker build -t ethdkg .`

### Run Container

Start the container and run the Ethereum ganache-cli node:  `docker run -p 127.0.0.1:8545:8545 -it ethdkg`

Start the container without ganache-cli:  
`docker run -p 127.0.0.1:8545:8545 -it ethdkg /bin/bash`

### Connect to Container

List all containers:  
`docker ps`  

Connect to running container to get a shell:  
`docker exec -it <CONTAINER ID> /bin/bash`

### Delete Container

`docker rmi ethdkg -f`

## Ganache Basics

Ganache (more specifically ganache-cli) is a CLI frontend to a locally running Ethereum node used for development purpose only.
Ganache is preinstalled in the provided docker image.

To start ganache-cli manually:  
`ganache-cli --host 0.0.0.0`  (new block for each transaction)  
`ganache-cli --host 0.0.0.0 --blockTime 15 --verbose --accounts 100`  (new block every 15 seconds)  

Mine a new block (from local machine or docker):  
`curl -X POST --data '{"jsonrpc":"2.0","method":"evm_mine","params":[],"id":1}' localhost:8545`

Alternatively one can you our helper package `utils.py` to mine e.g. 10 blocks:  
`python3 -c 'import utils; utils.mine_blocks(10)'`

## Development

### Using pipenv

Corrently the `web3` package has a dependency issue when used with `pipenv`.
Therefore installation of all dependencies with `pipenv` requires the following workarround:

`rm -rf Pipfile.lock && rm -rf ~/.cache/pip && rm -rf ~/.cache/pipenv && pipenv install --skip-lock web3 && pipenv lock --pre --clear`

### Solidity compiler

The python bindings for the solidity compiler are currently not compatible with `solc` in version 0.5.

Workaround:
Just stick to version 0.4.25 from <https://github.com/ethereum/solidity/releases> for now.  
Extract and copy to /usr/bin/solc under Ubuntu.

## Testing the protocol in the Ropsten Testwork

Use e.g. <https://faucet.ropsten.be/> to obtain testnet Ether.

Create some new accouts with geth and supply them with funds:  
`geth --testnet account new` or  
`geth --testnet account import <path_to_private_key_file>`  
`geth --testnet account import <(echo private_key_ without_0x)`

Follow <https://github.com/ethereum/go-ethereum/wiki/Installing-Geth> to install geth.

Starting a local geth node:  
`geth --testnet --syncmode light --rpc`

Starting a local geth node and unlock the account(s):
`geth --testnet --syncmode light --rpc --unlock 0,1,2,3,4,5,6,7,8,9 --password <(echo -n)`

## Acknowledgements

I would like to express my very great appreciation to my co-authors Aljosha Judmayer and Nicholas Stifter for the excellent collabortion and support throughout the design and implementation of this project, a variety of critical discussions, and their valuable contributions to the paper.
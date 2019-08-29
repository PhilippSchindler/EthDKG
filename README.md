# EthDKG: An Ethereum-based Distributed Key Generation Protocol

This is the implantation of our corresponding research [paper](paper/ethdkg.pdf).
To familiarize yourself with the implementation run the test cases or execute the protocol by following the instructions below.

**Note**: An earlier version of the protocol was presented at the CIW'19 workshop at the Financial Cryptography and Data Security 2019 conference.
The [documentation](fc19/), [paper](fc19/paper/Distributed%20Key%20Generation%20with%20Ethereum%20Smart%20Contracts.pdf) and [slides](fc19/demo/slides-fc19.pdf)
from the previous version have been moved to the folder `./fc19`.

## Getting started

We provided a docker container (see instruction below) for running the DKG protocol.
The docker container can be used to execute the provided test cases as well as the CLI client application.
Alternatively, the client application can be run directly on Linux operating systems, we describe both approaches below.
Currently, both approaches are tested on **Linux only**.

It is probably a good idea to read through our paper before going through the instructions below.

### Setup using Docker

In the following, we assume basic experience with Docker.
To the setup the required dependencies using Docker follow the steps below:

1. Download or clone this repository.
2. Switch to the `/scripts` folder of this repository.
3. Execute the script `docker_init.sh`.

The script `docker_init.sh` first downloads the official docker container for `ganache-cli` and the Ethereum go client `geth`.
Those are used for running an Ethereum testnet locally or connecting to the `ropsten` testnet.
Second, it builds our `ethdkg` docker container, by installing the Python 3.7 as well as our Python package with dependencies (see `/requirements.txt`) inside the container.

### Setup without Docker

1. Download or clone this repository.
2. Ensure your have `Python 3.7` and `pip` installed on your system.
3. Switch to the root folder of this repository.
4. Install our `ethdkg` Python package using the command: `python3.7 -m pip install -e .`
5. Follow the instructions on [https://www.npmjs.com/package/ganache-cli](https://www.npmjs.com/package/ganache-cli) to install `ganache-cli` locally (or use Ethereum's docker container instead).
6. Optionally, install `ganache` as graphical alternative to `ganache-cli`.
7. Optionally, install `geth` for testing the protocol on the actual Ethereum testnet or mainnet.

## Running the Test Cases

In the `./ethdkg` folder we provide automated tests for different scenarios, including simulations of adversarial behavior.
To execute the test cases perform the following steps:

1. Start a local `ganache` or `ganache-cli` instance with appropriate parameters.
   We recommend that you use either of the pre-configured scripts
   `/scripts/docker_ganache-cli_testing.sh` or `/scripts/ganache-cli_testing.sh`,
   which both set the parameters for running the test cases correctly.

2. Wait for `ganache` or `ganache-cli` to startup.

3. Run the test cases using the command: `pytest` from the root or `/ethdkg` folder  of the repository.
   If you using our docker container, you can use the script `/scripts/docker_ethdkg.sh` to start the docker container to obtain a shell with all required dependencies installed.

The test cases should now execute.
Depending on your system running all tests might take a while (approx. 5 min), a the DKG protocol is run multiple times, testing different scenarios and adversarial behavior.

## Running the DKG Client Application

The CLI client application `dkg.py` is located in the `/client` folder.  
Try running `python3 dkg.py --help` for information more infos on the CLI interface.

1. Start a local `ganache` or `ganache-cli` instance with appropriate parameters.
   We recommend that you use either of the pre-configured scripts
   `/scripts/docker_ganache-cli.sh` or `/scripts/ganache-cli.sh`,
   which both set the appropriate parameters using for running the DKG protocol,
   mining is enabled and interval is set to 15 seconds.

2. Wait for `ganache` or `ganache-cli` to startup.

3. Deploy the DKG contract using the command `python3.7 -m ethdkg deploy`.
   As default the account with index 0 is used for deployment.

4. Run the DKG clients using the commands  
   `python3.7 -m ethdkg run CONTRACT_ADDRESS --account-index 1`,  
   `python3.7 -m ethdkg run CONTRACT_ADDRESS --account-index 2`, ...  
   `python3.7 -m ethdkg run CONTRACT_ADDRESS --account-index n`,  
   in separate shells.
   Again, you can use the script `/scripts/docker_ethdkg.sh` to start the docker container to obtain a shell with all required dependencies installed, and issue the command within the container.

Now the DKG clients automatically execute the protocol.
When the protocol phase changes the DKG client application automatically waits for the next phase to start.
If you use `ganache` or `ganache-cli` locally you can use you our utilities to speed up the mining process and reduce the waiting time.
To immediately mine e.g. 10 new blocks you can use the helper function as follows:
`python3.7 -c 'from ethdkg import utils; utils.mine_blocks(10)'`

To run the protocol in the Ethereum testnet or mainnet use
`geth` instead of `ganache-cli`.
Again we provide helper script for running `geth` in the `/scripts`.
Additionally, you need to setup and unlock the accounts used for deployment and running the node(s).
Take a look at the [/evaluation](evaluation/) folder for an documented example of the protocol execution in the Ethereum testnet, which also includes a simulation of adversarial behavior.

## Helpers

When you modify or experiment with our implementation you might find your helper utilities used within the implementation useful.
To use them you can run a interactive Python shell `python3.7 -i` and import the utilities using `from ethdkg import utils`.

The you can for example issue the command `utils.deploy_contract('ETHDKG')` to deploy the contract `/contracts/ETHDKG.sol`.
Or you can use the command `utils.mine_block()` to instruct `ganache` to immediately mine a new block, a feature we use extensively to speed up our automated tests.
Our utils, automatically handle the connection to the local `ganache` or `geth` client and can also be used to interface with deployed contracts (see e.g. the `utils.get_contract` function).

## Security Notice

This software is provided "as is", without warranty of any kind, express or implied (see [MIT license](LICENSE)).
The security of the software critically depends on the choice of various parameters and the correct configuration of the smart contract.
The defaults we provide enable simple testing and development but are not suitable for a production deployment.
Fell free to contact us if you have additional questions.

## List of Dependencies

In the following, we list all dependencies required to run our protocol client with the version number we used.
The required python packages are specified in the file `/requirements.txt`.

* Python (3.7)
* Pip (18.1)
* Solidity compiler `solc` (0.5.11+commit.22be8592.Linux.g++), provided in the `/bin` folder
* Ganache (2.1.0)
* Ganache CLI (6.5.1)

## Acknowledgements

I would like to express my very great appreciation to my co-authors Aljosha Judmayer and Nicholas Stifter for the excellent collaboration and support throughout the design and implementation of this project, a variety of critical discussions, and their valuable contributions to the paper.

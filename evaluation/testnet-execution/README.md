# Test deployment and execution of the DKG protocol in the Ropsten Testnet

As an simple example scenario we deployed our DKG in the Ethereum Testnet Ropsten,
where 5 clients run the DKG protocol and interact with the contract to generate a shared key.

The address of the deployed contract is: `0x64eB9cbc8AAc7723A7A94b178b7Ac4c18D7E6269`

We used the following Ethereum Accounts for the clients:  
A: `0x81100f1eAadC6781412217a2287F3BBcF72AD9d6` (assigned id: 3)  
B: `0x4D307e4ebC9B92fBcfbc9108aeB86Cefff1dA918` (assigned id: 2)  
C: `0xb73939AF7d449D12361EbB4F60141625461456e7` (assigned id: 1)  
D: `0x980DFA039b673412fC16678B5D34E17a51028C91` (assigned id: 4)  
E: `0x93611f0B9b577F393D255C0194A3E28f4B90B643` (assigned id: 5)

We used Ethereum account `0x90AF78E467296D96DBcC60d7F2C8f6A1B370941f` to deploy the contract and provide funds for a clients executing the protocol.

Clients A, B and C follow the DKG protocol as specified.
To simulate adversarial conditions we instructed Client D aborts the protocol after the registration phase,
while Client E executes the entire protocol but actively tries to manipulate the protocol run by sending an invalid share of its key to the client with id 1.
The exact parameters used to start the depoly the contract and start the clients are given in the `launcher-testnet.sh` script.

The entire protocol runs can be inspected using an Testnet explorer such as Etherscan:  
<https://ropsten.etherscan.io/address/0x64eB9cbc8AAc7723A7A94b178b7Ac4c18D7E6269>  
Notice that the client implementation correctly does not check if some other client already sent the final public key to the smart contract.
Instead it always publishes this key, leading to a reverted transaction consuming very little gas.
This in indicated by the exclaimation mark symbol in the Etherscan block explorer.

Furthermore we provide the log output from the clients and the local geth node (see files `deploment.log`, `./client_X.log` and `./geth.log`).
The testcase in `client/test_testnet_sig.py` shows that the three honest nodes can indeed compute a valid signature under the generated master public key.

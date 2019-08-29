pragma solidity ^0.5.8;

contract Greeter {

    string public greeting;

    constructor() public {
        greeting = 'Hello World!';
    }

    function greet() public view returns (string memory) {
        return greeting;
    }

    function setGreeting(string memory _greeting) public {
        greeting = _greeting;
    }


    // function test_bn256Pairing()
    // public returns (uint256[1] result) {

    //     result[0] = 4711;

    //     uint256[12] memory input;

    //     input[0] = 1; // G1.x
    //     input[1] = 2; // G1.y
    //     input[2] = 11559732032986387107991004021392285783925812861821192530917403151452391805634;  // G2.x;
    //     input[3] = 10857046999023057135944570762232829481370756359578518086990519993285655852781;  // G2.x
    //     input[4] = 4082367875863433681332203403145435568316851327593401208105741076214120093531;   // G2.y
    //     input[5] = 8495653923123431417604973247489272438418190587263600148770280649306958101930;   // G2.y

    //     input[6] = 1; // G1.x
    //     input[7] = 2; // G1.y
    //     input[8] = 11559732032986387107991004021392285783925812861821192530917403151452391805634;  // G2.x;
    //     input[9] = 10857046999023057135944570762232829481370756359578518086990519993285655852781;  // G2.x
    //     input[10] = 4082367875863433681332203403145435568316851327593401208105741076214120093531;   // G2.y
    //     input[11] = 8495653923123431417604973247489272438418190587263600148770280649306958101930;   // G2.y

    //     assembly {
    //         // 0x08     id of precompiled bn256Pairing contract     (checking the elliptic curve pairings)
    //         // 0        number of ether to transfer
    //         // 384       size of call parameters, i.e. 12*256 bits == 384 bytes
    //         // 32        size of result (one 32 byte boolean!)
    //         if iszero(call(not(0), 0x08, 0, input, 384, result, 32)) {
    //             revert(0, 0)
    //         }
    //     }

    //     // result[0] = 4711;
    // }
}
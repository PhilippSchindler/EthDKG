pragma solidity ^0.4.24;

contract PairingTest {

    // the following two functions execute successfully, but show exaclty the opposite behaviour to the python implementation
    // notice that the python implemenation, when printing point from FQ2, flips the order of the coordinates 

    function test_pairing() public {
        uint256[12] memory input; 
        input[0] = 10744596414106452074759370245733544594153395043370666422502510773307029471145;   // x coordinate of G1 * 5    
        input[1] = 848677436511517736191562425154572367705380862894644942948681172815252343932;     // y coordinate of G1 * 5    

        input[2] = 11559732032986387107991004021392285783925812861821192530917403151452391805634;  // G2.x.imag  
        input[3] = 10857046999023057135944570762232829481370756359578518086990519993285655852781;  // G2.x.real
        input[4] = 4082367875863433681332203403145435568316851327593401208105741076214120093531;   // G2.y.imag
        input[5] = 8495653923123431417604973247489272438418190587263600148770280649306958101930;   // G2.y.real

        input[6] = 1;                                                                               // x coordinate of G1
        input[7] = 2;                                                                               // y coordinate of G1

        input[8] = 4540444681147253467785307942530223364530218361853237193970751657229138047649;    // x.imag coordinate of G2 * 5  
        input[9] = 20954117799226682825035885491234530437475518021362091509513177301640194298072;   // x.real coordinate of G2 * 5  
        input[10] = 11631839690097995216017572651900167465857396346217730511548857041925508482915;  // y.imag coordinate of G2 * 5  
        input[11] = 21508930868448350162258892668132814424284302804699005394342512102884055673846;  // y.real coordinate of G2 * 5  

        uint[1] memory result;
        bool success;
        assembly {
            success := call(sub(gas, 2000), 0x08, 0, input, 384, result, 32)
        }
        require(success, "Somethings is wrong with the input! (e.g. invalid points)");
        require(result[0] == 0, "Contrary to the python implementation the pairing check is actually NOT successful.");
    }


    function test_pairing_neg() public {
        uint256[12] memory input; 
        input[0] = 10744596414106452074759370245733544594153395043370666422502510773307029471145;   // x coordinate of G1 * 5    
        input[1] = 848677436511517736191562425154572367705380862894644942948681172815252343932;     // y coordinate of G1 * 5    

        input[2] = 11559732032986387107991004021392285783925812861821192530917403151452391805634;  // G2.x.imag  
        input[3] = 10857046999023057135944570762232829481370756359578518086990519993285655852781;  // G2.x.real
        input[4] = 4082367875863433681332203403145435568316851327593401208105741076214120093531;   // G2.y.imag
        input[5] = 8495653923123431417604973247489272438418190587263600148770280649306958101930;   // G2.y.real

        input[6] = 1;                                                                               // x coordinate of -G1
        input[7] = 21888242871839275222246405745257275088696311157297823662689037894645226208581;   // y coordinate of -G1

        input[8] = 4540444681147253467785307942530223364530218361853237193970751657229138047649;    // x.imag coordinate of G2 * 5  
        input[9] = 20954117799226682825035885491234530437475518021362091509513177301640194298072;   // x.real coordinate of G2 * 5  
        input[10] = 11631839690097995216017572651900167465857396346217730511548857041925508482915;  // y.imag coordinate of G2 * 5  
        input[11] = 21508930868448350162258892668132814424284302804699005394342512102884055673846;  // y.real coordinate of G2 * 5  

        uint[1] memory result;
        bool success;
        assembly {
            success := call(sub(gas, 2000), 0x08, 0, input, 384, result, 32)
        }
        require(success, "Somethings is wrong with the input! (e.g. invalid points)");
        require(result[0] == 1, "Contrary to the python implementation the pairing check is actually successful.");
    }

}

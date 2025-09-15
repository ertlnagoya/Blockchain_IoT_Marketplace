// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVerifier {
    function verifyProof(
        uint256[2] memory a,
        uint256[2][2] memory b,
        uint256[2] memory c,
        uint256[1] memory input
    ) external view returns (bool);
}

contract DataUserZKAccess {
    event UserZKVerified(address indexed user, uint256 level, string accessLevel);

    IVerifier public verifier;

    constructor(address _verifier) {
        verifier = IVerifier(_verifier);
    }

    function verifyUserLevelZK(
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256 level
    ) external returns (uint256, string memory) {
        require(level <= 2, "invalid level");
    uint256[1] memory pub = [level];
    bool ok = verifier.verifyProof(a, b, c, pub);
    require(ok, "invalid proof");

        string memory access = level == 2 ? "full" : (level == 1 ? "access" : "denied");
        emit UserZKVerified(msg.sender, level, access);
        return (level, access);
    }
}
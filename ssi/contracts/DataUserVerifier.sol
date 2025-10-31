// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataUserVerifier {
    event UserVerified(address indexed user, uint256 trustScore, string accessLevel);

    function verifyUserAccess(
        string memory entityType,
        string memory purpose,
        bool legalCompliance,
        string memory dataHandlingPolicy,
        bool misuseRecord
    ) public returns (uint256 trustScore, string memory accessLevel) {
        trustScore = 0;

        // 1️⃣ entityType（统一大写比较）
        if (
            compareStrings(toUpper(entityType), "GOVERNMENTORGANIZATION") ||
            compareStrings(toUpper(entityType), "POLICE")
        ) trustScore += 35;
        else if (compareStrings(toUpper(entityType), "ENTERPRISE")) trustScore += 20;
        else if (compareStrings(toUpper(entityType), "RESEARCH ORGANIZATION")) trustScore += 15;
        else trustScore += 5;

        // 2️⃣ purpose（统一大写比较）
        if (compareStrings(toUpper(purpose), "CRIME SEARCH")) trustScore += 25;
        else if (compareStrings(toUpper(purpose), "TRAFFIC MANAGEMENT")) trustScore += 20;
        else if (compareStrings(toUpper(purpose), "RESEARCH")) trustScore += 15;
        else trustScore += 5;

        // 3️⃣ legalCompliance
        if (legalCompliance) trustScore += 15;

        // 4️⃣ dataHandlingPolicy（统一大写比较）
        if (compareStrings(toUpper(dataHandlingPolicy), "ISO27001")) trustScore += 15;

        // 5️⃣ misuseRecord
        if (misuseRecord == false) trustScore += 10;
        else trustScore -= 10;

        // Access Level（统一大写比较）
        if (trustScore >= 80 && (
            compareStrings(toUpper(entityType), "GOVERNMENTORGANIZATION") ||
            compareStrings(toUpper(entityType), "POLICE"))
        ) {
            accessLevel = "full";
        } else if (trustScore >= 60) {
            accessLevel = "access";
        } else {
            accessLevel = "denied";
        }

        emit UserVerified(msg.sender, trustScore, accessLevel); // 写操作，触发MetaMask弹窗
        return (trustScore, accessLevel);
    }

    function compareStrings(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }

    function toUpper(string memory str) internal pure returns (string memory) {
        bytes memory bStr = bytes(str);
        for (uint i = 0; i < bStr.length; i++) {
            if ((uint8(bStr[i]) >= 97) && (uint8(bStr[i]) <= 122)) {
                bStr[i] = bytes1(uint8(bStr[i]) - 32);
            }
        }
        return string(bStr);
    }
}
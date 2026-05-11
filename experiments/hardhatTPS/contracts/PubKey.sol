// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

// errors
error PubKey__InvalidPubKey();
error PubKey__NotRegistered();

/**
 * @title PubKey
 * @notice MediatorのアカウントアドレスとRSA公開鍵のペアを保管するコントラクト
 */
import "hardhat/console.sol";

contract PubKey {
    mapping(address => string) private s_addressToPublicKey;

    function registerKey(string memory pubKey) public {
        if (!isPubKey(pubKey)) revert PubKey__InvalidPubKey();
        s_addressToPublicKey[tx.origin] = pubKey;
    }

    function isPubKey(string memory pubKey) private pure returns (bool) {
        bytes memory b = bytes(pubKey);
        if (b[0] == "[" && b[b.length - 1] == "]") {
            return true;
        }
        return false;
    }

    function existKey() private view returns (bool) {
        bytes memory b = bytes(s_addressToPublicKey[tx.origin]);
        return b.length != 0;
    }

    function getPubKey(address who) public view returns (string memory) {
        if (!existKey()) revert PubKey__NotRegistered();
        return s_addressToPublicKey[address(who)];
    }
}

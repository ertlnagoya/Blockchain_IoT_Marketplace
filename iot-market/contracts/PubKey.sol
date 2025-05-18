// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

// imports

// errors
error PubKey__InvalidPubKey();
error PubKey__NotRegistered();

/**
 * @title PubKey
 * @author Kenta Kawai
 * @notice MediatorのアカウントアドレスとRSA公開鍵のペアを保管するコントラクト
 */
import "hardhat/console.sol";

contract PubKey {
    // type declarations

    // state variables
    mapping(address => string) private s_addressToPublicKey;

    // events
    // constructor

    // functions
    /**
     * @notice アドレスと結びついた公開鍵を登録する関数
     * @param pubKey 公開鍵
     */
    function registerKey(string memory pubKey) public {
        if (!isPubKey(pubKey)) revert PubKey__InvalidPubKey();
        s_addressToPublicKey[tx.origin] = pubKey;
    }

    /**
     * @notice 公開鍵が正しい形式かどうかを確認する関数
     * @dev 今回は簡易的に、文字列が公開鍵の形式かどうかを確認する
     * @param pubKey 公開鍵
     */
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

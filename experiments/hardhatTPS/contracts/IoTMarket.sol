// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./Merchandise.sol";
import "./PubKey.sol";

/**
 * @title IoTMarket
 * @author Kenta Kawai
 * @notice Merchandiseコントラクトの管理を一元的に行うコントラクト
 * Dappsのフロントエンドに必要な情報を提供する
 */
contract IoTMarket {
    Merchandise[] public s_merchandises;

    // functions
    /**
     * @notice 商品の登録
     * @dev Merchandiseコントラクトを紐づけて登録する
     */
    function registerMerchandise(Merchandise merchandise) public {
        s_merchandises.push(merchandise);
    }

    function getMerchandises() public view returns (Merchandise[] memory) {
        return s_merchandises;
    }

    function getMerchandise(uint256 index) public view returns (Merchandise) {
        return s_merchandises[index];
    }
}

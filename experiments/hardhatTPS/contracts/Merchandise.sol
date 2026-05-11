// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

import "./PubKey.sol";

error Merchandise__NotOwner();
error Merchandise__NotForSale();
error Merchandise__Bunned();
error Merchandise__AlreadyPurchased();
error Merchandise__NotInProgress();
error Merchandise__NotEnoughETH();
error Merchandise__NotBuyer();
error Merchandise__WithdrawFailed();
error Merchandise__AccessDenied();

struct KeyValuePair {
    string key;
    string value;
}

contract Merchandise {
    enum MerchandiseState {
        SALE,
        IN_PROGRESS,
        BANNED
    }

    uint public constant RETRY_LIMIT = 10;
    address private immutable i_owner;
    bytes32 private immutable i_dataHash;
    uint private i_price;
    MerchandiseState public s_merchandiseState = MerchandiseState.SALE;
    uint private s_trialCount = 0;
    address private s_progressBuyer;
    PubKey private immutable i_pubKey;

    mapping(address => bool) public s_confirmedBuyers;
    mapping(address => bool) private i_accessDeniedAddresses;

    KeyValuePair[] private s_additionalInfo;

    event Purchase(address indexed owner, address indexed buyer, string pubkey);
    event Verify(
        address indexed owner,
        address indexed buyer,
        bool indexed result
    );
    event Upload(address indexed owner, address indexed buyer, string uri);

    constructor(
        uint price,
        bytes32 dataHash,
        PubKey pubKey,
        address[] memory accessDeniedAddresses,
        string[] memory additionalInfoKeys,
        string[] memory additionalInfoValues
    ) {
        i_owner = tx.origin;
        i_price = price;
        i_dataHash = dataHash;
        i_pubKey = pubKey;
        for (uint i = 0; i < accessDeniedAddresses.length; i++) {
            i_accessDeniedAddresses[accessDeniedAddresses[i]] = true;
        }
        for (uint i = 0; i < additionalInfoKeys.length; i++) {
            s_additionalInfo.push(
                KeyValuePair(additionalInfoKeys[i], additionalInfoValues[i])
            );
        }
    }

    function purchase() public payable {
        if (s_merchandiseState != MerchandiseState.SALE)
            revert Merchandise__NotForSale();
        if (msg.value < i_price) revert Merchandise__NotEnoughETH();
        if (i_accessDeniedAddresses[msg.sender])
            revert Merchandise__AccessDenied();
        if (s_confirmedBuyers[msg.sender] == true)
            revert Merchandise__AlreadyPurchased();

        s_merchandiseState = MerchandiseState.IN_PROGRESS;
        s_progressBuyer = msg.sender;

        string memory pubKey = i_pubKey.getPubKey(tx.origin);
        emit Purchase(i_owner, msg.sender, pubKey);
    }

    function verify(bytes32 dataHash) public returns (bool) {
        if (s_merchandiseState != MerchandiseState.IN_PROGRESS)
            revert Merchandise__NotInProgress();
        if (s_progressBuyer != msg.sender) revert Merchandise__NotBuyer();

        s_trialCount++;
        if (i_dataHash != dataHash && s_trialCount < RETRY_LIMIT) {
            emit Verify(i_owner, msg.sender, false);
            return false;
        } else if (i_dataHash != dataHash && s_trialCount >= RETRY_LIMIT) {
            s_merchandiseState = MerchandiseState.BANNED;
            return false;
        }

        s_merchandiseState = MerchandiseState.SALE;
        s_trialCount = 0;
        s_progressBuyer = address(0);
        s_confirmedBuyers[msg.sender] = true;
        emit Verify(i_owner, msg.sender, true);
        return true;
    }

    function withdraw() public {
        if (msg.sender != i_owner) revert Merchandise__NotOwner();
        if (s_merchandiseState == MerchandiseState.BANNED)
            revert Merchandise__Bunned();

        (bool success, ) = i_owner.call{value: address(this).balance}("");
        if (!success) revert Merchandise__WithdrawFailed();
    }

    function emitUpload(string memory encryptURI) public {
        if (msg.sender != i_owner) revert Merchandise__NotOwner();
        if (s_merchandiseState != MerchandiseState.IN_PROGRESS)
            revert Merchandise__NotInProgress();
        emit Upload(i_owner, s_progressBuyer, encryptURI);
    }

    function getAllAdditionalInfo() public view returns (KeyValuePair[] memory) {
        return s_additionalInfo;
    }

    function getRetryLimit() public pure returns (uint) {
        return RETRY_LIMIT;
    }

    function getOwner() public view returns (address) {
        return i_owner;
    }

    function getDataHash() public view returns (bytes32) {
        return i_dataHash;
    }

    function getPrice() public view returns (uint) {
        return i_price;
    }

    function getState() public view returns (MerchandiseState) {
        return s_merchandiseState;
    }

    function getTrialCount() public view returns (uint) {
        return s_trialCount;
    }

    function getProgressBuyer() public view returns (address) {
        return s_progressBuyer;
    }

    function isConfirmedBuyer(address buyer) public view returns (bool) {
        return s_confirmedBuyers[buyer];
    }

    function getPubKeyAddress() public view returns (address) {
        return address(i_pubKey);
    }
}

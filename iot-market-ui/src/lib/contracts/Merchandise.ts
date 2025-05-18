export const contractAddress = '';
export const abi = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "price",
                "type": "uint256"
            },
            {
                "internalType": "bytes32",
                "name": "dataHash",
                "type": "bytes32"
            },
            {
                "internalType": "contract PubKey",
                "name": "pubKey",
                "type": "address"
            },
            {
                "internalType": "address[]",
                "name": "accessDeniedAddresses",
                "type": "address[]"
            },
            {
                "internalType": "string[]",
                "name": "additionalInfoKeys",
                "type": "string[]"
            },
            {
                "internalType": "string[]",
                "name": "additionalInfoValues",
                "type": "string[]"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [],
        "name": "Merchandise__AccessDenied",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__AlreadyPurchased",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__Bunned",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__NotBuyer",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__NotEnoughETH",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__NotForSale",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__NotInProgress",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__NotOwner",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "Merchandise__WithdrawFailed",
        "type": "error"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "buyer",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "string",
                "name": "pubkey",
                "type": "string"
            }
        ],
        "name": "Purchase",
        "type": "event"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "buyer",
                "type": "address"
            },
            {
                "indexed": false,
                "internalType": "string",
                "name": "uri",
                "type": "string"
            }
        ],
        "name": "Upload",
        "type": "event"
    },
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": true,
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "address",
                "name": "buyer",
                "type": "address"
            },
            {
                "indexed": true,
                "internalType": "bool",
                "name": "result",
                "type": "bool"
            }
        ],
        "name": "Verify",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "RETRY_LIMIT",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "encryptURI",
                "type": "string"
            }
        ],
        "name": "emitUpload",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getAllAdditionalInfo",
        "outputs": [
            {
                "components": [
                    {
                        "internalType": "string",
                        "name": "key",
                        "type": "string"
                    },
                    {
                        "internalType": "string",
                        "name": "value",
                        "type": "string"
                    }
                ],
                "internalType": "struct KeyValuePair[]",
                "name": "",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getDataHash",
        "outputs": [
            {
                "internalType": "bytes32",
                "name": "",
                "type": "bytes32"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getOwner",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getPrice",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getProgressBuyer",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getPubKeyAddress",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getRetryLimit",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "pure",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getState",
        "outputs": [
            {
                "internalType": "enum Merchandise.MerchandiseState",
                "name": "",
                "type": "uint8"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTrialCount",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "buyer",
                "type": "address"
            }
        ],
        "name": "isConfirmedBuyer",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "purchase",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "name": "s_confirmedBuyers",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "s_merchandiseState",
        "outputs": [
            {
                "internalType": "enum Merchandise.MerchandiseState",
                "name": "",
                "type": "uint8"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "dataHash",
                "type": "bytes32"
            }
        ],
        "name": "verify",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
];

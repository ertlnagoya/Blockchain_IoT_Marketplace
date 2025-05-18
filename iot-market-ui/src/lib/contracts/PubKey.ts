export const contractAddress = '0x5FbDB2315678afecb367f032d93F642f64180aa3';
export const abi = [
    {
        "inputs": [],
        "name": "PubKey__InvalidPubKey",
        "type": "error"
    },
    {
        "inputs": [],
        "name": "PubKey__NotRegistered",
        "type": "error"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "who",
                "type": "address"
            }
        ],
        "name": "getPubKey",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "pubKey",
                "type": "string"
            }
        ],
        "name": "registerKey",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
];

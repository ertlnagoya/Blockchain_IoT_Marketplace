import { PUBKEY_ADDRESS } from './addresses';

export const contractAddress = PUBKEY_ADDRESS ?? '0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0';
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

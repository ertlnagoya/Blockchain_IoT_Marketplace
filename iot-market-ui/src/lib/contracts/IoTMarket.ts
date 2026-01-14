import { IOT_MARKET_ADDRESS } from './addresses';

export const contractAddress = IOT_MARKET_ADDRESS;
export const abi = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "index",
                "type": "uint256"
            }
        ],
        "name": "getMerchandise",
        "outputs": [
            {
                "internalType": "contract Merchandise",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getMerchandises",
        "outputs": [
            {
                "internalType": "contract Merchandise[]",
                "name": "",
                "type": "address[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "contract Merchandise",
                "name": "merchandise",
                "type": "address"
            }
        ],
        "name": "registerMerchandise",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "name": "s_merchandises",
        "outputs": [
            {
                "internalType": "contract Merchandise",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
];

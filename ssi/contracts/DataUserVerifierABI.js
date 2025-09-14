export const DataUserVerifierABI = [
  {
    "inputs": [
      { "internalType": "string", "name": "entityType", "type": "string" },
      { "internalType": "string", "name": "purpose", "type": "string" },
      { "internalType": "bool", "name": "legalCompliance", "type": "bool" },
      { "internalType": "string", "name": "dataHandlingPolicy", "type": "string" },
      { "internalType": "bool", "name": "misuseRecord", "type": "bool" }
    ],
    "name": "verifyUserAccess",
    "outputs": [
      { "internalType": "uint256", "name": "trustScore", "type": "uint256" },
      { "internalType": "string", "name": "accessLevel", "type": "string" }
    ],
    "stateMutability": "nonpayable", // 这里改为 nonpayable
    "type": "function"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": true, "internalType": "address", "name": "user", "type": "address" },
      { "indexed": false, "internalType": "uint256", "name": "trustScore", "type": "uint256" },
      { "indexed": false, "internalType": "string", "name": "accessLevel", "type": "string" }
    ],
    "name": "UserVerified",
    "type": "event"
  }
];
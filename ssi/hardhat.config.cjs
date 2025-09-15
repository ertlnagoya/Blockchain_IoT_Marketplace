require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    compilers: [
      { version: "0.8.28" }
    ]
  },
  networks: {
    hardhat: {
      hardfork: "london",
      accounts: {
        mnemonic: "test test test test test test test test test test test junk",
        initialIndex: 0,
        count: 20,
      },
      reset: true,
    },
    localhost: { url: "http://127.0.0.1:8546" },
  },
};
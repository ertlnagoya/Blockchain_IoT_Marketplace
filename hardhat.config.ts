import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import "dotenv/config";

const getCurrentTime = () => {
  const date = new Date();
  return date.toLocaleString("sv-SE");
};

const config: HardhatUserConfig = {
  defaultNetwork: "hardhat",
  solidity: "0.8.19",
  networks: {
    hardhat: {},
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
  },
  sourcify: {
    enabled: true,
  },
  gasReporter: {
    enabled: true,
    noColors: true,
    outputFile: `logs/${getCurrentTime()}`,
    coinmarketcap: "ec9d8d7e-6a0b-44e4-9194-83015afe73fd",
    gasPrice: 3.218,
  },
};

export default config;

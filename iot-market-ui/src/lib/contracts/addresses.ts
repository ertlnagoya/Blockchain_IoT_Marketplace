// Auto-loaded deployment addresses shared across the frontend
// Reads the latest Hardhat deployment JSON so we always talk to the correct contracts.
import deployments from '../../../../iot-market/deployments/localhost.json' assert { type: 'json' };

type DeploymentSchema = {
  iotMarket: string;
  merchandises: string[];
  pubKey?: string;
};

const { iotMarket, merchandises, pubKey } = deployments as DeploymentSchema;

export const IOT_MARKET_ADDRESS = iotMarket;
export const MERCHANDISE_ADDRESSES = merchandises;
export const PUBKEY_ADDRESS = pubKey;

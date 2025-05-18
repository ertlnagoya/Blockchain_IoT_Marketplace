import type { PageLoad } from "./$types";
import { IoTMarket__factory } from "../types/typechain-types";
import { contractAddress } from "$lib/contracts/IoTMarket";
import { Merchandise__factory } from "../types/typechain-types";
import { ethers } from "ethers";
import { CLIENT_SIDE_RPC_PROVIDER, SERVER_SIDE_RPC_PROVIDER } from "$lib/const/jsonRPCProvider";


export const load: PageLoad = async () => {
    // client or server sideで違うURLで叩かないといけない
    let provider;
    if (typeof window === "undefined") {
        provider = ethers.getDefaultProvider(SERVER_SIDE_RPC_PROVIDER);
    } else {
        provider = ethers.getDefaultProvider(CLIENT_SIDE_RPC_PROVIDER);
    }
    const IoTMarket = IoTMarket__factory.connect(contractAddress, provider);
    const merchandiseAddress = await IoTMarket.getMerchandises();
    const merchandisies = merchandiseAddress.map((address) => Merchandise__factory.connect(address, provider));
    const clientData = [];
    for (const merchandise of merchandisies) {
        const address = await merchandise.getAddress();
        const price = await merchandise.getPrice().then((price) => ethers.formatEther(price));
        const state = await merchandise.getState();
        clientData.push({
            address: address,
            state: state,
            price: price,
        })
    }
    return { clientData };
};




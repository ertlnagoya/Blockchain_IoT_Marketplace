import { ethers } from "ethers";
import { Merchandise__factory } from "../../../types/typechain-types";
import { SERVER_SIDE_RPC_PROVIDER, CLIENT_SIDE_RPC_PROVIDER } from "$lib/const/jsonRPCProvider";
import type { PageLoad } from "./$types";
export const load: PageLoad = async ({ params }) => {
    let provider;
    if (typeof window === "undefined") {
        provider = ethers.getDefaultProvider(SERVER_SIDE_RPC_PROVIDER);
    } else {
        provider = ethers.getDefaultProvider(CLIENT_SIDE_RPC_PROVIDER);
    }
    const address = params.address;
    const merchandise = Merchandise__factory.connect(address, provider);
    const price = await merchandise.getPrice().then((price) => ethers.formatEther(price));
    const clientData = {
        retryLimit: await merchandise.getRetryLimit(),
        owner: await merchandise.getOwner(),
        price: price,
        address: await merchandise.getAddress(),
        state: await merchandise.getState(),
        additionalInfo: await merchandise.getAllAdditionalInfo()
    };

    return clientData;
};

import { ethers } from "ethers";
import { Merchandise__factory } from "../../../types/typechain-types";
import { RPC_URL, NETWORK } from "$lib/const/jsonRPCProvider";
import type { PageLoad } from "./$types";
export const load: PageLoad = async ({ params }) => {
    // +page.ts runs only in the browser; there’s no need to check or branch on window
    const provider = new ethers.JsonRpcProvider(RPC_URL, NETWORK);

    const address = params.address;
    const merchandise = Merchandise__factory.connect(address, provider);

    const price = await merchandise.getPrice().then((p) => ethers.formatEther(p));
    const clientData = {
        retryLimit: await merchandise.getRetryLimit(),
        owner: await merchandise.getOwner(),
        price,
        address: await merchandise.getAddress(),
        state: await merchandise.getState(),
        additionalInfo: await merchandise.getAllAdditionalInfo()
    };

    return clientData;
};

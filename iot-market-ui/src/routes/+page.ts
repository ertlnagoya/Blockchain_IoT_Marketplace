import type { PageLoad } from "./$types";
import { IoTMarket__factory } from "../types/typechain-types";
import { contractAddress } from "$lib/contracts/IoTMarket";
import { Merchandise__factory } from "../types/typechain-types";
import { ethers, JsonRpcProvider } from "ethers";
import { RPC_URL, NETWORK } from "$lib/const/jsonRPCProvider";

function withTimeout<T>(p: Promise<T>, ms = 8000): Promise<T> {
  let id: any;
  return Promise.race([
    p,
    new Promise<T>((_, rej) => (id = setTimeout(() => rej(new Error("rpc timeout")), ms))),
  ]).finally(() => clearTimeout(id));
}

export const load: PageLoad = async () => {
    // Explicitly use the local RPC and disable network auto-detection
    const provider = new JsonRpcProvider(RPC_URL, NETWORK);
    const IoTMarket = IoTMarket__factory.connect(contractAddress, provider);
    
    try {
     const merchandiseAddress = await withTimeout(IoTMarket.getMerchandises());
     const merchandisies = merchandiseAddress.map((address) =>
       Merchandise__factory.connect(address, provider)
     );

     // Read each merchandise's info concurrently
     const clientData = await Promise.all(
       merchandisies.map(async (m) => {
         const [address, priceBN, state] = await Promise.all([
           withTimeout(m.getAddress()),
           withTimeout(m.getPrice()),
           withTimeout(m.getState()),
         ]);
         return {
           address,
           state,
           price: ethers.formatEther(priceBN),
         };
       })
     );
     return { clientData };
   } catch (e) {
     console.error("[+page.ts] load error:", e);
     // Do not block the first render when the chain is temporarily unavailable
     return { clientData: [] };
   }
};




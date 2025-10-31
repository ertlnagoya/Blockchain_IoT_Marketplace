在这个路径下，只要智能合约发生改变，必须重新编译
第二个指令是为了防止智能合约又编译到同一个地址下
这样肯定出错
所以ssi项目换一个端口
终端在这里打开/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/contracts
npx hardhat compile
npx hardhat node --port 8546


然后在contracts路径下，同样再打开这个终端
npx hardhat run scripts/deploy.cjs --network localhost
这样就能得到合约地址
把合约地址复制到/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/ssi-ui/src/components/verifyUserVC.jsx

再开前端终端
/Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi/ssi-ui
npm run dev



更新：零知识证明内容更新
cd /Users/lyhl/Downloads/vscode_workspace/IoTMarket/ssi
npx hardhat compile
npx hardhat run contracts/scripts/DataUserZKdeploy.cjs --network localhost

Verifier deployed: 0x5FC8d32690cc91D4c39d9d3abcBD16989F875707
DataUserZKAccess deployed: 0x0165878A594ca255338adfa4d48449f69242Eb8F
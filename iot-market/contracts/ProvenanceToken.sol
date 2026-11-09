// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Base64.sol";
import "@openzeppelin/contracts/utils/Strings.sol";

error ProvenanceToken__NotMinter();
error ProvenanceToken__AlreadyAnchored();
error ProvenanceToken__BadString();

/**
 * @title ProvenanceToken
 * @notice Stage P (C2PA provenance) P2: one token per detection event,
 *         anchoring the C2PA manifest label, the sha256 of the signed
 *         image and its IPFS CID. The image itself never goes on chain
 *         (docs/design/c2pa-provenance-spec §8).
 * @dev The chain points at the manifest, not the other way round: the
 *      token ID is unknown when the capture is signed (spec §8.3).
 */
contract ProvenanceToken is ERC721 {
    struct Provenance {
        string manifestLabel;
        bytes32 assetSha256;
        string cid;
        string sellerDid;
    }

    address private immutable i_minter;
    uint256 private s_nextTokenId = 1;
    mapping(uint256 => Provenance) private s_provenance;
    mapping(bytes32 => uint256) private s_tokenOfAsset;

    event ProvenanceAnchored(
        uint256 indexed tokenId,
        bytes32 indexed assetSha256,
        string manifestLabel,
        string cid,
        string sellerDid
    );

    constructor() ERC721("IW3IP Provenance", "IW3P") {
        i_minter = msg.sender;
    }

    /**
     * @notice Anchor one signed asset. An asset (sha256) is anchored once.
     */
    function mint(
        address to,
        string calldata manifestLabel,
        bytes32 assetSha256,
        string calldata cid,
        string calldata sellerDid
    ) external returns (uint256 tokenId) {
        if (msg.sender != i_minter) revert ProvenanceToken__NotMinter();
        if (s_tokenOfAsset[assetSha256] != 0) revert ProvenanceToken__AlreadyAnchored();
        _requireJsonSafe(manifestLabel);
        _requireJsonSafe(cid);
        _requireJsonSafe(sellerDid);
        tokenId = s_nextTokenId++;
        s_provenance[tokenId] = Provenance(manifestLabel, assetSha256, cid, sellerDid);
        s_tokenOfAsset[assetSha256] = tokenId;
        _safeMint(to, tokenId);
        emit ProvenanceAnchored(tokenId, assetSha256, manifestLabel, cid, sellerDid);
    }

    function provenanceOf(uint256 tokenId) external view returns (Provenance memory) {
        _requireMinted(tokenId);
        return s_provenance[tokenId];
    }

    /// @return the token anchoring `assetSha256`, or 0 when none
    function tokenOfAsset(bytes32 assetSha256) external view returns (uint256) {
        return s_tokenOfAsset[assetSha256];
    }

    function getMinter() external view returns (address) {
        return i_minter;
    }

    /// @notice JSON metadata as a data URI (spec §8.1)
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireMinted(tokenId);
        Provenance storage p = s_provenance[tokenId];
        bytes memory json = abi.encodePacked(
            '{"name":"IW3IP Provenance #', Strings.toString(tokenId),
            '","manifestLabel":"', p.manifestLabel,
            '","assetSha256":"', Strings.toHexString(uint256(p.assetSha256), 32),
            '","cid":"', p.cid,
            '","sellerDid":"', p.sellerDid,
            '"}'
        );
        return string(abi.encodePacked("data:application/json;base64,", Base64.encode(json)));
    }

    /// @dev keep tokenURI valid JSON: no quotes, backslashes or control characters
    function _requireJsonSafe(string calldata s) private pure {
        bytes calldata b = bytes(s);
        for (uint256 i = 0; i < b.length; i++) {
            bytes1 c = b[i];
            if (c == '"' || c == "\\" || uint8(c) < 0x20) revert ProvenanceToken__BadString();
        }
    }
}

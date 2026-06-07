// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SolisMerkleAnchor {
    event RootAnchored(bytes32 indexed root, uint256 timestamp);

    function anchorRoot(bytes32 root) public {
        emit RootAnchored(root, block.timestamp);
    }
}

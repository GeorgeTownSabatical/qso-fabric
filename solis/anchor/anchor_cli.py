from __future__ import annotations

import argparse

from solis.anchor.eth_anchor import EthereumAnchor
from solis.anchor.spherechain_anchor import SphereChainAnchor


def main() -> None:
    parser = argparse.ArgumentParser(description="Anchor Solis Merkle roots to external chains")
    parser.add_argument("--chain", choices=["ethereum", "spherechain"], required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--rpc-url", default="")
    parser.add_argument("--contract", default="")
    parser.add_argument("--private-key", default="")
    parser.add_argument("--endpoint", default="https://spherechain.local")
    args = parser.parse_args()

    if args.chain == "ethereum":
        anchor = EthereumAnchor(args.rpc_url, args.contract, args.private_key)
        result = anchor.anchor(args.root)
        print(result)
        return

    anchor = SphereChainAnchor(args.endpoint)
    result = anchor.anchor(args.root)
    print(result)


if __name__ == "__main__":
    main()

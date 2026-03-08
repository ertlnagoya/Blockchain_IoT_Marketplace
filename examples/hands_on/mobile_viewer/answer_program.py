#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from urllib import request

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.hands_on.common import detect_lan_ip


def build_mobile_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/mobile"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    host = args.host or detect_lan_ip()
    url = build_mobile_url(host, args.port)
    print(url)

    if args.check:
        with request.urlopen(url, timeout=5) as resp:  # noqa: S310 - local training endpoint
            print(f"HTTP {resp.status}")


if __name__ == "__main__":
    main()

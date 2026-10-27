"""Backward-compatible command-line entry point for the sandbox service."""

import argparse
import json

from sandbox_service import run_behavioral_scan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ecosystem", choices=("pypi", "npm"))
    parser.add_argument("package_name")
    parser.add_argument("--local-archive")
    args = parser.parse_args()
    print(json.dumps(run_behavioral_scan(args.ecosystem, args.package_name, args.local_archive)))


if __name__ == "__main__":
    main()
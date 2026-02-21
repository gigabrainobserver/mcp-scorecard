"""CLI entrypoint — python -m mcp_scorecard."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-scorecard",
        description="Trust scoring index for MCP servers",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (default: ./output)",
    )
    args = parser.parse_args()

    from mcp_scorecard.pipeline import run

    try:
        asyncio.run(run(output_dir=args.output))
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Replay the bounded warehouse sample using the source-neutral interpreter."""

import argparse
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import asdict
import json
from pathlib import Path

from .cosing_preview_adapter import adapt_cosing_preview
from .framework import InterpretationFramework

SAMPLE = Path(__file__).with_name("evaluation")


def sampled_inputs():
    """Translate only the saved evaluation rows. This is not an ingestion adapter."""
    parents = json.loads((SAMPLE / "inci_records.json").read_text(encoding="utf-8"))
    aliases = json.loads((SAMPLE / "typed_aliases.json").read_text(encoding="utf-8"))
    typed_by_parent = defaultdict(list)
    for row in aliases:
        typed_by_parent[row["inci_id"]].append(row)
    for row in parents:
        yield adapt_cosing_preview(row, typed_by_parent[row["inci_id"]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opsin", action="store_true", help="Use the existing local OPSIN Java bridge")
    args = parser.parse_args()
    with ExitStack() as stack:
        bridge = None
        if args.opsin:
            from providers import Bridge

            bridge = Bridge()
            stack.callback(bridge.close)
        framework = InterpretationFramework(name_parser=bridge)
        print(json.dumps([asdict(framework.interpret(item)) for item in sampled_inputs()], indent=2))


if __name__ == "__main__":
    main()

"""Command-line entry point for the local development workflow."""
import argparse
import json
from pathlib import Path

from .development import DATA, open_development
from .workflow import ChemicalInput, Enrichment, read_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DATA)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    for command in ("resolve", "commit"):
        sub = commands.add_parser(command)
        inputs = sub.add_mutually_exclusive_group(required=True)
        inputs.add_argument("--name")
        inputs.add_argument("--structure", help="Explicit SMILES for a structure-only input")
        inputs.add_argument("--csv", type=Path)
        inputs.add_argument("--text", type=Path)
        for field in ("smiles", "inchi", "inchikey", "cas", "ec", "inci-name", "source-system", "source-record-id"):
            sub.add_argument("--" + field, default="")
        sub.add_argument("--saved-evidence", type=Path)
        if command == "commit":
            sub.add_argument("--yes", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "init":
        substance, concept = open_development(args.directory, create=True)
        print(json.dumps({"substance_database": str(substance.path), "concept_database": str(concept.path)}))
        return
    extras = {field: getattr(args, field) for field in
              ("smiles", "inchi", "inchikey", "cas", "ec", "inci_name", "source_system", "source_record_id")}
    packet = json.loads(args.saved_evidence.read_text(encoding="utf-8-sig")) if args.saved_evidence else None
    if args.structure is not None:
        if extras["smiles"]:
            parser.error("Use --structure or --smiles once")
        records = [ChemicalInput("", **{**extras, "smiles": args.structure})]
    elif args.name is not None:
        records = [ChemicalInput(args.name, **extras)]
    else:
        if any(extras.values()) or packet:
            parser.error("Use per-record CSV fields for batches. Saved provider evidence takes one --name.")
        records = read_inputs((args.csv or args.text).read_text(encoding="utf-8-sig"), csv_input=bool(args.csv))
    with Enrichment(args.directory) as service:
        previews = ([service.resolve(records[0], saved_evidence=packet)] if packet else service.batch(records))
        if args.command == "commit":
            output = [{"preview": preview, "commit": service.commit(item, preview, saved_evidence=packet)}
                      for item, preview in zip(records, previews, strict=True)]
        else:
            output = previews
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

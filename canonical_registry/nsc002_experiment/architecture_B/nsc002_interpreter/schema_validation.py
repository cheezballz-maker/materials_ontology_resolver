"""Validate NSC-002 schema and reuse NSC-001 referential integrity checks."""
import json
from dataclasses import replace
from pathlib import Path
from jsonschema import Draft202012Validator
from shared.semantic_interface import validate_interpretation
SCHEMA=Path(__file__).resolve().parents[2]/'NSC-002/semantic_constraint_schema.json'
def validate(value):
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf8'))).validate(value.to_dict())
    validate_interpretation(replace(value,contract_id='NSC-001',contract_version='2.0'))

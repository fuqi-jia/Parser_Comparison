#!/usr/bin/env python3
"""Hand-rolled validator for ``rdl_atoms.json`` payloads.

We deliberately avoid taking a dependency on ``jsonschema`` so that the
case study runs out of the box on a vanilla Python 3 install. The checks
below mirror ``schema/rdl_atoms.schema.json`` closely enough for our v1
needs but are intentionally pragmatic, not exhaustive.
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from typing import Any


VALID_STATUSES = {"ok", "unsupported", "error"}
VALID_MODES = {"conjunction", "boolean"}


def _err(path: str, msg: str) -> str:
    return f"{path}: {msg}"


def validate_payload(payload: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return [_err("$", "top-level value must be a JSON object")]

    status = payload.get("status")
    if status not in VALID_STATUSES:
        errors.append(_err("$.status", f"must be one of {sorted(VALID_STATUSES)}; got {status!r}"))

    if "frontend" not in payload or not isinstance(payload["frontend"], str):
        errors.append(_err("$.frontend", "must be a string identifying the front-end"))

    if status == "ok":
        mode = payload.get("mode")
        if mode not in VALID_MODES:
            errors.append(_err("$.mode", f"must be one of {sorted(VALID_MODES)}; got {mode!r}"))

        if mode == "conjunction":
            errors.extend(_validate_conjunction(payload))
        elif mode == "boolean":
            errors.extend(_validate_boolean(payload))

    if status in {"unsupported", "error"}:
        if not isinstance(payload.get("reason"), str):
            errors.append(_err("$.reason", "must be a string when status is unsupported or error"))

    return errors


def _validate_conjunction(payload: dict) -> list[str]:
    errors: list[str] = []

    variables = payload.get("variables")
    if not isinstance(variables, list) or not all(isinstance(v, str) for v in variables):
        errors.append(_err("$.variables", "must be a list of strings"))

    constraints = payload.get("constraints")
    if not isinstance(constraints, list):
        errors.append(_err("$.constraints", "must be a list"))
        return errors

    for i, c in enumerate(constraints):
        prefix = f"$.constraints[{i}]"
        if not isinstance(c, dict):
            errors.append(_err(prefix, "must be a JSON object"))
            continue
        for key in ("lhs", "rhs", "bound"):
            if not isinstance(c.get(key), str):
                errors.append(_err(f"{prefix}.{key}", "must be a string"))
        if not isinstance(c.get("strict"), bool):
            errors.append(_err(f"{prefix}.strict", "must be a boolean"))
        bound_str = c.get("bound")
        if isinstance(bound_str, str):
            try:
                Fraction(bound_str.strip())
            except (ValueError, ZeroDivisionError) as exc:
                errors.append(_err(f"{prefix}.bound", f"is not a valid rational literal: {exc}"))

    return errors


def _validate_boolean(payload: dict) -> list[str]:
    # Reserved for P1; we just check basic shape.
    errors: list[str] = []
    if not isinstance(payload.get("cnf"), list):
        errors.append(_err("$.cnf", "must be a list of clauses"))
    if not isinstance(payload.get("atoms"), dict):
        errors.append(_err("$.atoms", "must be an object mapping atom-id (string) to constraint"))
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate an rdl_atoms.json payload.")
    p.add_argument("rdl_atoms_json")
    args = p.parse_args(argv)

    try:
        with open(args.rdl_atoms_json, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"check: cannot load {args.rdl_atoms_json}: {exc}", file=sys.stderr)
        return 2

    errors = validate_payload(payload)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

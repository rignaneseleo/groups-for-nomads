#!/usr/bin/env python3
import sys
import os
import json
import argparse
from typing import Any, Deque, List, Optional, Tuple

import jsonschema
from jsonschema.exceptions import best_match
from jsonschema.validators import validator_for

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.comments import CommentedMap, CommentedSeq


EXIT_SUCCESS = 0
EXIT_BAD_ARGS = 2
EXIT_SCHEMA_ERROR = 3
EXIT_YAML_PARSE_ERROR = 4
EXIT_VALIDATION_ERROR = 5
EXIT_UNEXPECTED_ERROR = 6


def gha_escape(s: str) -> str:
    # Per GitHub Actions command escaping
    return str(s).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def path_to_str(path: Deque[Any]) -> str:
    if not path:
        return "$"
    parts: List[str] = []
    for p in list(path):
        if isinstance(p, int):
            parts.append(f"[{p}]")
        else:
            if parts and not parts[-1].startswith("["):
                parts.append(".")
            parts.append(str(p))
    # Join while keeping bracketed indices tight
    out = ""
    for part in parts:
        if part == ".":
            out += "."
        else:
            out += part
    # Normalize "$.foo[0].bar"
    if not out.startswith("$"):
        out = "$." + out.lstrip(".")
    return out


def resolve_schema_path(yaml_file: str, cli_schema: Optional[str]) -> str:
    candidates: List[str] = []
    env_schema = os.getenv("SCHEMA_PATH")
    if cli_schema:
        candidates.append(cli_schema)
    if env_schema:
        candidates.append(env_schema)

    yaml_dir = os.path.dirname(os.path.abspath(yaml_file))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    candidates.extend(
        [
            os.path.join(yaml_dir, "schema.json"),
            os.path.join(script_dir, "schema.json"),
            os.path.join(cwd, "schema.json"),
        ]
    )

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError(
        f"Schema file not found. Checked: {', '.join([c for c in candidates if c])}"
    )


def load_schema(schema_path: str) -> Any:
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        # Validate the schema itself with the appropriate validator
        v_cls = validator_for(schema)
        v_cls.check_schema(schema)
        return schema
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON Schema at {schema_path}: {e}") from e
    except jsonschema.exceptions.SchemaError as e:
        raise ValueError(f"Schema is not a valid JSON Schema: {e.message}") from e
    except OSError as e:
        raise FileNotFoundError(f"Could not read schema file {schema_path}: {e}") from e


def load_yaml_with_positions(file_path: str) -> Any:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Use round-trip to keep line/column metadata (CommentedMap/Seq)
            yaml_parser = YAML(typ="rt")
            return yaml_parser.load(f)
    except FileNotFoundError as e:
        raise
    except YAMLError as e:
        # Attempt to extract line/column
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            line = mark.line + 1
            col = mark.column + 1
            raise SyntaxError(f"YAML parse error at line {line}, column {col}: {e}") from e
        raise SyntaxError(f"YAML parse error: {e}") from e
    except OSError as e:
        raise OSError(f"Could not read YAML file {file_path}: {e}") from e


def get_position_from_path(root: Any, path: Deque[Any]) -> Tuple[Optional[int], Optional[int]]:
    """
    Best-effort mapping from a jsonschema error path to YAML line/column using ruamel metadata.
    Returns 1-based (line, col) if available.
    """
    container = root
    parent = None
    key_or_index: Any = None
    try:
        for part in list(path):
            parent = container
            key_or_index = part
            container = container[part]  # Works for dict/list and ruamel types
    except Exception:
        # If traversal fails, we can't determine the position
        parent = None

    try:
        if isinstance(parent, CommentedMap):
            # lc.data is a dict: key -> (line, col)
            if key_or_index in parent.lc.data:
                line, col = parent.lc.data[key_or_index]
                return line + 1, col + 1
        elif isinstance(parent, CommentedSeq):
            # lc.data is a list: index -> (line, col)
            if isinstance(key_or_index, int) and 0 <= key_or_index < len(parent.lc.data):
                line, col = parent.lc.data[key_or_index]
                return line + 1, col + 1
    except Exception:
        pass

    # Fallback, try container itself (e.g., entire document)
    try:
        if hasattr(container, "lc"):
            line = getattr(container.lc, "line", None)
            col = getattr(container.lc, "col", None)
            if line is not None and col is not None:
                return line + 1, col + 1
    except Exception:
        pass

    return None, None


def format_text_error(
    file_path: str, err: jsonschema.ValidationError, line: Optional[int], col: Optional[int]
) -> str:
    parts = []
    parts.append("Validation error:")
    parts.append(f"  file: {file_path}")
    if line is not None and col is not None:
        parts.append(f"  location: line {line}, column {col}")
    parts.append(f"  path: {path_to_str(err.absolute_path)}")
    parts.append(f"  schema_path: {'.'.join([str(x) for x in list(err.absolute_schema_path)])}")
    parts.append(f"  message: {err.message}")
    parts.append(f"  validator: {err.validator}")
    parts.append(f"  validator_value: {repr(err.validator_value)}")
    # Show instance in a compact way if small
    try:
        instance_preview = repr(err.instance)
        if len(instance_preview) > 200:
            instance_preview = instance_preview[:197] + "..."
        parts.append(f"  instance: {instance_preview}")
    except Exception:
        pass
    return "\n".join(parts)


def format_json_error(
    file_path: str, err: jsonschema.ValidationError, line: Optional[int], col: Optional[int]
) -> dict:
    return {
        "type": "ValidationError",
        "file": file_path,
        "line": line,
        "column": col,
        "path": list(err.absolute_path),
        "path_str": path_to_str(err.absolute_path),
        "schema_path": list(err.absolute_schema_path),
        "message": err.message,
        "validator": err.validator,
        "validator_value": err.validator_value,
        # Avoid serializing complex YAML types
        "instance_repr": repr(err.instance),
    }


def print_gha_error(file_path: str, message: str, line: Optional[int], col: Optional[int]) -> None:
    l = line if line is not None else 1
    c = col if col is not None else 1
    print(f"::error file={file_path},line={l},col={c}::{gha_escape(message)}")


def validate_yaml(
    file_path: str,
    schema_path: str,
    output_format: str = "text",
    fail_fast: bool = False,
    quiet: bool = False,
) -> int:
    # Load schema
    try:
        schema = load_schema(schema_path)
    except Exception as e:
        msg = f"Schema load error: {e}"
        if output_format == "gha":
            print_gha_error(schema_path, msg, None, None)
        else:
            print(msg)
        return EXIT_SCHEMA_ERROR

    # Load YAML
    try:
        data = load_yaml_with_positions(file_path)
    except FileNotFoundError as e:
        msg = f"YAML file not found: {e}"
        if output_format == "gha":
            print_gha_error(file_path, msg, None, None)
        else:
            print(msg)
        return EXIT_YAML_PARSE_ERROR
    except SyntaxError as e:
        # Already includes line/col in message
        if output_format == "gha":
            # Best-effort extract numbers from message
            line = None
            col = None
            text = str(e)
            # Not robust but fine for annotation
            import re

            m = re.search(r"line (\d+), column (\d+)", text)
            if m:
                line = int(m.group(1))
                col = int(m.group(2))
            print_gha_error(file_path, text, line, col)
        else:
            print(f"YAML syntax error in {file_path}: {e}")
        return EXIT_YAML_PARSE_ERROR
    except OSError as e:
        msg = f"Could not read YAML file: {e}"
        if output_format == "gha":
            print_gha_error(file_path, msg, None, None)
        else:
            print(msg)
        return EXIT_YAML_PARSE_ERROR
    except Exception as e:
        msg = f"Unexpected error while reading YAML: {e}"
        if output_format == "gha":
            print_gha_error(file_path, msg, None, None)
        else:
            print(msg)
        return EXIT_UNEXPECTED_ERROR

    # Validate
    try:
        v_cls = validator_for(schema)
        v = v_cls(schema)
        errors = list(v.iter_errors(data))
    except Exception as e:
        msg = f"Unexpected error during validation: {e}"
        if output_format == "gha":
            print_gha_error(file_path, msg, None, None)
        else:
            print(msg)
        return EXIT_UNEXPECTED_ERROR

    if not errors:
        if not quiet:
            if output_format == "gha":
                # No GHA annotation on success; print a friendly line
                print(f"YAML validation successful for {file_path}")
            elif output_format == "json":
                print(json.dumps({"status": "ok", "file": file_path}, indent=2))
            else:
                print("YAML validation successful!")
        return EXIT_SUCCESS

    # If fail_fast, collapse to best_match
    if fail_fast:
        bm = best_match(errors)
        errors = [bm] if bm is not None else errors[:1]

    # Sort errors: by path length then message
    errors.sort(key=lambda e: (len(list(e.absolute_path)), str(e)))

    if output_format == "json":
        out = {
            "status": "error",
            "file": file_path,
            "schema": schema_path,
            "errorCount": len(errors),
            "errors": [],
        }
        for err in errors:
            line, col = get_position_from_path(data, err.absolute_path)
            out["errors"].append(format_json_error(file_path, err, line, col))
        print(json.dumps(out, indent=2))
    elif output_format == "gha":
        for err in errors:
            line, col = get_position_from_path(data, err.absolute_path)
            message = f"{err.message} (path: {path_to_str(err.absolute_path)}; validator: {err.validator})"
            print_gha_error(file_path, message, line, col)
        # Also print a summary line for logs
        print(f"{len(errors)} validation error(s) in {file_path}")
    else:
        print(f"Found {len(errors)} validation error(s) in {file_path}:")
        for idx, err in enumerate(errors, start=1):
            line, col = get_position_from_path(data, err.absolute_path)
            print(f"\n[{idx}/{len(errors)}]")
            print(format_text_error(file_path, err, line, col))

    return EXIT_VALIDATION_ERROR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a YAML file against a JSON Schema with detailed reporting."
    )
    parser.add_argument("yaml_file", help="Path to the YAML file to validate.")
    parser.add_argument(
        "-s",
        "--schema",
        dest="schema",
        default=None,
        help="Path to the JSON Schema file. "
        "If not provided, uses SCHEMA_PATH env var or searches for schema.json in the YAML directory, script directory, and CWD.",
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="fmt",
        choices=["text", "json", "gha"],
        default="text",
        help="Output format: text (default), json, or gha (GitHub Actions annotations).",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first (best) validation error.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress success output.",
    )

    args = parser.parse_args()

    file_path = args.yaml_file
    try:
        schema_path = resolve_schema_path(file_path, args.schema)
    except Exception as e:
        msg = f"{e}"
        if args.fmt == "gha":
            print_gha_error(file_path, msg, None, None)
        else:
            print(msg)
        sys.exit(EXIT_SCHEMA_ERROR)

    exit_code = validate_yaml(
        file_path=file_path,
        schema_path=schema_path,
        output_format=args.fmt,
        fail_fast=args.fail_fast,
        quiet=args.quiet,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"Unexpected failure: {e}")
        sys.exit(EXIT_UNEXPECTED_ERROR)

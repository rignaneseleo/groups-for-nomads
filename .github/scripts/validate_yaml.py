#!/usr/bin/env python3
import sys
import json
import jsonschema
from ruamel.yaml import YAML


def load_schema():
    with open("schema.json", "r") as schema_file:
        return json.load(schema_file)


def validate_yaml(file_path):
    try:
        # Load the schema
        schema = load_schema()

        # Load the YAML file
        with open(file_path, "r") as yaml_file:
            yaml_parser = YAML(typ="safe")
            data = yaml_parser.load(yaml_file)

        # Validate against JSON Schema
        jsonschema.validate(instance=data, schema=schema)

        print("YAML validation successful!")
        return True

    except jsonschema.exceptions.ValidationError as ve:
        print(f"Validation error: {ve}")
        # Provide more detailed error context
        print(f"Validation failed at: {ve.json_path}")
        print(f"Validator keyword: {ve.validator}")
        print(f"Validator value: {ve.validator_value}")
        return False
    except Exception as e:
        print(f"Unexpected error during validation: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Please provide the path to the YAML file")
        sys.exit(1)

    file_path = sys.argv[1]

    if validate_yaml(file_path):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

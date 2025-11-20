import sys
import os
import pytest
import json

# Add the scripts directory to sys.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".github", "scripts"))
)

import validate_yaml


# Mock schema path resolution
@pytest.fixture
def schema_path(tmp_path):
    path = tmp_path / "schema.json"
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    path.write_text(json.dumps(schema), encoding="utf-8")
    return str(path)


def test_validate_yaml_valid(tmp_path, schema_path):
    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text("name: Test\n", encoding="utf-8")

    exit_code = validate_yaml.validate_yaml(str(yaml_file), schema_path, quiet=True)
    assert exit_code == validate_yaml.EXIT_SUCCESS


def test_validate_yaml_invalid(tmp_path, schema_path):
    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text("age: 25\n", encoding="utf-8")  # Missing required 'name'

    exit_code = validate_yaml.validate_yaml(str(yaml_file), schema_path, quiet=True)
    assert exit_code == validate_yaml.EXIT_VALIDATION_ERROR


def test_validate_yaml_bad_syntax(tmp_path, schema_path):
    yaml_file = tmp_path / "data.yaml"
    yaml_file.write_text("name: [unclosed list\n", encoding="utf-8")

    exit_code = validate_yaml.validate_yaml(str(yaml_file), schema_path, quiet=True)
    assert exit_code == validate_yaml.EXIT_YAML_PARSE_ERROR

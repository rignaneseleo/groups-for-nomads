# .github/scripts/validate_yaml.py
from pykwalify.core import Core
import sys


def validate_yaml(data_file, schema_file):
    try:
        # Initialize pykwalify with the data and schema files
        validator = Core(source_file=data_file, schema_files=[schema_file])
        # Perform validation
        validator.validate(raise_exception=True)
        print(f"Validation successful: {data_file} conforms to {schema_file}")
        return 0
    except Exception as e:
        print(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_yaml.py <data_file> <schema_file>")
        sys.exit(1)

    data_file = sys.argv[1]
    schema_file = sys.argv[2]
    sys.exit(validate_yaml(data_file, schema_file))

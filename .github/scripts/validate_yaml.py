# .github/scripts/validate_yaml.py
import yaml
import sys
import re
import jsonschema
import pycountry
from iso3166 import countries

# Define important variables and enums
VALID_PLATFORMS = [
    "whatsapp",
    "telegram",
    "discord",
    "facebook",
    "slack",
    "linktree",
    "wechat",
    "kakaotalk",
    "viber",
    "messenger",
    "signal",
    "website",
]

VALID_CONTINENTS = [
    "Africa",
    "Antarctica",
    "Asia",
    "Europe",
    "North America",
    "Oceania",
    "South America",
    "Central America",
]

# Define the schema for the directory.yaml file
schema = {
    "type": "object",
    "required": ["version", "groups"],
    "properties": {
        "version": {"type": "number"},
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "platform", "url"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "platform": {
                        "type": "string",
                        "enum": VALID_PLATFORMS,
                    },
                    "url": {"type": "string", "format": "uri", "pattern": "^https?://"},
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "continent": {
                                    "type": "string",
                                    "enum": VALID_CONTINENTS,
                                },
                                "country_id": {
                                    "type": "string",
                                    "minLength": 2,
                                    "maxLength": 2,
                                },
                                "city": {"type": "string"},
                                "region": {"type": "string"},
                            },
                        },
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "language_id": {"type": "string", "minLength": 2, "maxLength": 2},
                    "commercial": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
    },
}


def validate_url(url):
    """Simple URL validation beyond the schema's pattern check"""
    if not url.startswith("http://") and not url.startswith("https://"):
        return False
    # Basic URL pattern
    pattern = re.compile(
        r"^(?:http|https)://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))


def validate_country_code(country_code):
    """Validate that country_id is a valid ISO 3166-1 alpha-2 code"""
    try:
        countries.get(country_code)
        return True
    except KeyError:
        return False


def validate_language_code(language_code):
    """Validate that language_id is a valid ISO 639-1 code"""
    try:
        return pycountry.languages.get(alpha_2=language_code) is not None
    except (KeyError, AttributeError):
        return False


def main():
    try:
        with open("directory.yaml", "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # Validate against JSON schema
        jsonschema.validate(instance=data, schema=schema)

        # Additional custom validations
        errors = []

        for i, group in enumerate(data.get("groups", [])):
            # Check URL more thoroughly
            if not validate_url(group.get("url", "")):
                errors.append(
                    f"Group #{i+1} '{group.get('name')}': Invalid URL format: {group.get('url')}"
                )

            # Check country codes
            if "locations" in group:
                for j, location in enumerate(group["locations"]):
                    if "country_id" in location and not validate_country_code(
                        location["country_id"]
                    ):
                        errors.append(
                            f"Group #{i+1} '{group.get('name')}': Invalid country code: {location['country_id']}"
                        )

            # Check language code
            if "language_id" in group and not validate_language_code(
                group["language_id"]
            ):
                errors.append(
                    f"Group #{i+1} '{group.get('name')}': Invalid language code: {group['language_id']}"
                )

            # Check for duplicate entries
            # This is a simple check for exact duplicates - you may want to enhance this
            for j, other_group in enumerate(data.get("groups", [])):
                if (
                    i != j
                    and group["name"] == other_group["name"]
                    and group["url"] == other_group["url"]
                ):
                    errors.append(
                        f"Group #{i+1} '{group.get('name')}': Duplicate entry with group #{j+1}"
                    )

        if errors:
            print("Validation failed with the following errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("directory.yaml validation successful! ✅")
            sys.exit(0)

    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except jsonschema.exceptions.ValidationError as e:
        print(f"Schema validation error: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

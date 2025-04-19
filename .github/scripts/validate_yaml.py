# .github/scripts/validate_yaml.py
import yaml
import sys
import re
import jsonschema
import pycountry
from iso3166 import countries


class Platform:
    def __init__(self, pattern):
        self.pattern = re.compile(pattern, re.IGNORECASE)

    def validate(self, url):
        return bool(self.pattern.match(url))


# Define important variables and enums
class Platforms:
    WHATSAPP = Platform(r"^https://(?:chat\.whatsapp\.com/|wa\.me/)[A-Za-z0-9+_\-]+")
    TELEGRAM = Platform(r"^https://t\.me/[A-Za-z0-9+_\-]+")
    DISCORD = Platform(r"^https://discord\.(?:gg|com)/[A-Za-z0-9+_\-]+")
    FACEBOOK = Platform(r"^https://(?:www\.)?facebook\.com/(?:groups/)?[A-Za-z0-9.]+")
    SLACK = Platform(r"^https://[A-Za-z0-9\-]+\.slack\.com/")
    LINKTREE = Platform(r"^https://linktr\.ee/[A-Za-z0-9_\-]+")
    WECHAT = Platform(r"^https://(?:www\.)?wechat\.com/")
    KAKAOTALK = Platform(r"^https://(?:www\.)?kakaocorp\.com/")
    VIBER = Platform(r"^https://(?:invite\.)?viber\.com/")
    MESSENGER = Platform(r"^https://(?:www\.)?messenger\.com/")
    SIGNAL = Platform(r"^https://signal\.(?:group|me)/")
    WEBSITE = Platform(
        r"^https?://(?:www\.)?[A-Za-z0-9][A-Za-z0-9-]{0,61}[A-Za-z0-9](?:\.[A-Za-z]{2,})+"
    )

    @classmethod
    def get_all(cls):
        return {
            name.lower(): value
            for name, value in cls.__dict__.items()
            if isinstance(value, Platform) and not name.startswith("_")
        }

    @classmethod
    def get_names(cls):
        return list(cls.get_all().keys())


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
                        "enum": Platforms.get_names(),
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


def validate_url(url, platform):
    """Validate URL based on the platform-specific pattern"""
    if not url.startswith("http://") and not url.startswith("https://"):
        return False

    # Use platform-specific regex if available
    platforms = Platforms.get_all()
    if platform in platforms:
        return platforms[platform].validate(url)

    return False


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
            # Check URL more thoroughly with platform-specific validation
            platform = group.get("platform", "")
            url = group.get("url", "")
            if not validate_url(url, platform):
                errors.append(
                    f"Group #{i+1} '{group.get('name')}': Invalid URL format for platform '{platform}': {url}"
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

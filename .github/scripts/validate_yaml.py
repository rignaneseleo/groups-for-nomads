import yaml
import sys
import re
import os
from pykwalify.core import Core
from pykwalify.errors import SchemaError, CoreError

# Platform-specific URL patterns
PLATFORM_URL_PATTERNS = {
    "whatsapp": r"^https://(?:chat\.whatsapp\.com/|wa\.me/)[A-Za-z0-9+_\-]+",
    "telegram": r"^https://t\.me/[A-Za-z0-9+_\-]+",
    "discord": r"^https://discord\.(?:gg|com)/[A-Za-z0-9+_\-]+",
    "facebook": r"^https://(?:www\.)?facebook\.com/(?:groups/)?[A-Za-z0-9.]+",
    "slack": r"^https://[A-Za-z0-9\-]+\.slack\.com/",
    "linktree": r"^https://linktr\.ee/[A-Za-z0-9_\-]+",
    "wechat": r"^https://(?:www\.)?wechat\.com/",
    "kakaotalk": r"^https://(?:www\.)?kakaocorp\.com/",
    "viber": r"^https://(?:invite\.)?viber\.com/",
    "messenger": r"^https://(?:www\.)?messenger\.com/",
}


def validate_platform_urls(data):
    """Validate URLs based on the platform-specific patterns"""
    errors = []

    for i, group in enumerate(data.get("groups", [])):
        platform = group.get("platform", "")
        url = group.get("url", "")

        if platform in PLATFORM_URL_PATTERNS:
            pattern = re.compile(PLATFORM_URL_PATTERNS[platform], re.IGNORECASE)
            if not pattern.match(url):
                errors.append(
                    f"Group #{i+1} '{group.get('name')}': Invalid URL format for platform '{platform}': {url}"
                )

    return errors


def validate_country_codes(data):
    """Validate country codes if present"""
    errors = []

    for i, group in enumerate(data.get("groups", [])):
        if "locations" in group:
            for j, location in enumerate(group["locations"]):
                if "country_id" in location:
                    country_id = location["country_id"]
                    # Simple check for ISO 3166-1 alpha-2 format (2 uppercase letters)
                    if not re.match(r"^[A-Z]{2}$", country_id):
                        errors.append(
                            f"Group #{i+1} '{group.get('name')}': Invalid country code format: {country_id}"
                        )

    return errors


def validate_language_codes(data):
    """Validate language codes if present"""
    errors = []

    for i, group in enumerate(data.get("groups", [])):
        if "language_id" in group:
            language_id = group["language_id"]
            # Simple check for ISO 639-1 format (2 lowercase letters)
            if not re.match(r"^[a-z]{2}$", language_id):
                errors.append(
                    f"Group #{i+1} '{group.get('name')}': Invalid language code format: {language_id}"
                )

    return errors


def check_duplicates(data):
    """Check for duplicate entries"""
    errors = []
    unique_entries = set()

    for i, group in enumerate(data.get("groups", [])):
        name = group.get("name", "")
        url = group.get("url", "")
        entry_key = f"{name}:{url}"

        if entry_key in unique_entries:
            errors.append(f"Group #{i+1} '{name}': Duplicate entry found")
        else:
            unique_entries.add(entry_key)

    return errors


def main():
    try:
        # Load the directory YAML file
        with open("directory.yaml", "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        # Validate against schema.yaml
        validator = Core(source_data=data, schema_files=["schema.yaml"])
        try:
            validator.validate(raise_exception=True)
            print("Basic schema validation passed! ✓")
        except (SchemaError, CoreError) as e:
            print(f"Schema validation failed: {e}")
            sys.exit(1)

        # Perform platform-specific URL validation
        url_errors = validate_platform_urls(data)

        # Validate country and language codes
        country_errors = validate_country_codes(data)
        language_errors = validate_language_codes(data)

        # Check for duplicates
        duplicate_errors = check_duplicates(data)

        # Combine all errors
        all_errors = url_errors + country_errors + language_errors + duplicate_errors

        if all_errors:
            print("Validation failed with the following errors:")
            for error in all_errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("All validations passed successfully! ✅")

            # For GitHub Actions, set output
            if "GITHUB_OUTPUT" in os.environ:
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write("validation=success\n")

            sys.exit(0)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

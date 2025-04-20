#!/usr/bin/env python3
import os
import re
import yaml
import json
import sys
import argparse
from urllib.parse import urlparse


def sanitize_json_string(s):
    """Clean up the JSON string input"""
    if isinstance(s, dict):
        return s.get("body", "")
    # If it starts and ends with quotes, remove them and unescape internal quotes
    if isinstance(s, str):
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        # Unescape any escaped quotes
        s = s.replace('\\"', '"')
        try:
            # Try to parse as JSON in case it's a JSON string
            parsed = json.loads(s)
            if isinstance(parsed, dict) and "body" in parsed:
                return parsed["body"]
            return s
        except json.JSONDecodeError:
            return s
    return str(s)


def extract_form_data(body):
    """Extract form data from the issue body"""
    # First sanitize the input
    body = sanitize_json_string(body)

    # Define the fields we want to extract
    fields = {
        "platform": r"### Platform\s*\n\s*([^\n]+)",
        "name": r"### Group Name\s*\n\s*([^\n]+)",
        "url": r"### Group URL\s*\n\s*([^\n]+)",
        "continent": r"### Continent\s*\n\s*([^\n]+)",
        "country": r"### Country\s*\n\s*([^\n]+|_No response_)",
        "city": r"### City\s*\n\s*([^\n]+|_No response_)",
        "tags": r"### Tags\s*\n\s*([^\n]+|_No response_)",
        "description": r"### Description\s*\n\s*([^\n]+|_No response_)",
    }

    data = {}
    for field, pattern in fields.items():
        match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if value == "_No response_":
                value = ""
            data[field] = value
        else:
            data[field] = ""

    # Handle tags specially - split into list if present
    if data.get("tags"):
        data["tags"] = [tag.strip() for tag in data["tags"].split(",")]
    else:
        data["tags"] = []

    return data


def validate_data(data):
    """Validate the extracted data"""
    errors = []

    # Required fields
    if not data.get("name"):
        errors.append("Group name is required")

    if not data.get("url"):
        errors.append("Group URL is required")
    else:
        try:
            result = urlparse(data["url"])
            if not all([result.scheme, result.netloc]):
                errors.append("Invalid URL format")
        except Exception:
            errors.append("Invalid URL format")

    if not data.get("platform"):
        errors.append("Platform is required")

    if not data.get("continent"):
        errors.append("Continent is required")

    return errors


def generate_yaml_entry(data):
    """Generate YAML entry from the validated data"""
    # Platform name mapping
    platform_map = {
        "WhatsApp": "whatsapp",
        "Telegram": "telegram",
        "Discord": "discord",
        "Facebook": "facebook",
        "WeChat": "wechat",
        "KakaoTalk": "kakaotalk",
        "Linktree": "linktree",
        "Viber": "viber",
        "Messenger": "messenger",
    }

    entry = {
        "name": data["name"],
        "platform": platform_map.get(data["platform"], data["platform"].lower()),
        "url": data["url"],
    }

    # Add location information
    locations = []
    if data["continent"] != "World (for global groups)":
        location = {"continent": data["continent"]}
        if data["country"]:
            location["country_id"] = data["country"]
        if data["city"]:
            location["city"] = data["city"]
        locations.append(location)
        entry["locations"] = locations

    # Add optional fields if present
    if data["tags"]:
        entry["tags"] = data["tags"]
    if data["description"]:
        entry["description"] = data["description"]

    return entry


def write_github_output(key, value, file_path):
    """Write to GitHub Actions output file"""
    if file_path:
        with open(file_path, "a") as f:
            # Escape special characters in the value
            value = (
                str(value).replace("%", "%25").replace("\n", "%0A").replace("\r", "%0D")
            )
            f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Process digital nomad group submissions"
    )
    parser.add_argument(
        "--issue-body", required=True, help="The body of the GitHub issue"
    )
    parser.add_argument("--issue-number", required=True, help="The GitHub issue number")
    parser.add_argument("--github-output", help="Path to GitHub output file")
    args = parser.parse_args()

    try:
        # Extract and validate data
        data = extract_form_data(args.issue_body)
        validation_errors = validate_data(data)

        if validation_errors:
            # Write validation errors to GitHub output
            write_github_output("valid", "false", args.github_output)
            error_message = "The following errors were found:\\n- " + "\\n- ".join(
                validation_errors
            )
            write_github_output("message", error_message, args.github_output)
            sys.exit(1)

        # Generate new entry
        new_entry = generate_yaml_entry(data)

        # Load existing YAML file
        yaml_file = "directory.yaml"
        if os.path.exists(yaml_file):
            with open(yaml_file, "r", encoding="utf-8") as f:
                directory = yaml.safe_load(f) or {"version": 1.0, "groups": []}
        else:
            directory = {"version": 1.0, "groups": []}

        # Add new entry
        directory["groups"].append(new_entry)

        # Write updated YAML file
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(directory, f, allow_unicode=True, sort_keys=False)

        # Write success output
        write_github_output("valid", "true", args.github_output)
        write_github_output("group_name", data["name"], args.github_output)
        write_github_output("platform", data["platform"], args.github_output)

        # Format location string
        location_parts = [data["continent"]]
        if data["country"]:
            location_parts.append(data["country"])
        if data["city"]:
            location_parts.append(data["city"])
        location_str = ", ".join(location_parts)

        write_github_output("location", location_str, args.github_output)
        write_github_output(
            "message",
            "Your submission has been processed successfully!",
            args.github_output,
        )

    except Exception as e:
        # Write error output
        write_github_output("valid", "false", args.github_output)
        write_github_output(
            "message", f"An error occurred: {str(e)}", args.github_output
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

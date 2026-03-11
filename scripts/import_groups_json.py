#!/usr/bin/env python3
"""
Import groups from a JSON file (groups.json) into data.yaml,
converting to the YAML schema format and skipping duplicates by URL.
"""

import argparse
import json
import sys
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

COUNTRY_NAME_TO_ISO = {
    "Albania": "AL",
    "Argentina": "AR",
    "Australia": "AU",
    "Barbados": "BB",
    "Brazil": "BR",
    "Bulgaria": "BG",
    "Cambodia": "KH",
    "Canada": "CA",
    "China": "CN",
    "Colombia": "CO",
    "Costa Rica": "CR",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czechia": "CZ",
    "Denmark": "DK",
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "England": "GB",
    "France": "FR",
    "Georgia": "GE",
    "Germany": "DE",
    "Gibraltar": "GI",
    "Greece": "GR",
    "Guatemala": "GT",
    "Hong Kong": "HK",
    "Hungary": "HU",
    "India": "IN",
    "Indonesia": "ID",
    "Ireland": "IE",
    "Italy": "IT",
    "Japan": "JP",
    "Kenya": "KE",
    "Malaysia": "MY",
    "Malta": "MT",
    "Mexico": "MX",
    "Morocco": "MA",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Nicaragua": "NI",
    "Peru": "PE",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Romania": "RO",
    "Serbia": "RS",
    "Singapore": "SG",
    "Slovenia": "SI",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Taiwan": "TW",
    "Thailand": "TH",
    "Turkey": "TR",
    "United Arab Emirates": "AE",
    "United States": "US",
    "Vietnam": "VN",
}

COUNTRY_TO_CONTINENT = {
    "AL": "Europe",
    "AR": "South America",
    "AU": "Oceania",
    "BB": "Central America",
    "BR": "South America",
    "BG": "Europe",
    "KH": "Asia",
    "CA": "North America",
    "CN": "Asia",
    "CO": "South America",
    "CR": "Central America",
    "HR": "Europe",
    "CY": "Europe",
    "CZ": "Europe",
    "DK": "Europe",
    "EC": "South America",
    "EG": "Africa",
    "SV": "Central America",
    "GB": "Europe",
    "FR": "Europe",
    "GE": "Europe",
    "DE": "Europe",
    "GI": "Europe",
    "GR": "Europe",
    "GT": "Central America",
    "HK": "Asia",
    "HU": "Europe",
    "IN": "Asia",
    "ID": "Asia",
    "IE": "Europe",
    "IT": "Europe",
    "JP": "Asia",
    "KE": "Africa",
    "MY": "Asia",
    "MT": "Europe",
    "MX": "North America",
    "MA": "Africa",
    "NL": "Europe",
    "NZ": "Oceania",
    "NI": "Central America",
    "PE": "South America",
    "PH": "Asia",
    "PL": "Europe",
    "PT": "Europe",
    "RO": "Europe",
    "RS": "Europe",
    "SG": "Asia",
    "SI": "Europe",
    "ZA": "Africa",
    "KR": "Asia",
    "ES": "Europe",
    "LK": "Asia",
    "TW": "Asia",
    "TH": "Asia",
    "TR": "Asia",
    "AE": "Asia",
    "US": "North America",
    "VN": "Asia",
}

PLATFORM_MAP = {
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "discord": "discord",
    "facebook": "facebook",
    "reddit": "reddit",
    "meetup": "meetup",
    "slack": "slack",
    "instagram": "instagram",
    "linktree": "linktree",
}

TAG_NORMALIZE = {
    "Accommodation": "accommodation",
    "Crypto": "cryptocurrency",
    "Digital Nomads": "networking",
    "Events": "events",
    "Expat": "expats",
    "Expats": "expats",
    "Finance": "finance",
    "Food": "food",
    "Housing": "housing",
    "Jobs": "jobs",
    "Nightlife": "nightlife",
    "Outdoor Activities": "outdoors",
    "Social": "social",
    "Sports": "sports",
    "Travel": "backpacking",
    "Volunteering": "volunteering",
    "Women": "women",
    "LGBTQ+": "lgbtq",
    "Freelancers": "freelancing",
    "Coworking": "coworking",
    "Language Exchange": "language_exchange",
    "Health & Wellness": "wellness",
    "Tech": "technology",
    "Photography": "photography",
    "Art": "art",
    "Music": "music",
    "Pets": "pets",
    "Parenting": "parents",
    "Entrepreneurs": "entrepreneurship",
    "Real Estate": "real_estate",
    "Visa & Immigration": "visa",
}


def normalize_tag(tag: str) -> str:
    if tag in TAG_NORMALIZE:
        return TAG_NORMALIZE[tag]
    return tag.lower().replace(" ", "_").replace("&", "and").replace("-", "_")


def convert_group(src: dict) -> CommentedMap | None:
    group_name = src.get("group_name", "").strip()
    group_link = src.get("group_link", "").strip()
    platform_raw = src.get("type", "").strip().lower()

    if not group_name or not group_link:
        return None

    platform = PLATFORM_MAP.get(platform_raw)
    if platform is None:
        print(f"  WARNING: Unknown platform '{src.get('type')}' for '{group_name}', skipping", file=sys.stderr)
        return None

    entry = CommentedMap()
    entry["name"] = group_name
    entry["platform"] = platform
    entry["url"] = group_link

    country_name = src.get("country", "").strip()
    city = src.get("city", "").strip()

    if country_name and country_name != "Global":
        country_id = COUNTRY_NAME_TO_ISO.get(country_name)
        if not country_id:
            print(f"  WARNING: Unknown country '{country_name}' for '{group_name}'", file=sys.stderr)
            return None

        continent = COUNTRY_TO_CONTINENT.get(country_id, "")

        location = CommentedMap()
        location["continent"] = continent
        location["country_id"] = country_id

        if city and city != country_name:
            location["city"] = city

        locations = CommentedSeq()
        locations.append(location)
        entry["locations"] = locations

    tags_raw = src.get("tags", [])
    if tags_raw:
        tags = CommentedSeq()
        for t in tags_raw:
            normalized = normalize_tag(t.strip())
            if normalized and normalized not in tags:
                tags.append(normalized)
        if tags:
            entry["tags"] = tags

    return entry


def main():
    parser = argparse.ArgumentParser(description="Import groups from JSON into data.yaml")
    parser.add_argument("json_file", help="Path to the source JSON file")
    parser.add_argument(
        "--yaml-file",
        default="data.yaml",
        help="Path to the destination YAML file (default: data.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be added without modifying the YAML file",
    )
    args = parser.parse_args()

    with open(args.json_file, "r", encoding="utf-8") as f:
        src_groups = json.load(f)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(args.yaml_file, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    existing_urls = {g["url"] for g in data.get("groups", [])}

    added = 0
    skipped_dup = 0
    skipped_err = 0

    for src in src_groups:
        link = src.get("group_link", "").strip()
        if link in existing_urls:
            skipped_dup += 1
            continue

        entry = convert_group(src)
        if entry is None:
            skipped_err += 1
            continue

        if args.dry_run:
            print(f"  Would add: {entry['name']} ({entry['platform']}) - {entry['url']}")
        else:
            data["groups"].append(entry)
            existing_urls.add(link)

        added += 1

    if not args.dry_run and added > 0:
        with open(args.yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

    print(f"\nDone. Added: {added}, Skipped (duplicate): {skipped_dup}, Skipped (error): {skipped_err}")


if __name__ == "__main__":
    main()

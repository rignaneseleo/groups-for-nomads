#!/usr/bin/env python3
"""
Import WhatsApp groups from Elementor-style HTML into data.yaml.

Expected structure per group:
  <p><strong>Group: ...</strong></p>
  <p>Location: ...</p>
  <p>Category: ...</p>
  <p>...<a href="...">Join here</a>...</p>
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from urllib.parse import urlsplit, urlunsplit

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

COUNTRY_NAME_TO_ISO = {
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Egypt": "EG",
    "Georgia": "GE",
    "Greece": "GR",
    "Hungary": "HU",
    "Italy": "IT",
    "The Netherlands": "NL",
    "Netherlands": "NL",
    "Portugal": "PT",
    "Spain": "ES",
}

COUNTRY_TO_CONTINENT = {
    "HR": "Europe",
    "CY": "Europe",
    "CZ": "Europe",
    "EG": "Africa",
    "GE": "Europe",
    "GR": "Europe",
    "HU": "Europe",
    "IT": "Europe",
    "NL": "Europe",
    "PT": "Europe",
    "ES": "Europe",
}

CATEGORY_TO_TAG = {
    "social": "social",
    "sports": "sports",
    "sportsy": "sports",
    "foodie": "food",
    "lgbtq": "lgbtq",
    "artsy": "art",
}


def strip_tags(raw: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw)
    clean = html.unescape(clean)
    clean = clean.replace("\xa0", " ")
    return re.sub(r"\s+", " ", clean).strip()


def normalize_country(heading_text: str) -> str:
    text = strip_tags(heading_text)
    text = re.sub(r"\s*Digital Nomad WhatsApp Groups\s*$", "", text, flags=re.I)
    text = re.sub(r"^[^A-Za-z]+", "", text)
    return text.strip()


def normalize_url(url: str) -> str:
    raw = url.strip()
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    netloc = parts.netloc.lower()

    # WhatsApp links frequently include tracking query params; ignore those.
    if netloc == "chat.whatsapp.com":
        return urlunsplit((parts.scheme.lower(), netloc, path, "", ""))

    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))


def guess_tag(category: str) -> str:
    normalized = category.strip().lower()
    return CATEGORY_TO_TAG.get(normalized, "community")


def parse_groups(widget_html: str) -> list[dict[str, str]]:
    section_pattern = re.compile(
        r"<h3[^>]*>(.*?)</h3>(.*?)(?=<h3[^>]*>|$)",
        re.IGNORECASE | re.DOTALL,
    )
    group_pattern = re.compile(
        r"<p>\s*<strong>\s*Group:\s*(.*?)\s*</strong>\s*</p>\s*"
        r"<p>\s*Location:\s*(.*?)\s*</p>\s*"
        r"<p>\s*Category:\s*(.*?)\s*</p>\s*"
        r"<p>.*?<a[^>]*href=\"([^\"]+)\"[^>]*>.*?</a>.*?</p>",
        re.IGNORECASE | re.DOTALL,
    )

    parsed: list[dict[str, str]] = []
    for heading_html, section_html in section_pattern.findall(widget_html):
        country = normalize_country(heading_html)
        if not country:
            continue

        for name_html, location_html, category_html, href in group_pattern.findall(section_html):
            name = strip_tags(name_html)
            location = strip_tags(location_html)
            category = strip_tags(category_html)
            url = normalize_url(html.unescape(href))

            if not name or not url:
                continue

            parsed.append(
                {
                    "name": name,
                    "country": country,
                    "location": location,
                    "category": category,
                    "url": url,
                }
            )

    return parsed


def to_yaml_entry(group: dict[str, str]) -> CommentedMap | None:
    country = group["country"]
    country_id = COUNTRY_NAME_TO_ISO.get(country)
    if not country_id:
        print(f"WARNING: Unknown country '{country}', skipping '{group['name']}'", file=sys.stderr)
        return None

    entry = CommentedMap()
    entry["name"] = group["name"]
    entry["platform"] = "whatsapp"
    entry["url"] = group["url"]

    location = CommentedMap()
    location["continent"] = COUNTRY_TO_CONTINENT[country_id]
    location["country_id"] = country_id

    city = group["location"]
    if city and city.lower() not in {country.lower(), "global", "worldwide"}:
        location["city"] = city

    locations = CommentedSeq()
    locations.append(location)
    entry["locations"] = locations

    tags = CommentedSeq()
    tags.append(guess_tag(group["category"]))
    entry["tags"] = tags
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Elementor widget groups into data.yaml")
    parser.add_argument("--yaml-file", default="data.yaml", help="Path to data.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Show entries without writing")
    args = parser.parse_args()

    widget_html = sys.stdin.read()
    if not widget_html.strip():
        raise SystemExit("No HTML provided on stdin.")

    groups = parse_groups(widget_html)
    print(f"Parsed {len(groups)} groups from HTML")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(args.yaml_file, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    existing_urls = {normalize_url(g["url"]) for g in data.get("groups", []) if g.get("url")}
    seen_in_payload: set[str] = set()

    added = 0
    skipped_existing = 0
    skipped_payload_dup = 0
    skipped_errors = 0

    for group in groups:
        url = group["url"]
        if url in existing_urls:
            skipped_existing += 1
            continue
        if url in seen_in_payload:
            skipped_payload_dup += 1
            continue

        entry = to_yaml_entry(group)
        if entry is None:
            skipped_errors += 1
            continue

        if args.dry_run:
            print(f"  Would add: {entry['name']} ({entry['url']}) [{entry['tags'][0]}]")
        else:
            data["groups"].append(entry)
            existing_urls.add(url)
            seen_in_payload.add(url)
        added += 1

    if not args.dry_run and added:
        with open(args.yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

    print(
        f"Done. Added: {added}, Skipped existing: {skipped_existing}, "
        f"Skipped payload dup: {skipped_payload_dup}, Skipped errors: {skipped_errors}"
    )


if __name__ == "__main__":
    main()

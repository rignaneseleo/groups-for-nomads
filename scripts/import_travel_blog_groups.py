#!/usr/bin/env python3
"""
Import WhatsApp travel groups from a blog HTML snippet into data.yaml.

Input is read from stdin.
Only chat.whatsapp.com links are imported.
"""

from __future__ import annotations

import argparse
import html
import re
from html.parser import HTMLParser
from pathlib import Path

import yaml

COUNTRY_NAME_TO_ISO = {
    "Armenia": "AM",
    "Australia": "AU",
    "Azerbaijan": "AZ",
    "Cambodia": "KH",
    "Central America": None,
    "China": "CN",
    "Europe": None,
    "Georgia": "GE",
    "Hong Kong": "HK",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Iraq": "IQ",
    "Japan": "JP",
    "Kazakhstan": "KZ",
    "Korea": "KR",
    "Kyrgyzstan": "KG",
    "Laos": "LA",
    "Malaysia": "MY",
    "Maldives": "MV",
    "Mauritania": "MR",
    "Mexico": "MX",
    "Middle East": None,
    "Morocco": "MA",
    "Nepal": "NP",
    "New Zealand": "NZ",
    "North America": None,
    "Pakistan": "PK",
    "Philippines": "PH",
    "South America": None,
    "Sri Lanka": "LK",
    "Taiwan": "TW",
    "Thailand": "TH",
    "Turkiye": "TR",
    "Turkey": "TR",
    "Turkmenistan": "TM",
    "Vietnam": "VN",
}

COUNTRY_TO_CONTINENT = {
    "AM": "Asia",
    "AU": "Oceania",
    "AZ": "Asia",
    "KH": "Asia",
    "CN": "Asia",
    "GE": "Europe",
    "HK": "Asia",
    "IN": "Asia",
    "ID": "Asia",
    "IR": "Asia",
    "IQ": "Asia",
    "JP": "Asia",
    "KZ": "Asia",
    "KR": "Asia",
    "KG": "Asia",
    "LA": "Asia",
    "MY": "Asia",
    "MV": "Asia",
    "MR": "Africa",
    "MX": "North America",
    "MA": "Africa",
    "NP": "Asia",
    "NZ": "Oceania",
    "PK": "Asia",
    "PH": "Asia",
    "LK": "Asia",
    "TW": "Asia",
    "TH": "Asia",
    "TR": "Europe",
    "TM": "Asia",
    "VN": "Asia",
}

SECTION_CONTINENT_HINT = {
    "Asia WhatsApp Travel Groups": "Asia",
    "Central & South America WhatsApp Travel Groups": "South America",
    "North America WhatsApp Travel Groups": "North America",
    "Africa WhatsApp Travel Groups": "Africa",
    "Middle East WhatsApp Travel Groups": "Asia",
    "General Travel WhatsApp Groups": None,
}


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def escape_yaml_string(value: str) -> str:
    if not value:
        return '""'
    needs_quotes = any(
        [
            value.startswith((" ", "-", ":", "?", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`")),
            ":" in value,
            "#" in value,
            "\n" in value,
            value.startswith("{") or value.startswith("["),
            value in ("true", "false", "null", "yes", "no", "on", "off"),
        ]
    )
    if needs_quotes:
        return '"' + value.replace('"', '\\"') + '"'
    return value


def guess_primary_tag(name: str, section: str) -> str:
    text = f"{name} {section}".lower()
    if any(k in text for k in ("female", "girls", "women")):
        return "women"
    if "expat" in text:
        return "expats"
    if "couchsurf" in text:
        return "couchsurfing"
    if "overland" in text or "silk road" in text:
        return "overlanding"
    if "backpack" in text:
        return "backpacking"
    if "food" in text:
        return "food"
    if "coffee" in text:
        return "coffee"
    if "nightlife" in text:
        return "nightlife"
    if "art" in text:
        return "art"
    if "tech" in text:
        return "technology"
    if "work" in text:
        return "jobs"
    if "health" in text:
        return "health"
    if "travel" in text:
        return "travel"
    return "social"


def infer_country_id(h3_text: str, link_text: str) -> str | None:
    candidates: list[str] = []
    h3_clean = re.sub(r"\s+", " ", h3_text.replace("–", "-")).strip()
    link_clean = re.sub(r"\s+", " ", link_text.replace("–", "-")).strip()
    candidates.extend([h3_clean, link_clean])

    for text in candidates:
        for country_name, iso in COUNTRY_NAME_TO_ISO.items():
            if country_name and country_name.lower() in text.lower():
                return iso
    return None


def infer_city_from_text(text: str) -> str | None:
    known = [
        "Da Nang",
        "Kadikoy",
        "Agadir",
        "CDMX",
        "Mexico City",
        "Bali",
        "Java",
        "Sumatra",
        "Koh Samui",
        "Bangkok",
        "Chiang Mai",
        "Koh Phangan",
        "Koh Tao",
        "Khao Sok",
        "Phuket",
    ]
    lowered = text.lower()
    for city in known:
        if city.lower() in lowered:
            return city
    return None


class BlogListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_h2 = ""
        self.current_h3 = ""
        self.current_h4 = ""
        self.in_h2 = False
        self.in_h3 = False
        self.in_h4 = False
        self.in_li = False
        self.in_a = False
        self.current_li_text = ""
        self.current_links: list[tuple[str, str]] = []
        self.current_href = ""
        self.current_a_text = ""
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2":
            self.in_h2 = True
        elif tag == "h3":
            self.in_h3 = True
        elif tag == "h4":
            self.in_h4 = True
        elif tag == "li":
            self.in_li = True
            self.current_li_text = ""
            self.current_links = []
        elif tag == "a" and self.in_li:
            self.in_a = True
            self.current_href = ""
            self.current_a_text = ""
            for attr, value in attrs:
                if attr == "href" and value:
                    self.current_href = value

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2":
            self.in_h2 = False
        elif tag == "h3":
            self.in_h3 = False
        elif tag == "h4":
            self.in_h4 = False
        elif tag == "a" and self.in_a:
            self.in_a = False
            if self.current_href:
                self.current_links.append((self.current_href, self.current_a_text.strip()))
        elif tag == "li" and self.in_li:
            self.in_li = False
            for href, link_text in self.current_links:
                self.items.append(
                    {
                        "section_h2": self.current_h2.strip(),
                        "section_h3": self.current_h3.strip() or self.current_h4.strip(),
                        "li_text": self.current_li_text.strip(),
                        "link_text": link_text.strip(),
                        "href": href.strip(),
                    }
                )

    def handle_data(self, data: str) -> None:
        if self.in_h2:
            self.current_h2 += data
        elif self.in_h3:
            self.current_h3 += data
        elif self.in_h4:
            self.current_h4 += data
        if self.in_li:
            self.current_li_text += data
        if self.in_a:
            self.current_a_text += data


def build_entry(item: dict[str, str]) -> dict | None:
    url = normalize_url(html.unescape(item["href"]))
    if "chat.whatsapp.com/" not in url:
        return None

    section_h2 = html.unescape(item["section_h2"]).strip()
    section_h3 = html.unescape(item["section_h3"]).strip()
    link_text = html.unescape(item["link_text"]).strip()
    li_text = html.unescape(item["li_text"]).strip()

    if not link_text:
        return None

    generic = {"main chat", "main group", "one", "two", "join", "chat info"}
    if link_text.lower() in generic and section_h3:
        name = f"{section_h3} - {link_text.title()}"
    elif link_text.lower() in {"main chat", "main group"} and section_h2:
        name = f"{section_h2} - {link_text.title()}"
    else:
        name = link_text

    country_id = infer_country_id(section_h3, f"{link_text} {li_text}")
    continent = COUNTRY_TO_CONTINENT.get(country_id) if country_id else SECTION_CONTINENT_HINT.get(section_h2)
    city = infer_city_from_text(f"{section_h3} {link_text} {li_text}")

    entry = {
        "name": name,
        "platform": "whatsapp",
        "url": url,
        "locations": [],
        "tags": [guess_primary_tag(name, section_h2 or section_h3)],
    }

    if continent or country_id or city:
        loc = {}
        if continent:
            loc["continent"] = continent
        if country_id:
            loc["country_id"] = country_id
        if city and (not country_id or city.lower() not in section_h3.lower()):
            loc["city"] = city
        if loc:
            entry["locations"] = [loc]

    return entry


def format_entry(entry: dict) -> str:
    lines = [
        f"  - name: {escape_yaml_string(entry['name'])}",
        f"    platform: {entry['platform']}",
        f"    url: {entry['url']}",
    ]
    if entry.get("locations"):
        lines.append("    locations:")
        for loc in entry["locations"]:
            first_key = None
            for key in ("continent", "country_id", "city"):
                if key in loc:
                    first_key = key
                    break
            if not first_key:
                continue

            first_val = loc[first_key]
            if first_key == "city":
                first_val = escape_yaml_string(first_val)
            lines.append(f"      - {first_key}: {first_val}")

            for key in ("continent", "country_id", "city"):
                if key == first_key or key not in loc:
                    continue
                val = escape_yaml_string(loc[key]) if key == "city" else loc[key]
                lines.append(f"        {key}: {val}")
    if entry.get("tags"):
        lines.append("    tags:")
        for tag in entry["tags"]:
            lines.append(f"      - {tag}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WhatsApp groups from blog HTML into data.yaml")
    parser.add_argument("--yaml-file", default="data.yaml", help="Path to data.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print additions without writing file")
    args = parser.parse_args()

    html_content = Path("/dev/stdin").read_text(encoding="utf-8")
    if not html_content.strip():
        raise SystemExit("No HTML provided on stdin")

    blog_parser = BlogListParser()
    blog_parser.feed(html_content)

    raw_items = blog_parser.items
    entries = []
    for item in raw_items:
        entry = build_entry(item)
        if entry:
            entries.append(entry)

    with open(args.yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    existing_urls = {normalize_url((group or {}).get("url", "")) for group in data.get("groups", [])}

    to_add = []
    seen = set()
    for entry in entries:
        url = entry["url"]
        if url in existing_urls or url in seen:
            continue
        seen.add(url)
        to_add.append(entry)

    print(f"Parsed WhatsApp links: {len(entries)}")
    print(f"New groups to add: {len(to_add)}")

    if args.dry_run:
        for entry in to_add:
            print(f"  Would add: {entry['name']} ({entry['url']}) [{entry['tags'][0]}]")
        return

    if not to_add:
        return

    block = []
    for entry in to_add:
        block.append(format_entry(entry))

    with open(args.yaml_file, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("\n".join(block))
        f.write("\n")


if __name__ == "__main__":
    main()

from collections import defaultdict
from pathlib import Path

import yaml


def test_data_yaml_has_no_duplicate_links():
    data_path = Path(__file__).resolve().parents[1] / "data.yaml"
    with data_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    duplicates = defaultdict(list)
    for index, group in enumerate(data.get("groups", []), start=1):
        url = (group or {}).get("url")
        if not isinstance(url, str):
            continue
        normalized = url.strip()
        if normalized:
            duplicates[normalized].append(f"#{index}: {group.get('name', '<unknown>')}")

    duplicate_entries = {
        url: locations for url, locations in duplicates.items() if len(locations) > 1
    }
    assert not duplicate_entries, "Duplicate links found in data.yaml:\n" + "\n".join(
        f"- {url} -> {', '.join(locations)}"
        for url, locations in sorted(duplicate_entries.items())
    )

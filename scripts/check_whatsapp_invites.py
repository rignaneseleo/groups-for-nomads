#!/usr/bin/env python3
"""
Check WhatsApp invite links in data.yaml.

- Fails when inactive/offline links are found.
- Warns when invite page title differs from group name.
- Optional --apply mode updates names and removes inactive entries.
"""

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml


@dataclass
class LinkResult:
    status: str
    reason: str
    title: str


class WhatsAppInviteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.element_ids: set[str] = set()
        self.href_by_id: dict[str, str] = {}
        self._tag_depth = 0
        self._main_block_depth: int | None = None
        self._in_main_block_h3 = False
        self._current_h3 = ""
        self.main_block_h3_texts: list[str] = []
        self.main_block_has_image = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        self._tag_depth += 1
        attrs_map = dict(attrs)
        element_id = attrs_map.get("id")
        if element_id:
            self.element_ids.add(element_id)
            if element_id == "main_block":
                self._main_block_depth = self._tag_depth

        if tag == "a":
            href = attrs_map.get("href")
            if element_id and href:
                self.href_by_id[element_id] = href

        in_main_block = (
            self._main_block_depth is not None and self._tag_depth > self._main_block_depth
        )

        if tag == "img" and in_main_block and attrs_map.get("src"):
            self.main_block_has_image = True

        if tag == "h3" and in_main_block:
            self._in_main_block_h3 = True
            self._current_h3 = ""

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._in_main_block_h3:
            self._current_h3 += data

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == "h3" and self._in_main_block_h3:
            self._in_main_block_h3 = False
            self.main_block_h3_texts.append(self._current_h3.strip())

        if self._main_block_depth is not None and self._tag_depth == self._main_block_depth:
            self._main_block_depth = None

        if self._tag_depth > 0:
            self._tag_depth -= 1


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _fetch_html(url: str, timeout_seconds: int = 15) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read(250_000).decode("utf-8", errors="replace")


def _validate_link(url: str, retries: int) -> LinkResult:
    html = ""
    for attempt in range(retries + 1):
        try:
            html = _fetch_html(url)
            break
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(2 * (2**attempt))
                continue
            if exc.code == 429:
                return LinkResult("inconclusive", "HTTP 429 (rate limited)", "")
            return LinkResult("inactive", f"HTTP {exc.code}", "")
        except URLError as exc:
            return LinkResult("inactive", f"URL error: {exc.reason}", "")
        except TimeoutError:
            return LinkResult("inactive", "timeout", "")
        except Exception as exc:  # pragma: no cover
            return LinkResult("inactive", f"unexpected error: {exc}", "")

    parser = WhatsAppInviteHTMLParser()
    parser.feed(html)

    if "main_block" not in parser.element_ids:
        return LinkResult("inactive", "missing #main_block", "")

    action_button_href = parser.href_by_id.get("action-button", "")
    if not action_button_href.startswith("https://chat.whatsapp.com/"):
        return LinkResult("inactive", "missing/invalid #action-button invite href", "")

    web_button_href = parser.href_by_id.get("whatsapp-web-button", "")
    if not web_button_href.startswith("https://web.whatsapp.com/accept?code="):
        return LinkResult("inactive", "missing/invalid #whatsapp-web-button href", "")

    if not parser.main_block_has_image:
        return LinkResult("inactive", "group image is missing", "")

    title = next((t for t in parser.main_block_h3_texts if t), "")
    if not title:
        return LinkResult("inactive", "group title is empty", "")

    return LinkResult("active", "ok", title)


def _sleep_with_jitter(delay_ms: int, jitter_ms: int) -> None:
    if delay_ms <= 0 and jitter_ms <= 0:
        return
    extra = random.randint(0, jitter_ms) if jitter_ms > 0 else 0
    time.sleep((delay_ms + extra) / 1000.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-file", default="data.yaml")
    parser.add_argument("--urls-file", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delay-ms", type=int, default=1200)
    parser.add_argument("--jitter-ms", type=int, default=900)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    data_path = Path(args.data_file)
    with data_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    groups = data.get("groups", [])
    selected_urls: set[str] | None = None
    if args.urls_file:
        urls_path = Path(args.urls_file)
        if not urls_path.exists():
            print(f"URLs file not found: {urls_path}")
            return 2
        selected_urls = {
            line.strip()
            for line in urls_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("https://chat.whatsapp.com/")
        }
        if not selected_urls:
            print("No WhatsApp URLs to check from URLs file.")
            return 0

    inactive_urls: set[str] = set()
    rename_by_url: dict[str, str] = {}

    whatsapp_groups_all = [
        g
        for g in groups
        if isinstance(g, dict)
        and isinstance(g.get("url"), str)
        and g.get("url", "").strip().startswith("https://chat.whatsapp.com/")
    ]
    if selected_urls is None:
        whatsapp_groups = whatsapp_groups_all
    else:
        whatsapp_groups = [
            g for g in whatsapp_groups_all if g.get("url", "").strip() in selected_urls
        ]
        if not whatsapp_groups:
            print("No matching WhatsApp groups found in data.yaml for selected URLs.")
            return 0

    total = len(whatsapp_groups)
    print(f"Checking {total} WhatsApp links...")
    for idx, group in enumerate(whatsapp_groups, start=1):
        url = group["url"].strip()
        name = str(group.get("name", "<unknown>"))
        _sleep_with_jitter(max(0, args.delay_ms), max(0, args.jitter_ms))
        result = _validate_link(url, max(0, args.retries))

        if result.status != "active":
            inactive_urls.add(url)
            print(f"[{idx}/{total}] OFFLINE {name} -> {url} | {result.reason}")
            continue

        if _normalize_name(name) != _normalize_name(result.title):
            rename_by_url[url] = result.title
            print(
                f"[{idx}/{total}] WARNING name mismatch: {name} -> {result.title} | {url}"
            )
            print(
                "MISMATCH_JSON "
                + json.dumps(
                    {"current_name": name, "live_name": result.title, "url": url},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"[{idx}/{total}] OK {name}")

    print()
    print(f"Offline groups: {len(inactive_urls)}")
    print(f"Name mismatches: {len(rename_by_url)}")

    if args.apply:
        new_groups = []
        removed = 0
        renamed = 0
        for group in groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            url = group.get("url")
            if not isinstance(url, str):
                new_groups.append(group)
                continue
            normalized = url.strip()
            if normalized in inactive_urls:
                removed += 1
                continue
            if normalized in rename_by_url:
                group["name"] = rename_by_url[normalized]
                renamed += 1
            new_groups.append(group)

        data["groups"] = new_groups
        with data_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        print(f"Applied changes to {data_path}: removed={removed}, renamed={renamed}")

    # Fail on offline links; mismatches are warnings.
    return 1 if inactive_urls else 0


if __name__ == "__main__":
    sys.exit(main())

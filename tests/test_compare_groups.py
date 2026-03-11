import os
import sys


sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

import compare_groups


def test_extract_urls_from_html_skips_header_rows_and_extracts_links():
    html = """
    <table>
      <tbody>
        <tr>
          <td><strong>ARGENTINA</strong></td>
          <td></td>
          <td></td>
          <td></td>
        </tr>
        <tr>
          <td>BA Nomads</td>
          <td>Argentina</td>
          <td>Buenos Aires</td>
          <td>
            <a href="https://chat.whatsapp.com/AAA">Join</a>
            <a href="https://t.me/ba_nomads">Telegram</a>
          </td>
        </tr>
      </tbody>
    </table>
    """

    groups = compare_groups.extract_urls_from_html(html)

    assert groups == [
        {
            "name": "BA Nomads",
            "country": "Argentina",
            "city": "Buenos Aires",
            "url": "https://chat.whatsapp.com/AAA",
        },
        {
            "name": "BA Nomads",
            "country": "Argentina",
            "city": "Buenos Aires",
            "url": "https://t.me/ba_nomads",
        },
    ]


def test_load_yaml_urls_reads_only_non_empty_urls(tmp_path):
    yaml_path = tmp_path / "data.yaml"
    yaml_path.write_text(
        """
version: "1.0"
groups:
  - name: First
    url: https://example.com/one
  - name: Second
    url:
  - name: Third
""".strip(),
        encoding="utf-8",
    )

    urls = compare_groups.load_yaml_urls(yaml_path)

    assert urls == {"https://example.com/one"}


def test_normalize_url_trims_and_removes_trailing_slashes():
    assert compare_groups.normalize_url("  https://example.com/path///  ") == (
        "https://example.com/path"
    )

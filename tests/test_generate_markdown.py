import sys
import os
import pytest

# Add the scripts directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.github', 'scripts')))

import generate_markdown

def test_generate_markdown_structure():
    data = {
        "version": "1.0",
        "groups": [
            {
                "name": "Global Group",
                "platform": "discord",
                "url": "https://discord.gg/global"
            },
            {
                "name": "Asian Group",
                "platform": "telegram",
                "url": "https://t.me/asia",
                "locations": [{"continent": "Asia"}]
            },
            {
                "name": "Thai Group",
                "platform": "line",
                "url": "https://line.me/thai",
                "locations": [{"continent": "Asia", "country_id": "TH"}]
            }
        ]
    }
    
    md = generate_markdown.generate_markdown(data)
    
    assert "# Index" in md
    assert "### [World](#world)" in md
    assert "### [Asia](#continent-asia)" in md
    
    # Check for World section content
    assert "# World <a name=\"world\"></a>" in md
    assert "[Global Group](https://discord.gg/global)" in md
    
    # Check for Continent section content
    assert "# Asia <a name=\"continent-asia\"></a>" in md
    assert "[Asian Group](https://t.me/asia)" in md
    
    # Check for Country section content
    assert "## Thailand 🇹🇭 <a name=\"thailand\"></a>" in md
    assert "[Thai Group](https://line.me/thai)" in md

def test_get_country_name():
    assert generate_markdown.get_country_name("US") == "United States of America"
    assert generate_markdown.get_country_name("TH") == "Thailand"
    # Test unknown code returns code
    assert generate_markdown.get_country_name("ZZ") == "ZZ"


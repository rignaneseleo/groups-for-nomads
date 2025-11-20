import sys
import os
import pytest
from ruamel.yaml.comments import CommentedMap

# Add the scripts directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.github', 'scripts')))

import process_new_group

def test_parse_issue_body_basic():
    body = """
### Group Name
My Awesome Group

### Platform
Telegram

### URL
https://t.me/awesomegroup
"""
    expected = {
        'name': 'My Awesome Group',
        'platform': 'telegram',
        'url': 'https://t.me/awesomegroup'
    }
    assert process_new_group.parse_issue_body(body) == expected

def test_parse_issue_body_full():
    body = """
### Group Name
Chiang Mai Nomads

### Platform
WhatsApp

### URL
https://chat.whatsapp.com/12345

### Continent
Asia

### Country Code
TH

### City
Chiang Mai

### Language Code
en

### Commercial
- [x] This is a commercial group

### Tags
coworking, social, hiking

### Additional Information
Great group!
"""
    result = process_new_group.parse_issue_body(body)
    
    assert result['name'] == 'Chiang Mai Nomads'
    assert result['platform'] == 'whatsapp'
    assert result['url'] == 'https://chat.whatsapp.com/12345'
    assert result['continent'] == 'Asia'
    assert result['country_id'] == 'TH'
    assert result['city'] == 'Chiang Mai'
    assert result['language_id'] == 'en'
    assert result['commercial'] is True
    assert result['tags'] == ['coworking', 'social', 'hiking']
    assert result['description'] == 'Great group!'

def test_parse_issue_body_empty_sections():
    body = """
### Group Name
Minimal Group

### Platform
Discord

### URL
https://discord.gg/minimal

### City
_No response_
"""
    result = process_new_group.parse_issue_body(body)
    assert result['name'] == 'Minimal Group'
    assert result['platform'] == 'discord'
    assert result['city'] is None

def test_create_group_entry():
    parsed_data = {
        'name': 'Test Group',
        'platform': 'slack',
        'url': 'https://slack.com/test',
        'continent': 'Europe',
        'country_id': 'DE',
        'commercial': False,
        'tags': ['tech']
    }
    
    entry = process_new_group.create_group_entry(parsed_data)
    
    assert isinstance(entry, CommentedMap)
    assert entry['name'] == 'Test Group'
    assert entry['platform'] == 'slack'
    assert entry['url'] == 'https://slack.com/test'
    assert len(entry['locations']) == 1
    assert entry['locations'][0]['continent'] == 'Europe'
    assert entry['locations'][0]['country_id'] == 'DE'
    assert 'commercial' not in entry # False values usually omitted or check implementation
    # checking implementation: if parsed_data.get('commercial'): group['commercial'] = True. So if False, it is omitted.
    assert entry['tags'] == ['tech']

def test_create_group_entry_commercial():
    parsed_data = {
        'name': 'Commercial Group',
        'platform': 'web',
        'url': 'https://example.com',
        'commercial': True
    }
    entry = process_new_group.create_group_entry(parsed_data)
    assert entry['commercial'] is True


import os
import re
import yaml
import json
import sys
from urllib.parse import urlparse

# Get environment variables
issue_number = os.environ.get('ISSUE_NUMBER')
issue_body = os.environ.get('ISSUE_BODY')

# The body is JSON-encoded, so we need to decode it
if issue_body.startswith('"') and issue_body.endswith('"'):
    issue_body = json.loads(issue_body)

# Extract form data
def extract_form_data(body):
    data = {}
    
    # Use a more robust approach to find the values
    platform_match = re.search(r'### Platform\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$)', body, re.DOTALL)
    name_match = re.search(r'### Group Name\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$)', body, re.DOTALL)
    url_match = re.search(r'### Group URL\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$)', body, re.DOTALL)
    continent_match = re.search(r'### Continent\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$)', body, re.DOTALL)
    country_match = re.search(r'### Country\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$|_No response_)', body, re.DOTALL)
    city_match = re.search(r'### City\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$|_No response_)', body, re.DOTALL)
    tags_match = re.search(r'### Tags\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$|_No response_)', body, re.DOTALL)
    description_match = re.search(r'### Description\s*\n\s*(\S.*?)(?:\n\s*###|\n\s*$|_No response_)', body, re.DOTALL)
    
    data['platform'] = platform_match.group(1).strip() if platform_match else None
    data['name'] = name_match.group(1).strip() if name_match else None
    data['url'] = url_match.group(1).strip() if url_match else None
    data['continent'] = continent_match.group(1).strip() if continent_match else None
    data['country'] = country_match.group(1).strip() if country_match and '_No response_' not in country_match.group(1) else ''
    data['city'] = city_match.group(1).strip() if city_match and '_No response_' not in city_match.group(1) else ''
    
    if tags_match and '_No response_' not in tags_match.group(1):
        data['tags'] = [tag.strip() for tag in tags_match.group(1).split(',')]
    else:
        data['tags'] = []
    
    data['description'] = description_match.group(1).strip() if description_match and '_No response_' not in description_match.group(1) else ''
    
    # Print out what we found for debugging
    print(f"Extracted data: {json.dumps(data, indent=2)}")
    
    return data

# Validate data
def validate_data(data):
    errors = []
    
    if not data['name']:
        errors.append("Group name is required")
    
    if not data['url']:
        errors.append("Group URL is required")
    else:
        # Basic URL validation
        try:
            result = urlparse(data['url'])
            if not all([result.scheme, result.netloc]):
                errors.append("Invalid URL format")
        except:
            errors.append("Invalid URL format")
    
    if not data['platform']:
        errors.append("Platform is required")
        
    if not data['continent']:
        errors.append("Continent is required")
    
    return errors

# Generate YAML entry
def generate_yaml_entry(data):
    platform_map = {
        'WhatsApp': 'whatsapp',
        'Telegram': 'telegram',
        'Discord': 'discord',
        'Facebook': 'facebook',
        'WeChat': 'wechat'
    }
    
    platform_key = platform_map.get(data['platform'], data['platform'].lower())
    
    entry = {
        'name': data['name'],
        'platform': platform_key,
        'url': data['url'],
        'location': {
            'continent': data['continent'],
        }
    }
    
    if data['country']:
        entry['location']['country'] = data['country']
    
    if data['city']:
        entry['location']['city'] = data['city']
    
    if data['tags']:
        entry['tags'] = data['tags']
        
    if data['description']:
        entry['description'] = data['description']
        
    return entry

# Process the submission
try:
    data = extract_form_data(issue_body)
    validation_errors = validate_data(data)

    if validation_errors:
        # Output errors using environment file
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"valid=false\n")
            error_message = "The following errors were found:\\n\\n" + "\\n".join([f"- {error}" for error in validation_errors])
            f.write(f"message={error_message}\n")
        sys.exit(0)

    # Check if directory.yaml exists, if not create a basic structure
    yaml_file = 'directory.yaml'
    if not os.path.exists(yaml_file):
        directory = {'version': '1.0', 'groups': []}
    else:
        # Read current YAML file
        with open(yaml_file, 'r') as file:
            directory = yaml.safe_load(file) or {'version': '1.0', 'groups': []}
        
        # Make sure the structure is valid
        if 'groups' not in directory:
            directory['groups'] = []

    # Generate new entry
    new_entry = generate_yaml_entry(data)

    # Add to directory
    directory['groups'].append(new_entry)

    # Write updated YAML
    with open(yaml_file, 'w') as file:
        yaml.dump(directory, file, sort_keys=False, default_flow_style=False)

    # Output success using environment file
    location_str = f"{data['continent']}"
    if data['country']:
        location_str += f", {data['country']}"
    if data['city']:
        location_str += f", {data['city']}"
        
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"valid=true\n")
        f.write(f"group_name={data['name']}\n")
        f.write(f"platform={data['platform']}\n")
        f.write(f"location={location_str}\n")
        f.write(f"message=Your submission has been processed successfully!\n")
    
except Exception as e:
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"valid=false\n")
        f.write(f"message=An error occurred: {str(e)}\n")
    sys.exit(1)

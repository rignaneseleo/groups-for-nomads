import os
import sys
import re
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

def parse_issue_body(body):
    """
    Parses the markdown body of the issue form.
    Returns a dictionary with the extracted fields.
    """
    data = {}
    # Split by H3 headers
    sections = re.split(r'^###\s+', body, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split('\n')
        header = lines[0].strip()
        content = '\n'.join(lines[1:]).strip()

        if content == "_No response_":
            content = None

        if header == "Group Name":
            data['name'] = content
        elif header == "Platform":
            data['platform'] = content.lower() if content else None
        elif header == "URL":
            data['url'] = content
        elif header == "Continent":
            data['continent'] = content
        elif header == "Country Code":
            data['country_id'] = content.upper() if content else None
        elif header == "City":
            data['city'] = content
        elif header == "Language Code":
            data['language_id'] = content.lower() if content else None
        elif header == "Commercial":
            # Checkbox handling: "- [x] This is a commercial group"
            data['commercial'] = "[x]" in content if content else False
        elif header == "Tags":
            if content:
                # Split by comma and strip whitespace
                tags = [t.strip() for t in content.split(',') if t.strip()]
                data['tags'] = tags
            else:
                data['tags'] = []
        elif header == "Additional Information":
            data['description'] = content

    return data

def create_group_entry(parsed_data):
    """
    Converts parsed data into the schema format.
    """
    group = CommentedMap()
    group['name'] = parsed_data.get('name')
    group['platform'] = parsed_data.get('platform')
    group['url'] = parsed_data.get('url')

    # Locations
    location = CommentedMap()
    if parsed_data.get('continent'):
        location['continent'] = parsed_data['continent']
    if parsed_data.get('country_id'):
        location['country_id'] = parsed_data['country_id']
    if parsed_data.get('city'):
        location['city'] = parsed_data['city']

    if location:
        group['locations'] = [location]

    # Optional fields
    if parsed_data.get('language_id'):
        group['language_id'] = parsed_data['language_id']

    if parsed_data.get('commercial'):
        group['commercial'] = True

    if parsed_data.get('tags'):
        group['tags'] = parsed_data['tags']

    if parsed_data.get('description'):
        group['description'] = parsed_data['description']

    return group

def main():
    issue_body = os.environ.get('ISSUE_BODY')
    if not issue_body:
        print("No issue body provided.")
        sys.exit(1)

    parsed_data = parse_issue_body(issue_body)

    # Basic validation
    if not parsed_data.get('name') or not parsed_data.get('url'):
        print("Missing required fields (Name or URL).")
        sys.exit(1)

    new_group = create_group_entry(parsed_data)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    file_path = 'data.yaml'

    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.load(f)

    if 'groups' not in data:
        data['groups'] = []

    data['groups'].append(new_group)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f)

    print(f"Added group: {new_group['name']}")

if __name__ == "__main__":
    main()

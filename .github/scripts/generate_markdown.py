# .github/scripts/generate_markdown.py
import yaml
import sys
from iso3166 import countries
from collections import defaultdict

# Platform icon mapping
PLATFORM_ICONS = {
    "whatsapp": "icons/whatsapp.svg",
    "telegram": "icons/telegram.svg",
    "discord": "icons/discord.svg",
    "linktree": "icons/linktree.svg",
    "facebook": "icons/facebook.svg",
    "slack": "icons/slack.svg",
    "kakaotalk": "icons/kakaotalk.svg",
    "viber": "icons/viber.svg",
    "messenger": "icons/messenger.svg",
    "wechat": "icons/wechat.svg",
    # Add more platforms as needed
}


def get_country_name(country_id):
    """Get country name from ISO 3166-1 alpha-2 code"""
    try:
        return countries.get(country_id).name
    except KeyError:
        return country_id  # Return the code if not found


def generate_markdown(data):
    """Generate markdown content from YAML data"""
    md_content = "# Index\n"
    md_content += "[//]: # (Continents and countries go here)\n"

    # Initialize structures to hold groups by region
    world_groups = []
    continent_groups = defaultdict(list)
    country_groups = defaultdict(list)
    city_groups = defaultdict(list)

    # Sort groups into categories
    for group in data.get("groups", []):
        if "locations" not in group or not group["locations"]:
            world_groups.append(group)
            continue

        for location in group["locations"]:
            if "continent" in location:
                continent = location["continent"]
                continent_groups[continent].append((group, location))

                if "country_id" in location:
                    country_id = location["country_id"]
                    country_name = get_country_name(country_id)
                    country_key = f"{country_id}_{country_name}"
                    country_groups[country_key].append((group, location))

                    if "city" in location:
                        city = location["city"]
                        city_key = f"{country_id}_{city}"
                        city_groups[city_key].append((group, location))

    # Generate table of contents
    md_content += "### [World](#world)\n\n"

    # Add continents to TOC
    continents = sorted(continent_groups.keys())
    for continent in continents:
        safe_anchor = continent.lower().replace(" ", "-")
        md_content += f"### [{continent}](#continent-{safe_anchor})\n"

        # Add countries within this continent to TOC
        countries_in_continent = {}
        for country_key in country_groups:
            country_id, country_name = country_key.split("_", 1)
            for group, location in country_groups[country_key]:
                if location.get("continent") == continent:
                    countries_in_continent[country_key] = country_name

        for country_key, country_name in sorted(
            countries_in_continent.items(), key=lambda x: x[1]
        ):
            country_id = country_key.split("_", 1)[0]
            safe_country_anchor = country_name.lower().replace(" ", "-")
            flag_emoji = (
                "🇦🇶"
                if country_id == "AQ"
                else "".join([chr(ord("🇦") + ord(c) - ord("A")) for c in country_id])
            )
            md_content += f"- [{flag_emoji} {country_name}](#{safe_country_anchor})\n"

        md_content += "\n"

    md_content += "------\n\n"

    # Generate World section
    md_content += '# World <a name="world"></a>\n'
    md_content += "[//]: # (Country-independent Networks and Communities go here)\n"

    for group in world_groups:
        platform = group.get("platform", "website")
        icon = PLATFORM_ICONS.get(platform, "")
        name = group.get("name", "Unknown Group")
        url = group.get("url", "#")

        if icon:
            md_content += f"![{platform.capitalize()}]({icon}) "
        md_content += f"[{name}]({url})\n\n"

    md_content += "<p>&nbsp;</p><p>&nbsp;</p>\n\n"

    # Generate Continent sections
    for continent in continents:
        safe_anchor = continent.lower().replace(" ", "-")
        md_content += f'# {continent} <a name="continent-{safe_anchor}"></a>\n\n'

        # Add continent-level groups
        continent_level_groups = []
        for group, location in continent_groups[continent]:
            if "country_id" not in location:
                continent_level_groups.append(group)

        for group in continent_level_groups:
            platform = group.get("platform", "website")
            icon = PLATFORM_ICONS.get(platform, "")
            name = group.get("name", "Unknown Group")
            url = group.get("url", "#")

            commercial = " (Commercial)" if group.get("commercial", False) else ""
            language = (
                f" ({group.get('language_id', '').upper()})"
                if "language_id" in group
                else ""
            )

            if icon:
                md_content += f"![{platform.capitalize()}]({icon}) "
            md_content += f"[{name}{language}{commercial}]({url})\n\n"

        # Generate Country sections within this continent
        countries_in_continent = {}
        for country_key in country_groups:
            country_id, country_name = country_key.split("_", 1)
            for group, location in country_groups[country_key]:
                if location.get("continent") == continent:
                    countries_in_continent[country_key] = country_name

        for country_key, country_name in sorted(
            countries_in_continent.items(), key=lambda x: x[1]
        ):
            country_id = country_key.split("_", 1)[0]
            safe_country_anchor = country_name.lower().replace(" ", "-")
            flag_emoji = (
                "🇦🇶"
                if country_id == "AQ"
                else "".join([chr(ord("🇦") + ord(c) - ord("A")) for c in country_id])
            )

            md_content += (
                f'## {country_name} {flag_emoji} <a name="{safe_country_anchor}"></a>\n'
            )

            # Find country-level groups (no city)
            country_level_groups = []
            for group, location in country_groups[country_key]:
                if location.get("continent") == continent and "city" not in location:
                    country_level_groups.append(group)

            for group in country_level_groups:
                platform = group.get("platform", "website")
                icon = PLATFORM_ICONS.get(platform, "")
                name = group.get("name", "Unknown Group")
                url = group.get("url", "#")

                commercial = " (Commercial)" if group.get("commercial", False) else ""
                language = (
                    f" ({group.get('language_id', '').upper()})"
                    if "language_id" in group
                    else ""
                )

                if icon:
                    md_content += f"![{platform.capitalize()}]({icon}) "
                md_content += f"[{name}{language}{commercial}]({url})\n\n"

            # Find cities in this country
            cities_in_country = set()
            for city_key in city_groups:
                city_country_id, city_name = city_key.split("_", 1)
                if city_country_id == country_id:
                    cities_in_country.add(city_name)

            # Generate City sections
            for city in sorted(cities_in_country):
                city_key = f"{country_id}_{city}"
                md_content += f"### {city}\n"

                for group, location in city_groups[city_key]:
                    if (
                        location.get("continent") == continent
                        and location.get("country_id") == country_id
                    ):
                        platform = group.get("platform", "website")
                        icon = PLATFORM_ICONS.get(platform, "")
                        name = group.get("name", "Unknown Group")
                        url = group.get("url", "#")

                        commercial = (
                            " (Commercial)" if group.get("commercial", False) else ""
                        )
                        language = (
                            f" ({group.get('language_id', '').upper()})"
                            if "language_id" in group
                            else ""
                        )

                        if icon:
                            md_content += f"![{platform.capitalize()}]({icon}) "
                        md_content += f"[{name}{language}{commercial}]({url})\n\n"

            md_content += "<p>&nbsp;</p><p>&nbsp;</p>\n\n"

    return md_content


def main():
    try:
        with open("directory.yaml", "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        md_content = generate_markdown(data)

        with open("directory.md", "w", encoding="utf-8") as output_file:
            output_file.write(md_content)

        print("Successfully generated directory.md from YAML data! ✅")
        sys.exit(0)

    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

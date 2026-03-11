#!/usr/bin/env python3
"""
Compare groups from an HTML table with existing groups in data.yaml.
Identifies groups that are missing from data.yaml.
"""

import re
import yaml
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse


class TableHTMLParser(HTMLParser):
    """Parse HTML table to extract group data."""
    
    def __init__(self):
        super().__init__()
        self.groups = []
        self.current_row = []
        self.current_cell = ""
        self.current_links = []
        self.in_td = False
        self.in_th = False
        self.in_a = False
        self.current_href = ""
        
    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.in_td = True
            self.current_cell = ""
            self.current_links = []
        elif tag == "th":
            self.in_th = True
        elif tag == "a" and self.in_td:
            self.in_a = True
            for attr, value in attrs:
                if attr == "href":
                    self.current_href = value
                    
    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False
            self.current_row.append({
                "text": self.current_cell.strip(),
                "links": self.current_links
            })
        elif tag == "th":
            self.in_th = False
        elif tag == "tr":
            if len(self.current_row) >= 4:
                self.groups.append(self.current_row)
            self.current_row = []
        elif tag == "a" and self.in_a:
            self.in_a = False
            if self.current_href:
                self.current_links.append(self.current_href)
            self.current_href = ""
            
    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data


def extract_urls_from_html(html_content: str) -> list[dict]:
    """Extract group information from HTML table."""
    parser = TableHTMLParser()
    parser.feed(html_content)
    
    groups = []
    for row in parser.groups:
        if len(row) >= 4:
            name = row[0]["text"]
            country = row[1]["text"]
            city = row[2]["text"]
            links = row[3]["links"]
            
            # Skip header-like rows (country headers have empty other fields)
            if not country and not city and not links:
                continue
            
            for link in links:
                groups.append({
                    "name": name,
                    "country": country,
                    "city": city,
                    "url": link
                })
    
    return groups


def load_yaml_urls(yaml_path: Path) -> set[str]:
    """Load all URLs from the data.yaml file."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    urls = set()
    for group in data.get("groups", []):
        url = group.get("url", "")
        if url:
            urls.add(url)
    
    return urls


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    url = url.strip()
    # Remove trailing slashes
    url = url.rstrip("/")
    return url


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    yaml_path = project_root / "data.yaml"
    
    # HTML content from the table (read from stdin or file)
    html_content = """<table><thead><tr><th><strong>WhatsApp Group Name</strong></th><th><strong>Country</strong></th><th><strong>City</strong></th><th><strong>Link</strong></th></tr></thead><tbody><tr><td><strong>ARGENTINA</strong></td><td></td><td></td><td></td></tr><tr><td>PATAGONIA (Bariloche and more)</td><td>Argentina</td><td>Bariloche</td><td><a href="https://chat.whatsapp.com/Cr4CdA6dScu7rblxsQFBHN" rel="nofollow">Join</a></td></tr><tr><td>Argentina Travellers ✈️😎</td><td>Argentina</td><td>Buenos Aires</td><td><a href="https://linktr.ee/argentinatravellers" rel="nofollow">Linktree</a></td></tr><tr><td>BA Digital Nomads III</td><td>Argentina</td><td>Buenos Aires</td><td><a href="https://linktr.ee/BADigitalNomads" rel="nofollow">Linktree</a></td></tr><tr><td>BA nomads II</td><td>Argentina</td><td>Buenos Aires</td><td><a href="https://chat.whatsapp.com/EEmxp7WXwU4DVlkDtF7OKP" rel="nofollow">Join</a></td></tr><tr><td>Trips/Weekends outside BA (Buenos Aires)</td><td>Argentina</td><td>Buenos Aires</td><td><a href="https://chat.whatsapp.com/ELqsQOXd5hV15ViByMuPit" rel="nofollow">Join</a></td></tr><tr><td><strong>AUSTRALIA</strong></td><td></td><td></td><td></td></tr><tr><td>Australia Backpackers</td><td>Australia</td><td>global</td><td><a href="https://chat.whatsapp.com/C5WEjPekNCyAJJhvsmumw7" rel="nofollow">Join</a></td></tr><tr><td><strong>BRAZIL</strong></td><td></td><td></td><td></td></tr><tr><td>chat selina floripa</td><td>Brazil</td><td>Florianópolis</td><td><a href="https://chat.whatsapp.com/G1bznwlz49M6MUcxaEZjx3" rel="nofollow">Join</a></td></tr><tr><td>Hike aholics Rio Janerio</td><td>Brazil</td><td>Rio de Janeiro</td><td><a href="https://chat.whatsapp.com/IpBlhKpfaEf00d85stp4wK" rel="nofollow">Join</a></td></tr><tr><td>Rio Digital Nomads</td><td>Brazil</td><td>Rio de Janeiro</td><td><a href="https://chat.whatsapp.com/B60QYOkl0z7BUYQQScKEeS" rel="nofollow">Join</a></td></tr><tr><td>Rio Meet Up Group 3.0</td><td>Brazil</td><td>Rio de Janeiro</td><td><a href="https://chat.whatsapp.com/DtA92BgHvco0Zyo0uFGm5t" rel="nofollow">Join</a></td></tr><tr><td>•M&amp;E• International meetups &amp; Events SP</td><td>Brazil</td><td>São Paulo</td><td><a href="https://chat.whatsapp.com/EJEUalSjTuQ2CaAYl0dUdv" rel="nofollow">Join</a></td></tr><tr><td><strong>BULGARIA</strong></td><td></td><td></td><td></td></tr><tr><td>Bansko Social</td><td>Bulgaria</td><td>Bansko</td><td><a href="https://chat.whatsapp.com/KN0kH6ybNY09gThnQs6p4c" rel="nofollow">Join</a></td></tr><tr><td>Fall Into Bansko 2023</td><td>Bulgaria</td><td>Bansko</td><td><a href="https://chat.whatsapp.com/EvG9pnALGxy6Boglyz99tT" rel="nofollow">Join</a></td></tr><tr><td><strong>CAMBODIA</strong></td><td></td><td></td><td></td></tr><tr><td>Cambodia Backpackers</td><td>Cambodia</td><td>Phnom Penh</td><td><a href="https://chat.whatsapp.com/DIc4msPAqloHVZ70JQ1YlD" rel="nofollow">Join</a></td></tr><tr><td>Cambodia seasia travel</td><td>Cambodia</td><td>Siem Reap</td><td><a href="https://chat.whatsapp.com/LOTXBFQluoW2oLOTRoulTR" rel="nofollow">Join</a></td></tr><tr><td><strong>COLOMBIA</strong></td><td></td><td></td><td></td></tr><tr><td>Bogota Expats Meetups 🥳🥳🥳</td><td>Colombia</td><td>Bogotá</td><td><a href="https://chat.whatsapp.com/K4ZmeuXfUQcJ46E4DKa6z1" rel="nofollow">Join</a></td></tr><tr><td>Cali female power</td><td>Colombia</td><td>Cali</td><td><a href="https://chat.whatsapp.com/CPoejtN2WevCyztW5Ts7MP" rel="nofollow">Join</a></td></tr><tr><td>Cartagena Nomads☀️🙌🏻</td><td>Colombia</td><td>Cartagena</td><td><a href="https://chat.whatsapp.com/JfByrLNqNkRCma0CX7qF4A" rel="nofollow">Join</a></td></tr><tr><td>♦️Medellin Digital Nomads CLUB</td><td>Colombia</td><td>Medellín</td><td><a href="https://chat.whatsapp.com/E96ssGpGTVH3LKnr84XYWm" rel="nofollow">Join</a></td></tr><tr><td>Medellín Coworking Crew</td><td>Colombia</td><td>Medellín</td><td><a href="https://chat.whatsapp.com/FsyklhO2jDw5hsTBFpedcN" rel="nofollow">Join</a></td></tr><tr><td><strong>CYPRUS</strong></td><td></td><td></td><td></td></tr><tr><td>Cyprus Nomading &amp; Travel</td><td>Cyprus</td><td>Limassol</td><td><a href="https://chat.whatsapp.com/JCxnP9A1eggFw8UGdlDv9s" rel="nofollow">Join</a></td></tr><tr><td>Limassol Chill Group ☀🏄🏼&zwj;♂👨&zwj;💻🍜</td><td>Cyprus</td><td>Limassol</td><td><a href="https://t.me/+ZIYM7jC0vGFmZDM0" rel="nofollow">Telegram</a></td></tr><tr><td>Nicosia Chill Group ☀🎊👨&zwj;💻🍜🍸</td><td>Cyprus</td><td>Nicosia</td><td><a href="https://chat.whatsapp.com/DpwkDERUR109njI7SsLQXJ" rel="nofollow">Join</a></td></tr><tr><td>Arriving in Paphos 🌍</td><td>Cyprus</td><td>Paphos</td><td><a href="https://chat.whatsapp.com/Kkz8BzpcRJiJz3LihpexSm" rel="nofollow">Join</a></td></tr><tr><td>Paphos Boardgame Meeples - Community</td><td>Cyprus</td><td>Paphos</td><td><a href="https://chat.whatsapp.com/DqMMPD7RaCYAGKn6Z18JyA" rel="nofollow">Join</a></td></tr><tr><td>PAPHOS WEEKLY ENTREPRENEURIAL &amp; DIGITAL NOMAD MEETUP</td><td>Cyprus</td><td>Paphos</td><td><a href="https://chat.whatsapp.com/LJlipoDKeFO5hWc4F6MNJk" rel="nofollow">Join</a></td></tr><tr><td><strong>EGYPT</strong></td><td></td><td></td><td></td></tr><tr><td>Dahab Digital Nomads</td><td>Egypt</td><td>Dahab</td><td><a href="https://chat.whatsapp.com/DD6GNpu2i4bF8Z0HqozfB4" rel="nofollow">Join</a></td></tr><tr><td><strong>GEORGIA</strong></td><td></td><td></td><td></td></tr><tr><td>🇬🇪 Social Meet-up 2 💚</td><td>Georgia</td><td>Tbilisi</td><td><a href="https://chat.whatsapp.com/DJC3ns2jnV4I8EbIK69eyg" rel="nofollow">Join</a></td></tr><tr><td><strong>GERMANY</strong></td><td></td><td></td><td></td></tr><tr><td>Advise and help in Berlin</td><td>Germany</td><td>Berlin</td><td><a href="https://chat.whatsapp.com/CMc9HgS4nPB7E1lhfSEDZf" rel="nofollow">Join</a></td></tr><tr><td>Germany</td><td>Germany</td><td>global</td><td><a href="https://chat.whatsapp.com/CwowkEKHjZsC8y0ZvZssn4" rel="nofollow">Join</a></td></tr><tr><td><strong>GREECE</strong></td><td></td><td></td><td></td></tr><tr><td>Athens Digital Nomads Meetup- Main - Community</td><td>Greece</td><td>Athens</td><td><a href="https://chat.whatsapp.com/JfXVHnuoqmSIDC1WIlGgm6" rel="nofollow">Join</a></td></tr><tr><td>DN👩🏽&zwj;💻👨🏽&zwj;💻Remote workers Athens</td><td>Greece</td><td>Athens</td><td><a href="https://chat.whatsapp.com/KR6KpUsat9uK5kyR6ixxjQ" rel="nofollow">Join</a></td></tr><tr><td><strong>HONG KONG</strong></td><td></td><td></td><td></td></tr><tr><td>Hong Kong seasia travel</td><td>Hong Kong</td><td>Hong Kong</td><td><a href="https://chat.whatsapp.com/HAqapfiWHyd8k5CwgzSOKG" rel="nofollow">Join</a></td></tr><tr><td><strong>HUNGARY</strong></td><td></td><td></td><td></td></tr><tr><td>Budapest Expats MeetUp 🍻</td><td>Hungary</td><td>Budapest</td><td><a href="https://chat.whatsapp.com/F6bEFbCcWIDGZFpjXea0ae" rel="nofollow">Join</a></td></tr><tr><td><strong>INDIA</strong></td><td></td><td></td><td></td></tr><tr><td>India seasia travel</td><td>India</td><td>Delhi</td><td><a href="https://chat.whatsapp.com/FPDSC9QB2Tv5HnVDIieooh" rel="nofollow">Join</a></td></tr><tr><td>nOmAdS in DELHI NCR</td><td>India</td><td>Delhi</td><td><a href="https://chat.whatsapp.com/HJbsCYK4Ash6j8gH692CK6" rel="nofollow">Join</a></td></tr><tr><td>India backpacker</td><td>India</td><td>Jaipur</td><td><a href="https://chat.whatsapp.com/H8cXuNXuZdRDIW5C0EsZa6" rel="nofollow">Join</a></td></tr><tr><td><strong>INDONESIA</strong></td><td></td><td></td><td></td></tr><tr><td>Bali Digital Nomads 👨&zwj;💻👩&zwj;💻</td><td>Indonesia</td><td>Bali</td><td><a href="https://chat.whatsapp.com/Di0b8sniyNb8qvWCBp37UU" rel="nofollow">Join</a></td></tr><tr><td>Bali, Indonesia seasia</td><td>Indonesia</td><td>Bali</td><td><a href="https://chat.whatsapp.com/GC1xJYkHFuNJE2Qk5JZHd4" rel="nofollow">Join</a></td></tr><tr><td>Bali Backpackers</td><td>Indonesia</td><td>Bali</td><td><a href="https://chat.whatsapp.com/HK6K3FWGr7RF5TkMobkHvR" rel="nofollow">Join</a></td></tr><tr><td>Kalimantan, Indonesia seasia</td><td>Indonesia</td><td>Balikpapan</td><td><a href="https://chat.whatsapp.com/GT8FC2VeY54FUDBGySeCc7" rel="nofollow">Join</a></td></tr><tr><td>Indonesia seasia travel</td><td>Indonesia</td><td>Jakarta</td><td><a href="https://chat.whatsapp.com/DW3jmtkVo0AHXlu0Qxu0SM" rel="nofollow">Join</a></td></tr><tr><td>Indonesia</td><td>Indonesia</td><td>Jakarta</td><td><a href="https://chat.whatsapp.com/L906asogJIhEnms6mJmE9T" rel="nofollow">Join</a></td></tr><tr><td>Papua, Indonesia seasia</td><td>Indonesia</td><td>Jayapura</td><td><a href="https://chat.whatsapp.com/F2QJFq90k4vKpalxmabClr" rel="nofollow">Join</a></td></tr><tr><td>East Nusa Tenggara, Indonesia seasia</td><td>Indonesia</td><td>Kupang</td><td><a href="https://chat.whatsapp.com/L5pRHP0LEoYGTFJFFDRcDK" rel="nofollow">Join</a></td></tr><tr><td>Lombok-Gili Islands, Indonesia seasia</td><td>Indonesia</td><td>Lombok-Gili Islands</td><td><a href="https://chat.whatsapp.com/CIV9KSvlXh8JNnqzwO9xRB" rel="nofollow">Join</a></td></tr><tr><td>Sulawesi, Indonesia seasia</td><td>Indonesia</td><td>Makassar</td><td><a href="https://chat.whatsapp.com/JDc9YtZMn3J3oaCxPVkWAl" rel="nofollow">Join</a></td></tr><tr><td>Indonesia Backpackers</td><td>Indonesia</td><td>Medan</td><td><a href="https://chat.whatsapp.com/LxZ8TPHYsUz0XzWNeIE18I" rel="nofollow">Join</a></td></tr><tr><td>Sumatra, Indonesia seasia</td><td>Indonesia</td><td>Sumatra</td><td><a href="https://chat.whatsapp.com/CwqCBAVlrcjLJOg9wLl7gP" rel="nofollow">Join</a></td></tr><tr><td>Java, Indonesia seasia</td><td>Indonesia</td><td>Surabaya</td><td><a href="https://chat.whatsapp.com/LBFuNfOWiQYIQ9SnlbuLa1" rel="nofollow">Join</a></td></tr><tr><td>Indonesia backpacker</td><td>Indonesia</td><td>Surabaya</td><td><a href="https://chat.whatsapp.com/Jq1VChT8BkaB7YZAGyRt8x" rel="nofollow">Join</a></td></tr><tr><td><strong>ITALY</strong></td><td></td><td></td><td></td></tr><tr><td>Digital Nomads Napoli</td><td>Italy</td><td>Naples</td><td><a href="https://chat.whatsapp.com/K2ym3rviJ9vICPV4RhFnQN" rel="nofollow">Join</a></td></tr><tr><td><strong>JAPAN</strong></td><td></td><td></td><td></td></tr><tr><td>Japan seasia travel</td><td>Japan</td><td>Japan</td><td><a href="https://chat.whatsapp.com/BmVdqgqNaxPGGjuk3P0Car" rel="nofollow">Join</a></td></tr><tr><td>Japan Backpackers</td><td>Japan</td><td>Tokyo</td><td><a href="https://chat.whatsapp.com/JzLDJabg4T1HU4X8lu9ie5" rel="nofollow">Join</a></td></tr><tr><td><strong>KAZAKHSTAN</strong></td><td></td><td></td><td></td></tr><tr><td>Kazakhstan Travelers</td><td>Kazakhstan</td><td>Almaty</td><td><a href="https://chat.whatsapp.com/K0lKCCtY8unFyJbqJSrwqI" rel="nofollow">Join</a></td></tr><tr><td><strong>LAOS</strong></td><td></td><td></td><td></td></tr><tr><td>Laos Backpackers</td><td>Laos</td><td>global</td><td><a href="https://chat.whatsapp.com/DBd0Gu4EdkaDMDBx28mb4j" rel="nofollow">Join</a></td></tr><tr><td>Laos Backpackers</td><td>Laos</td><td>Luang Prabang</td><td><a href="https://chat.whatsapp.com/KcWJazkCRMK9T3lQhWRz1d" rel="nofollow">Join</a></td></tr><tr><td>Laos seasia travel</td><td>Laos</td><td>Vientiane</td><td><a href="https://chat.whatsapp.com/Ej0Kit7ukxGARezDU5eFBf" rel="nofollow">Join</a></td></tr><tr><td><strong>MALAYSIA</strong></td><td></td><td></td><td></td></tr><tr><td>Malaysia seasia travel</td><td>Malaysia</td><td>George Town</td><td><a href="https://chat.whatsapp.com/L7stedT6f70H86MbUBTpMR" rel="nofollow">Join</a></td></tr><tr><td>Malaysia Travelers</td><td>Malaysia</td><td>Kuala Lumpur</td><td><a href="https://chat.whatsapp.com/Jcxg9Z7hsDw4GO7PCZLmGx" rel="nofollow">Join</a></td></tr><tr><td>Borneo Travelers</td><td>Malaysia</td><td>Kota Kinabalu</td><td><a href="https://chat.whatsapp.com/Lt4YlYWEXpuKfjaM9wiKqR" rel="nofollow">Join</a></td></tr><tr><td><strong>MEXICO</strong></td><td></td><td></td><td></td></tr><tr><td>Cancun</td><td>Mexico</td><td>Cancun</td><td><a href="https://chat.whatsapp.com/J5Syyf18I4a0k9IaSYZua2" rel="nofollow">Join</a></td></tr><tr><td>Healtcare: Guadalajara Nayarit Puerto Vallarta</td><td>Mexico</td><td>Guadalajara</td><td><a href="https://chat.whatsapp.com/Dc1ByLJSAmi3f0uvRbYn5F" rel="nofollow">Join</a></td></tr><tr><td>Digital Nomads Mexico 🇲🇽🪅</td><td>Mexico</td><td>Mexico City</td><td><a href="https://chat.whatsapp.com/ELQfGtuKQiZIFp35iIPRWA" rel="nofollow">Join</a></td></tr><tr><td>Healtcare: Mexico City and Queretaro</td><td>Mexico</td><td>Mexico City</td><td><a href="https://chat.whatsapp.com/HLq3OJ8jj3C0EznnjpcEC7" rel="nofollow">Join</a></td></tr><tr><td>Reconnect: Ice Bath Crew (Mexico)</td><td>Mexico</td><td>Mexico City</td><td><a href="https://chat.whatsapp.com/KZDi9hxOvKcJXnyhfqIhTF" rel="nofollow">Join</a></td></tr><tr><td>Healtcare: Oaxaca City Puerto Escondido San Cristobal</td><td>Mexico</td><td>Oaxaca City</td><td><a href="https://chat.whatsapp.com/DMHYvzeMr7EA2pFkJZJbW8" rel="nofollow">Join</a></td></tr><tr><td>Oaxaca Expats &amp; Nomads</td><td>Mexico</td><td>Oaxaca City</td><td><a href="https://chat.whatsapp.com/LmU655cbiOB4bBCPryfhih" rel="nofollow">Join</a></td></tr><tr><td>Techies in Playa</td><td>Mexico</td><td>Playa del Carmen</td><td><a href="https://chat.whatsapp.com/C4cUoPdyqYXAwuCtjRtojB" rel="nofollow">Join</a></td></tr><tr><td>Playa Digital nomads</td><td>Mexico</td><td>Playa del Carmen</td><td><a href="https://chat.whatsapp.com/CPrbArhQWAX0nIQyG38OWJ" rel="nofollow">Join</a></td></tr><tr><td>Healtcare: Playa del Carmen Cozumel Cancun Tulum Merida</td><td>Mexico</td><td>Playa del Carmen</td><td><a href="https://chat.whatsapp.com/JYQQ7P4EOSsCU3qQHI5R7R" rel="nofollow">Join</a></td></tr><tr><td>Playa del Carmen parties</td><td>Mexico</td><td>Playa del Carmen</td><td><a href="https://chat.whatsapp.com/HQDcIx335bO6AoRb8xGlaj" rel="nofollow">Join</a></td></tr><tr><td>Playa Q&amp;As</td><td>Mexico</td><td>Playa del Carmen</td><td><a href="https://chat.whatsapp.com/KPMr3YkQst16OdbhTROFeW" rel="nofollow">Join</a></td></tr><tr><td>Tulum Digital Nomads - Community</td><td>Mexico</td><td>Tulum</td><td><a href="https://chat.whatsapp.com/C3QHkQzfK3W9Qew7D8dRvp" rel="nofollow">Join</a></td></tr><tr><td>Tulum Expat Events - Community</td><td>Mexico</td><td>Tulum</td><td><a href="https://chat.whatsapp.com/E0mJYGXA1XxKL0N99jDhqC" rel="nofollow">Join 1</a><br><a href="https://chat.whatsapp.com/BNcNKKPJhunK52aaJpAo5a" rel="nofollow">Join 2</a></td></tr><tr><td>Tulum Dinner Club🍴 - Community</td><td>Mexico</td><td>Tulum</td><td><a href="https://chat.whatsapp.com/I6qcb3JOo8yKeDXSP6VLIV" rel="nofollow">Join</a></td></tr><tr><td>PDC - DN - Group (Mexico)</td><td>Mexico</td><td>global</td><td><a href="https://chat.whatsapp.com/BjojZZrvPus5c6zqjbbcWE" rel="nofollow">Join</a></td></tr><tr><td><strong>MYANMAR</strong></td><td></td><td></td><td></td></tr><tr><td>Myanmar Backpacker</td><td>Myanmar</td><td>Yangon</td><td><a href="https://linktr.ee/backpackersasia" rel="nofollow">Linktree</a></td></tr><tr><td><strong>NEPAL</strong></td><td></td><td></td><td></td></tr><tr><td>Nepal Backpackers</td><td>Nepal</td><td>Kathmandu</td><td><a href="https://chat.whatsapp.com/KtKxzBDkHznHs0tkqUdGSf" rel="nofollow">Join</a></td></tr><tr><td><strong>NETHERLANDS</strong></td><td></td><td></td><td></td></tr><tr><td>Digital nomads NL 🇳🇱</td><td>Netherlands</td><td>Amsterdam</td><td><a href="https://chat.whatsapp.com/LuqFCn0I88p5FFxMB6jngh" rel="nofollow">Join</a></td></tr><tr><td><strong>NEW ZEALAND</strong></td><td></td><td></td><td></td></tr><tr><td>New Zealand Backpackers</td><td>New Zealand</td><td>Auckland</td><td><a href="https://chat.whatsapp.com/FRJXlrUU9X9Ix5Ht7COvUU" rel="nofollow">Join</a></td></tr><tr><td><strong>PHILIPPINES</strong></td><td></td><td></td><td></td></tr><tr><td>Philippine's backpackers</td><td>Philippines</td><td>Cebu City</td><td><a href="https://chat.whatsapp.com/JsXlqCCH05y9owjXxCz4R7" rel="nofollow">Join</a></td></tr><tr><td>The Philippines seasia travel</td><td>Philippines</td><td>Manila</td><td><a href="https://chat.whatsapp.com/FJBB4T4fVHfIyDCG0cAiaI" rel="nofollow">Join</a></td></tr><tr><td>Philippines</td><td>Philippines</td><td>Manila</td><td><a href="https://chat.whatsapp.com/JsXlqCCH05y9owjXxCz4R7g" rel="nofollow">Join</a></td></tr><tr><td><strong>PORTUGAL</strong></td><td></td><td></td><td></td></tr><tr><td>Lagos Remoters 💻☀️no ads</td><td>Portugal</td><td>Lagos</td><td><a href="https://chat.whatsapp.com/Faa5Hcwx59d8rP1oqPSjeo" rel="nofollow">Join</a></td></tr><tr><td><strong>SINGAPORE</strong></td><td></td><td></td><td></td></tr><tr><td>Singapore seasia travel</td><td>Singapore</td><td>Singapore</td><td><a href="https://chat.whatsapp.com/DNNI3OoATzuGACk85tvFP7" rel="nofollow">Join</a></td></tr><tr><td><strong>SOUTH KOREA</strong></td><td></td><td></td><td></td></tr><tr><td>South Korea Backpackers</td><td>South Korea</td><td>Seoul</td><td><a href="https://chat.whatsapp.com/FtnHvR3lkrF5XCgCaGvN7b" rel="nofollow">Join</a></td></tr><tr><td>South Korea seasia travel</td><td>South Korea</td><td>Seoul</td><td><a href="https://chat.whatsapp.com/JM81kFj5abN8RKYlcSKuop" rel="nofollow">Join</a></td></tr><tr><td><strong>SPAIN</strong></td><td></td><td></td><td></td></tr><tr><td>Expat meetings BCN1 - Community</td><td>Spain</td><td>Barcelona</td><td><a href="https://www.expatmeetings.com/" rel="nofollow">Visit</a></td></tr><tr><td>Expat meetings BCN3 - Community</td><td>Spain</td><td>Barcelona</td><td><a href="https://www.expatmeetings.com/" rel="nofollow">Visit</a></td></tr><tr><td>BCN Meetup</td><td>Spain</td><td>Barcelona</td><td><a href="https://abnb.me/h9DZdc3lICb" rel="nofollow">Join</a></td></tr><tr><td>BCN DNs (join new group)</td><td>Spain</td><td>Barcelona</td><td><a href="https://chat.whatsapp.com/LkAtbcEMfjCLijR4KwfWUZ" rel="nofollow">Join</a></td></tr><tr><td>The Cool Kids of Barcelona</td><td>Spain</td><td>Barcelona</td><td><a href="https://chat.whatsapp.com/KEU2Yr4WrQBHyADLsnhL6E" rel="nofollow">Join</a></td></tr><tr><td>MALLORCA Digital Nomads💻🏝</td><td>Spain</td><td>Mallorca</td><td><a href="https://chat.whatsapp.com/EiDX7hKMnL50U5HvhNJRAa" rel="nofollow">Join</a></td></tr><tr><td>DIGITAL NOMADS TENERIFE SOUTH - Community</td><td>Spain</td><td>Tenerife</td><td><a href="https://chat.whatsapp.com/J64owcOVGzAIzM6diWhwuE" rel="nofollow">Join</a></td></tr><tr><td>TENERIFE Digital Nomads💻🏝</td><td>Spain</td><td>Tenerife</td><td><a href="https://t.me/+5n-VTOLAJXs2M2Q0" rel="nofollow">Telegram</a></td></tr><tr><td><strong>SRI LANKA</strong></td><td></td><td></td><td></td></tr><tr><td>Sri Lanka Travelers</td><td>Sri Lanka</td><td>global</td><td><a href="https://chat.whatsapp.com/CLMRaxKrSQCAOVmfHQ6ORD" rel="nofollow">Join</a></td></tr><tr><td><strong>THAILAND</strong></td><td></td><td></td><td></td></tr><tr><td>Bangkok Backpackers</td><td>Thailand</td><td>Bangkok</td><td><a href="https://media-fra3-1.cdn.whatsapp.net/v/t61.24694-24/263695086_920450918863595_4084005594260757978_n.jpg?_nc_sid=e6ed6c&amp;ccb=11-4&amp;oh=..." rel="nofollow">Media Link</a></td></tr><tr><td>Thailand seasia travel</td><td>Thailand</td><td>Bangkok</td><td><a href="https://chat.whatsapp.com/DzrxQT985r3IaFcizvFota" rel="nofollow">Join</a></td></tr><tr><td>Thailand group Backpackers</td><td>Thailand</td><td>Chiang Mai</td><td><a href="https://chat.whatsapp.com/Gh8GfRvCbBFJx8JYcv7JPv" rel="nofollow">Join</a></td></tr><tr><td>Digital Nomads Chiang Mai - Community</td><td>Thailand</td><td>Chiang Mai</td><td><a href="https://chat.whatsapp.com/Jj6aRzWsMag6yHuMHKO5YC" rel="nofollow">Join</a></td></tr><tr><td>Thailand backpacker</td><td>Thailand</td><td>Phuket</td><td><a href="https://chat.whatsapp.com/HfPEMIGc3nFEXpGoZhiFvC" rel="nofollow">Join</a></td></tr><tr><td><strong>TURKEY</strong></td><td></td><td></td><td></td></tr><tr><td>Istanbul Digital Nomads</td><td>Turkey</td><td>Istanbul</td><td><a href="https://chat.whatsapp.com/KseDnKcjHw98wfPl3etefe" rel="nofollow">Join</a></td></tr><tr><td><strong>VIETNAM</strong></td><td></td><td></td><td></td></tr><tr><td>Vietnam backpackers</td><td>Vietnam</td><td>Da Nang</td><td><a href="https://chat.whatsapp.com/LFv26KzvEMnHb8giScflN7" rel="nofollow">Join</a></td></tr><tr><td>Vietnam seasia travel</td><td>Vietnam</td><td>Hanoi</td><td><a href="https://chat.whatsapp.com/Gac7rmdFjTJAM2lRDmVmKt" rel="nofollow">Join</a></td></tr><tr><td>Vietnam Backpackers</td><td>Vietnam</td><td>Ho Chi Minh City</td><td><a href="https://chat.whatsapp.com/JTDf6YGiBXRCPj0uBMYL7h" rel="nofollow">Join</a></td></tr><tr><td><strong>WORLDWIDE</strong></td><td></td><td></td><td></td></tr><tr><td>🎭 Nomad Artists 🎸🎬</td><td>Worldwide</td><td>Worldwide</td><td><a href="https://chat.whatsapp.com/BBtTZGHSHjHIskzR9P0aZF" rel="nofollow">Join</a></td></tr><tr><td>Backpackers in general</td><td>Worldwide</td><td>Global</td><td><a href="https://linktr.ee/backpackerss" rel="nofollow">Linktree</a></td></tr><tr><td>Justin link to nomad groups</td><td>Worldwide</td><td>Global</td><td><a href="https://justin-travel.com/travel-whatsapp-groups/" rel="nofollow">Visit</a></td></tr></tbody></table>"""
    
    # Extract groups from HTML
    html_groups = extract_urls_from_html(html_content)
    print(f"Found {len(html_groups)} groups in HTML table")
    
    # Load existing URLs from YAML
    yaml_urls = load_yaml_urls(yaml_path)
    print(f"Found {len(yaml_urls)} URLs in data.yaml")
    
    # Find missing groups
    missing_groups = []
    for group in html_groups:
        normalized_url = normalize_url(group["url"])
        # Check if URL exists in yaml (check both normalized and original)
        if normalized_url not in yaml_urls and group["url"] not in yaml_urls:
            missing_groups.append(group)
    
    # Print results
    print(f"\n{'='*80}")
    print(f"MISSING GROUPS: {len(missing_groups)} groups not in data.yaml")
    print(f"{'='*80}\n")
    
    # Group by country for better readability
    by_country = {}
    for group in missing_groups:
        country = group["country"] or "Unknown"
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(group)
    
    for country in sorted(by_country.keys()):
        print(f"\n## {country}")
        for group in by_country[country]:
            print(f"  - {group['name']}")
            print(f"    City: {group['city']}")
            print(f"    URL: {group['url']}")


if __name__ == "__main__":
    main()

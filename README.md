# nomadgroups.wiki

Welcome to the Digital Nomad Community Directory! This project aims to create a comprehensive list of online communities and groups specifically catered to digital nomads. Whether you're a seasoned nomad or just starting your remote work journey, this directory will help you connect with like-minded individuals, find support, and discover exciting opportunities around the world.

## The list

👉🏻 Click [HERE](directory.md) to open the list

## 🗂️ How the Directory Works

This project uses three main files:

1. **`data.yaml`** - The **source of truth** where all data is stored and maintained
2. **`schema.json`** - Defines the structure and validation rules for the directory data
3. **`directory.md`** - The human-readable file that's automatically generated from the YAML data

> **Important:** Always make changes to `data.yaml`, NOT the markdown file. The markdown file is automatically generated and any direct changes will be overwritten.

## 🤝 How to Contribute

We welcome and appreciate all contributions to this directory! Here's how you can add new groups:

### Adding a New Group

1. Navigate to [data.yaml](data.yaml)
2. Click the "Edit" (pencil) button
3. Add your group at the end of the list following this example:

   ```yaml
   - name: "Chiang Mai Digital Nomads"  # Always use quotes for strings
     platform: "whatsapp"  # Supported: whatsapp, telegram, discord, linktree, facebook, slack
     url: "https://chat.whatsapp.com/example"
     locations:
       - continent: "Asia"  # Must be one of: Africa, Antarctica, Asia, Europe, North America, South America, Central America, Oceania
         country_id: "TH"  # ISO 3166-1 alpha-2 country code
         city: "Chiang Mai"  # Optional
         region: "Northern Thailand"  # Optional
     language_id: "en"  # Optional: ISO 639-1 language code
     commercial: false  # No quotes for boolean values
     tags:  # Optional: keywords to categorize the group
       - "coworking"
       - "meetups"
       - "housing"
   ```

4. For multiple locations:

   ```yaml
   - name: "Southeast Asia Nomads"
     platform: "telegram"
     url: "https://t.me/example"
     locations:
       - continent: "Asia"
         country_id: "TH"
       - continent: "Asia"
         country_id: "VN"
       - continent: "Asia"
         country_id: "ID"
   ```

5. Click "Propose changes"
6. Submit a pull request

> **Note:** All contributions are automatically validated against [schema.json](schema.json). Your PR will only be merged if it passes validation.

## 🔧 Technical Information

### Automated Workflows

This repository uses GitHub Actions for automation:

1. **Validation Workflow**
   - Runs on every pull request
   - Validates data against schema.json
   - Ensures data integrity

2. **Markdown Generation**
   - Triggers on data.yaml updates
   - Automatically regenerates directory.md
   - Maintains consistency

### Schema Details

The `schema.json` file enforces:
- Valid platform values
- Correct continent names
- Proper URL formats
- Required and optional fields
- Data type validation

For complete validation requirements, refer to [schema.json](schema.json).

## 📜 License

This project is licensed under the [GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007](LICENSE). By contributing, you agree to release your contributions under this license.

---

Let's build the most comprehensive digital nomad community directory together! Your contributions help fellow nomads connect and thrive in their remote work adventures. 🌍✨
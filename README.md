# nomadgroups.wiki

Welcome to the Digital Nomad Community Directory! This project aims to create a comprehensive list of online communities and groups specifically catered to digital nomads. Whether you're a seasoned nomad or just starting your remote work journey, this directory will help you connect with like-minded individuals, find support, and discover exciting opportunities around the world.

## The list

👉🏻 Click [HERE](directory.md) to open the list

## How the Directory Works

This project uses three main files:

1. **data.yaml** - This is the **source of truth** where all data is stored and maintained
2. **schema.json** - This defines the structure and validation rules for the directory data
3. **directory.md** - This is the human-readable file that's automatically generated from the YAML data

When a change is made to data.yaml, our GitHub workflow automatically validates it against the schema and then regenerates the markdown file.

> **Important:** Always make changes to the data.yaml file, NOT the markdown file. The markdown file is automatically generated and any direct changes to it will be overwritten.

## How to Contribute

Contributions to this directory are highly encouraged and greatly appreciated. If you come across any digital nomad groups that are not listed here, please add them by following these steps:

### Option 1: Using the Issue Form (Easiest)

1. Go to the "Issues" tab in this repository
2. Click on "New Issue"
3. Select the "Add New Digital Nomad Group" template
4. Fill out the form with the group details
5. Submit the issue

Our automated workflow will process your submission and create a pull request.

NOTE: This won't let you create a group for multiple locations. If you need to add a group for multiple locations, please use Option 2.

### Option 2: Direct YAML Editing

1. Navigate to the [data.yaml](data.yaml) file in this repository
2. Click on the "Edit" (pencil) button to start editing the file
3. Add the details of the group following the YAML schema. Here's a comprehensive example:

   ```yaml
   - name: "Chiang Mai Digital Nomads"
     platform: "whatsapp"  # Supported: whatsapp, telegram, discord, linktree, facebook, slack, etc.
     url: "https://chat.whatsapp.com/example"
     locations:
       - continent: "Asia"  # Must be one of: Africa, Antarctica, Asia, Europe, North America, South America, Central America, Oceania
         country_id: "TH"  # ISO 3166-1 alpha-2 country code
         city: "Chiang Mai"  # Optional: City name
         region: "Northern Thailand"  # Optional: Region within the country
     language_id: "en"  # Optional: ISO 639-1 language code if not English
     commercial: false  # Optional: true if this is a paid/commercial group
     tags:  # Optional: keywords to categorize the group
       - "coworking"
       - "meetups"
       - "housing"
   ```

   You can add multiple locations for groups that span different regions:

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

4. Make sure to place your entry in the appropriate section, maintaining alphabetical order
5. Once you have added the group, provide a meaningful commit message
6. Click on the "Propose changes" button
7. Finally, submit a pull request (PR) for your changes to be reviewed and merged

> **Note:** All contributions are automatically validated against the [schema.json](schema.json) file, which defines the required structure and allowed values. Your PR will only be merged if it passes this validation.

Please note that contributions should follow the existing format and be relevant to the digital nomad community. Let's work together to build a vibrant and inclusive resource for all digital nomads!

## Technical Information

### Directory Structure

The directory is organized first by continents, then by countries, all in alphabetical order.
This allows users to easily find communities in specific locations. Each country section contains a list of groups along with their descriptions and links.

### Automated Workflows

This repository uses several GitHub Actions workflows:

1. **Validation**: Every pull request is automatically validated against the schema.json
2. **Markdown Generation**: When data.yaml is updated, the directory.md file is automatically regenerated
3. **Group Submission**: Issues created with the "New Group" label are processed automatically

### Schema Details

The schema.json file defines the structure and requirements for the directory data. Key requirements include:

- Valid platform values (whatsapp, telegram, discord, etc.)
- Valid continent names
- URL format validation
- Required and optional fields

Refer to the [schema.json](schema.json) file for complete details on data validation requirements.

## License

This project is licensed under the [GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007](LICENSE), ensuring your freedom to use, modify, and distribute the software, while keeping it free and open source. By contributing to this directory, you agree to release your contributions under this license.

Let's create a comprehensive directory of digital nomad communities together! Start contributing today and help fellow nomads connect and thrive in their remote work adventures!
# Digital Nomads Groups Directory

Welcome to the **Digital Nomad Community Directory** — an open dataset of online communities for digital nomads, expats, and remote workers.

The goal of this project is simple: make it easy to **find the local WhatsApp, Telegram, Discord, and other groups** where people share real information about cities around the world.

These groups are often the **best source of local knowledge** — from housing and coworking spaces to meetups and practical advice.

---

# 🌐 Browse the Directory

👉🏻 Click **[HERE](directory.md)** to view the full list for free.

This repository contains the **raw dataset** of groups.

# ⭐️ Directory with Superpowers

If you'd rather **search, filter, and explore the groups easily**, you can use the website built on top of this dataset:

👉 **https://nomadgroups.wiki**

The website adds:

- 🤖 **Telegram bot search**
- 🔎 **Search by city, country, or group name**
- 🗺️ **3D interactive world map**
- 🎯 **Filters by platform** (WhatsApp, Telegram, Discord, Facebook, Slack, Linktree)
- ⭐ **Community ratings** to find active groups

Think of this repo as the **open database**, and the website as the **user-friendly interface**.

---

# 🗂️ How the Directory Works

This project uses three main files:

1. **`data.yaml`**  
   The **source of truth** where all group data is stored.

2. **`schema.json`**  
   Defines the structure and validation rules for the data.

3. **`directory.md`**  
   A human-readable directory automatically generated from the YAML data.

> ⚠️ Always edit **`data.yaml`**, not the markdown file.  
> `directory.md` is automatically generated and manual edits will be overwritten.

---

# 🤝 How to Contribute

We welcome contributions! You can add new groups in two ways.

## Method 1: Easy (Recommended)

Simply **[open a new issue](https://github.com/rignaneseleo/groups-for-nomads/issues/new?template=add_group.yml)** using the **Add a New Group** template.

Fill in the details and the group will be added to the dataset.

---

## Method 2: Advanced (Pull Request)

If you're comfortable with GitHub and YAML:

1. Open **[data.yaml](data.yaml)**
2. Click the **Edit (pencil)** button
3. Add your group at the end of the list following this example:

```yaml
- name: "Chiang Mai Digital Nomads"
  platform: "whatsapp"
  url: "https://chat.whatsapp.com/example"
  locations:
    - continent: "Asia"
      country_id: "TH"
      city: "Chiang Mai"
      region: "Northern Thailand"
  language_id: "en"
  commercial: false
  tags:
    - "coworking"
    - "meetups"
    - "housing"
````

### Multiple locations example

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

Then:

4. Click **Propose changes**
5. Submit a **Pull Request**

All contributions are automatically validated against **schema.json** before being merged.

---

# 🎁 Free access for contributors

The website **NomadGroups.wiki** is built on top of this open dataset.

If you contribute to this repository, you're welcome to **use the website for free**.

Just open an issue or submit a pull request, ping me at gn@leorigna.com and I'll send you lifetime access.

This helps improve the dataset while keeping the directory useful for everyone.

---

# 🔧 Technical Information

## Automated Workflows

This repository uses **GitHub Actions** to keep the dataset clean and up-to-date.

### Validation Workflow

Runs on every pull request.

* Validates data against `schema.json`
* Ensures formatting and data integrity

---

### Markdown Generation

Automatically generates the directory:

* Triggered when `data.yaml` changes
* Regenerates `directory.md`
* Keeps the list consistent

---

### Link Checker

Runs weekly to identify broken invitation links.

This helps keep the directory accurate.

---

### WhatsApp Invite Validation

Validates WhatsApp invite links using the **invite page structure**.

Features:

* Checks only new or modified links in pull requests
* Detects offline groups
* Adds **PR review comments** when invite names differ
* Supports manual cleanup via workflow dispatch

Manual mode (`workflow_dispatch`) with `apply_changes=true` can:

* Remove offline groups
* Rename groups to match the live invite name
* Upload updated `data.yaml` as an artifact

---

# 📊 Schema Details

The **`schema.json`** file enforces:

* Valid platform values
* Correct continent names
* Proper URL formats
* Required and optional fields
* Data type validation

See **[schema.json](schema.json)** for full validation rules.

---

# 🧭 Why this repository exists

This project started in **June 2023** as a simple open-source list of digital nomad groups.

Over time the dataset grew to hundreds of communities across many countries.

The goal is to keep a **public, community-maintained dataset** that anyone can:

* use
* analyze
* build tools on top of

Since browsing the raw list became difficult, I built **NomadGroups.wiki** as a tool on top of the dataset to make it easier to explore. The website also helps with outreach, allowing more people to discover and join these communities.

The **data remains open here on GitHub**.

---

# 📜 License

This project is licensed under the **GNU General Public License v3**.

By contributing, you agree to release your contributions under this license.

See **[LICENSE](LICENSE)** for details.

---

🌍 Let's build the **largest directory of digital nomad communities** together.

Your contributions help nomads connect, share knowledge, and make every new city easier to navigate.

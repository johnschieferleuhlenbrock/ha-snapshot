# HA Snapshot

**HA Snapshot** is a custom Home Assistant integration that:
- Exports a **condensed, minified JSON snapshot** of your HA environment (devices, entities, areas, integrations).  
- Offers a **Config Flow** for easy installation via the Integrations UI (no YAML edits required).  
- Provides a **sidebar panel** (using built-in authentication) to trigger snapshot exports in one click.

## Table of Contents

1. [Features](#features)  
2. [Prerequisites](#prerequisites)  
3. [Installation](#installation)  
   - [Via HACS](#via-hacs)  
   - [Manual](#manual)  
4. [Configuration & Setup](#configuration--setup)  
5. [Usage](#usage)  
   - [Service Call](#service-call)  
   - [Sidebar Panel](#sidebar-panel)  
6. [Data Export Details](#data-export-details)  
7. [FAQ / Troubleshooting](#faq--troubleshooting)  
8. [Support & Contributions](#support--contributions)  
9. [License](#license)

---

## Features

- **Minified JSON** output for smaller file size and quick download.  
- **Skips “back of house”** items (devices without a manufacturer or name).  
- **Uses built-in HA auth**: No separate tokens or sign-in required.  
- **Sidebar panel** for a convenient single-click export.  
- Optional **persistent notification** with a download link.

---

## Prerequisites

- **Home Assistant 2023.1.0** or newer (for best compatibility).  
- **HACS** (if you plan to install and update through HACS).

---

## Installation

### Via HACS

1. In Home Assistant, go to **HACS → Integrations**.  
2. Click the three-dot menu, then **Custom repositories**.  
3. Paste the GitHub URL for this repository and select **Integration** as the category.  
4. Once added, search for **“HA Snapshot”** in HACS and install it.  
5. **Restart** Home Assistant to load the new integration code.

> **Note:** If you see an error message such as `The version fb0de85 for this integration cannot be used with HACS`, this typically means HACS requires a **GitHub release tag** (e.g., `v0.1.0`) that follows [Semantic Versioning](https://semver.org/). Be sure to create a release in your repository with a valid semver tag so HACS can detect the correct version.

### Manual

1. Copy the `ha_snapshot` folder from `custom_components/` in this repo into your Home Assistant config folder:  
2. Place `ha_snapshot_panel.js` into `config/www/`.  
3. **Restart** Home Assistant.

---

## Configuration & Setup

1. In Home Assistant, go to **Settings → Devices & Services**.  
2. Click **+ Add Integration**.  
3. Search for **HA Snapshot** and select it.  
4. If prompted, follow the minimal Config Flow steps to finish setup.  
5. Home Assistant will create a config entry for “HA Snapshot” and automatically register a **sidebar panel** labeled “HA Snapshot.”

No need to manually add `panel_custom` YAML—this integration handles panel registration.

---

## Usage

### Service Call

- The integration provides a custom service: `ha_snapshot.export_data`.  
- To call it:  
1. Open **Developer Tools → Services** in Home Assistant.  
2. Select the service: **`ha_snapshot.export_data`**.  
3. (Optional) In **Service Data**, enter `{"notify": true}` to receive a persistent notification with the download link.  
4. Click **Call Service**.  

A file named `ha_snapshot_data.json` is written to your `/config/www/` folder, accessible at:  


### Sidebar Panel

1. In the left sidebar, click **HA Snapshot** (icon: `mdi:folder-download`).  
2. On the loaded page, click **“Export Snapshot”**.  
3. The integration runs the `export_data` service. If `notify: true` is passed in code, it shows a persistent notification with a download link.

---

## Data Export Details

- **Output file**: `/config/www/ha_snapshot_data.json` (minified JSON).  
- **Devices**: Contains name, manufacturer, model, firmware, area ID, and any associated entities.  
- **Entities**: Includes `entity_id`, name, device_class, unit_of_measurement, etc.  
- **Areas**: From HA’s **Area Registry** (ID, name, picture).  
- **Integrations**: Links config entry IDs to their devices and entities.  
- “Back of house” devices (missing manufacturer/name) are skipped to keep JSON lean.

---

## FAQ / Troubleshooting

1. **Exported file not found?**  
   - Make sure the `/config/www` folder exists (the integration will create it if needed). Then look under `/local/ha_snapshot_data.json`.
2. **Panel not appearing?**  
   - Confirm the integration was set up via the Config Flow. Check logs for errors during panel registration.
3. **Call to `async_entries_for_device` failing?**  
   - In older HA versions, a fallback approach is used. Check logs for warnings, but your data should still export.
4. **Removing the integration?**  
   - Go to **Settings → Devices & Services**, click **“HA Snapshot”**, then **Delete**. This removes the config entry and sidebar panel.

---

## Support & Contributions

- **Issues**: Please open a [GitHub Issue](../../issues) for bugs or feature requests.  
- **Pull Requests**: Contributions are welcome. Submit a PR to improve code, docs, or features.  
- **Community**: Share feedback, ideas, or questions in the Home Assistant community forums.

---

## License

This project is released under the [MIT License](LICENSE). Feel free to use, modify, or distribute under these terms.

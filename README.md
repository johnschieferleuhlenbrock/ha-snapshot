# HA Snapshot

A custom [Home Assistant](https://www.home-assistant.io/) integration that **exports** your devices, entities, and areas in a **hierarchical JSON** format (floors → areas → devices → entities), and can **import** changes back into Home Assistant (only entity names and labels).

## Features

- **Export**: Writes a JSON snapshot to `/config/www/<filename>.json`.
- **Import**: Reads a JSON file (previously exported or custom) and updates existing entities' names/labels.
- **No YAML**: Set up via the **HA UI** (Config Flow).
- **Sidebar Panel**: A built-in custom panel to trigger export/import in a friendly UI.
- **Built-in Auth**: Panel uses the user’s existing HA session (no tokens needed).
- **Optional**: [GitHub Action](.github/workflows/bump-version.yml) to automatically bump the `manifest.json` patch version.

## Installation

### HACS

1. In **HACS** → **Integrations** → **Custom repositories**:
   - Add your repo URL (e.g. `https://github.com/johnschieferleuhlenbrock/ha-snapshot`).
   - Category: **Integration**.
2. Search for “HA Snapshot” in HACS, **Install**, then **Restart** Home Assistant.
3. Go to **Settings → Devices & Services → + Add Integration** → **HA Snapshot**.

### Manual

1. Copy `ha_snapshot/` under `custom_components/`:
2. **Restart** Home Assistant.
3. **Settings → Devices & Services → + Add Integration** → “HA Snapshot.”

## Usage

1. **Config Flow**:
- Choose whether to skip nameless devices and/or include disabled entities.
2. **Sidebar Panel** (labeled “HA Snapshot”):
- **Export**: choose filename, toggle notification, click “Export.”
- **Import**: select a `.json` file, toggle notification, click “Import.”
- Only entity names and labels are updated. Unknown or new entities are skipped.
3. **Persistent Notifications**: If “Notify” is on, you’ll see a download link or import result.

## Versioning & Releases

- **Manifest**: Contains `"version": "0.5.0"`.
- **Tags**: Tag your repo with `v0.5.0` for HACS to detect the release.
- See [bump-version.yml](.github/workflows/bump-version.yml) for an example GitHub Action that automatically increments patch versions.

## License

[MIT License](LICENSE). Feel free to modify or distribute under these terms.

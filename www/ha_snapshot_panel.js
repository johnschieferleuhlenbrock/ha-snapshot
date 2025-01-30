// custom_components/ha_snapshot/panel/ha_snapshot_panel.js
/**
 * A custom element <ha-snapshot-panel> that runs inside Home Assistant's main frontend.
 * Because embed_iframe=false, we get this.hass automatically for calling services.
 *
 * This file is served at /ha_snapshot/panel/ha_snapshot_panel.js (registered by __init__.py).
 */

import { LitElement, html, css } from "lit";
import "@material/mwc-button";
import "@material/mwc-textfield";
import "@material/mwc-checkbox";
import "@material/mwc-formfield";

class HaSnapshotPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },   // Provided by the HA frontend
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },

      _statusMessage: { type: String },
      _filename: { type: String },
      _notifyExport: { type: Boolean },
      _notifyImport: { type: Boolean },
      _importFileContent: { type: String }
    };
  }

  constructor() {
    super();
    this._statusMessage = "";
    this._filename = "ha_snapshot_data.json";
    this._notifyExport = true;
    this._notifyImport = true;
    this._importFileContent = "";
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 16px;
      }
      h1 {
        font-size: 1.4em;
        margin-bottom: 8px;
      }
      .card {
        background: var(--card-background-color, #fff);
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
      }
      mwc-textfield {
        display: block;
        margin-bottom: 12px;
      }
      .actions {
        margin-top: 8px;
      }
      .status {
        margin-top: 8px;
        color: var(--secondary-text-color);
        min-height: 1.2em;
      }
      .import-limitations {
        background-color: var(--secondary-background-color);
        padding: 8px;
        border-radius: 4px;
        font-size: 0.9em;
      }
    `;
  }

  render() {
    return html`
      <h1>HA Snapshot</h1>
      <p>Export and Import your Home Assistant data.</p>

      <div class="card">
        <h2>Export</h2>
        <p>Exports to <code>/config/www/${this._filename}</code> and optionally notifies with a download link.</p>

        <mwc-textfield
          label="Output Filename"
          .value=${this._filename}
          @input=${(e) => this._filename = e.target.value}
        ></mwc-textfield>

        <mwc-formfield label="Notify on export?">
          <mwc-checkbox
            ?checked=${this._notifyExport}
            @change=${(e) => this._notifyExport = e.target.checked}
          ></mwc-checkbox>
        </mwc-formfield>

        <div class="actions">
          <mwc-button outlined label="Export Now" icon="file_download" @click=${this._exportNow}></mwc-button>
        </div>
        <div class="status">${this._statusMessage}</div>
      </div>

      <div class="card">
        <h2>Import</h2>
        <div class="import-limitations">
          <strong>Note:</strong> Only existing entities’ <em>names</em> and <em>labels</em> are updated.
          We do <em>not</em> create/remove entities, reassign devices, or change domains.
        </div>
        <input type="file" accept=".json" @change=${this._onFileSelected} style="margin-top: 8px;" />

        <mwc-formfield label="Notify on import?">
          <mwc-checkbox
            ?checked=${this._notifyImport}
            @change=${(e) => this._notifyImport = e.target.checked}
          ></mwc-checkbox>
        </mwc-formfield>

        <div class="actions">
          <mwc-button outlined label="Import Now" icon="file_upload" @click=${this._importNow}></mwc-button>
        </div>
        <div class="status">${this._statusMessage}</div>
      </div>
    `;
  }

  _exportNow() {
    if (!this.hass) {
      this._setStatus("Error: No hass object available.");
      return;
    }
    this._setStatus("Exporting snapshot...");
    this.hass.callService("ha_snapshot", "export_data", {
      filename: this._filename,
      notify: this._notifyExport
    })
    .then(() => {
      this._setStatus("Export request sent! Check notifications if 'notify' was selected.");
    })
    .catch((err) => {
      this._setStatus(`Export failed: ${err}`);
    });
  }

  _onFileSelected(e) {
    const file = e.target.files[0];
    if (!file) {
      this._importFileContent = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = (evt) => {
      this._importFileContent = evt.target.result;
    };
    reader.readAsText(file);
  }

  _importNow() {
    if (!this.hass) {
      this._setStatus("Error: No hass object available.");
      return;
    }
    if (!this._importFileContent) {
      this._setStatus("No file selected or file is empty.");
      return;
    }
    this._setStatus("Importing snapshot data...");
    this.hass.callService("ha_snapshot", "import_data", {
      import_json: this._importFileContent,
      notify: this._notifyImport
    })
    .then(() => {
      this._setStatus("Import request sent! Check notifications for results.");
    })
    .catch((err) => {
      this._setStatus(`Import failed: ${err}`);
    });
  }

  _setStatus(msg) {
    this._statusMessage = msg;
    console.info("[HA Snapshot Panel]", msg);
  }
}

customElements.define("ha-snapshot-panel", HaSnapshotPanel);

// custom_components/ha_snapshot/panel/ha_snapshot_panel.js

import { LitElement, html, css } from "lit";
import "@material/mwc-button";
import "@material/mwc-textfield";
import "@material/mwc-checkbox";
import "@material/mwc-formfield";

class HaSnapshotPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },  // Provided by Home Assistant
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },

      _statusMessage: { type: String },
      _selectedFile: { type: Object },
      _selectedFileContent: { type: String },
      _notifyExport: { type: Boolean },
      _notifyImport: { type: Boolean },
      _filename: { type: String }
    };
  }

  constructor() {
    super();
    this._statusMessage = "";
    this._selectedFile = null;
    this._selectedFileContent = "";
    this._notifyExport = true;
    this._notifyImport = true;
    this._filename = "ha_snapshot_data.json";
  }

  static get styles() {
    return css`
      :host {
        display: block;
        padding: 16px;
        color: var(--primary-text-color, #000);
      }
      h1 {
        font-size: 1.4em;
        margin: 0 0 8px 0;
      }
      h2 {
        margin-top: 24px;
        font-size: 1.2em;
      }
      .card {
        background: var(--card-background-color, #fff);
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: var(--ha-card-box-shadow, none);
      }
      .actions {
        margin-top: 16px;
      }
      .status {
        margin-top: 8px;
        color: var(--secondary-text-color);
      }
      mwc-textfield {
        display: block;
        margin-bottom: 8px;
      }
      mwc-checkbox {
        margin-right: 8px;
      }
      pre {
        white-space: pre-wrap;
        background: var(--secondary-background-color, #f5f5f5);
        padding: 8px;
        border-radius: 4px;
      }
    `;
  }

  render() {
    return html`
      <h1>HA Snapshot</h1>
      <p>Export and import Home Assistant data (devices, entities, areas, etc.)</p>

      <div class="card">
        <h2>Export</h2>
        <p>Export your current data to <code>/config/www/${this._filename}</code>. 
           The JSON follows a <strong>floors→areas→devices→entities</strong> hierarchy.</p>

        <mwc-textfield
          label="Output Filename"
          .value=${this._filename}
          @input=${(e) => this._filename = e.target.value}
        ></mwc-textfield>

        <mwc-formfield label="Notify with persistent notification?">
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
        <p>
          You can only update <strong>existing entities’ names and labels</strong>. 
          We do <strong>NOT</strong> create new entities, remove entities, or change domains/devices. 
          If a JSON entry references an unknown entity_id, it's skipped.
        </p>
        <p>
          Select a previously exported <code>.json</code> file below. Then click “Import” to apply allowed changes:
        </p>
        <input type="file" accept=".json" @change=${this._onFileSelected} />
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

  _setStatus(msg) {
    this._statusMessage = msg;
    // Also log to console for debugging
    console.info("[HA Snapshot Panel]", msg);
  }

  _exportNow() {
    if (!this.hass) {
      this._setStatus("Error: No hass object available.");
      return;
    }
    const data = {
      notify: this._notifyExport,
      filename: this._filename
    };
    this._setStatus("Exporting... Please wait.");
    this.hass.callService("ha_snapshot", "export_data", data)
      .then(() => {
        this._setStatus("Export triggered successfully!");
      })
      .catch((err) => {
        this._setStatus(`Export failed: ${err}`);
      });
  }

  _onFileSelected(e) {
    const file = e.target.files[0];
    if (!file) {
      this._selectedFileContent = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      this._selectedFileContent = ev.target.result;
    };
    reader.readAsText(file);
  }

  _importNow() {
    if (!this.hass) {
      this._setStatus("Error: No hass object available.");
      return;
    }
    if (!this._selectedFileContent) {
      this._setStatus("No file selected or file content is empty.");
      return;
    }
    this._setStatus("Importing... Please wait.");
    this.hass.callService("ha_snapshot", "import_data", {
      notify: this._notifyImport,
      import_json: this._selectedFileContent
    })
    .then(() => {
      this._setStatus("Import triggered successfully! Check notifications for results.");
    })
    .catch((err) => {
      this._setStatus(`Import failed: ${err}`);
    });
  }
}

customElements.define("ha-snapshot-panel", HaSnapshotPanel);

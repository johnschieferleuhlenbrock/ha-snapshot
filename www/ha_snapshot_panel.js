// ======================================
// www/ha_snapshot_panel.js
// ======================================

// We'll load LitElement (already in HA frontend) from the built-in environment:
import { LitElement, html, css } from "https://unpkg.com/lit-element/lit-element.js?module";

class HaSnapshotPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },  // Provided by Home Assistant
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        margin: 16px;
      }
      h1 {
        font-size: 1.5em;
        margin-bottom: 0.5em;
      }
      mwc-button {
        --mdc-theme-primary: var(--primary-color);
      }
    `;
  }

  render() {
    return html`
      <h1>HA Snapshot</h1>
      <div>
        <p>Click "Export Snapshot" to gather devices, entities, and areas into a JSON file. 
        If you choose notify=true, you'll get a persistent notification with the download link.</p>
        <mwc-button raised label="Export Snapshot" @click="${this._exportSnapshot}"></mwc-button>
      </div>
    `;
  }

  _exportSnapshot() {
    // The user is already logged in, so we can call the service directly.
    this.hass.callService("ha_snapshot", "export_data", {
      notify: true
    });
  }
}

// The custom element name must match the 'panel_custom name:' in configuration.yaml
customElements.define("ha-snapshot-panel", HaSnapshotPanel);

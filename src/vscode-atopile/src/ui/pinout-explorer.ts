/**
 * Pinout Explorer webview - Interactive IC pinout visualization.
 *
 * Reads the pinout.json build artifact and renders an interactive
 * chip diagram with color-coded pins, bus highlighting, and
 * alternate function display.
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import { getCurrentPinout, onPinoutChanged } from '../common/pinout';
import { BaseWebview } from './webview-base';

class PinoutExplorerWebview extends BaseWebview {
    constructor() {
        super({
            id: 'pinout_explorer',
            title: 'Pinout',
        });
    }

    protected getHtmlContent(_webview: vscode.Webview): string {
        const resource = getCurrentPinout();

        if (!resource || !resource.exists) {
            return this.getMissingResourceHtml('Pinout');
        }

        // Read and parse the JSON data
        let jsonData: string;
        try {
            jsonData = fs.readFileSync(resource.path, 'utf-8');
            const parsed = JSON.parse(jsonData);
            if (!parsed.components || parsed.components.length === 0) {
                return this.getMissingResourceHtml('Pinout (no ICs found — need components with 5+ pins)');
            }
        } catch {
            return this.getMissingResourceHtml('Pinout (invalid JSON)');
        }

        return this.getPinoutHtml(jsonData);
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const resource = getCurrentPinout();
        if (resource && fs.existsSync(resource.path)) {
            roots.push(vscode.Uri.file(require('path').dirname(resource.path)));
        }
        return roots;
    }

    /**
     * Generate the full self-contained HTML for the pinout viewer.
     * SVG-based chip diagram with physical pad positions, rotated labels,
     * CubeIDE-style colored pin pads, and a collapsible side panel.
     */
    private getPinoutHtml(jsonData: string): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pinout</title>
<style>
:root {
  --bg: var(--vscode-editor-background, #1e1e1e);
  --fg: var(--vscode-editor-foreground, #d4d4d4);
  --fg-muted: var(--vscode-descriptionForeground, #888);
  --border: var(--vscode-panel-border, #333);
  --accent: var(--vscode-textLink-foreground, #4fc1ff);
  --panel-bg: var(--vscode-sideBar-background, #252526);
  --hover: var(--vscode-list-hoverBackground, #2a2d2e);
  --select: var(--vscode-list-activeSelectionBackground, #094771);
  --font: var(--vscode-font-family, system-ui, sans-serif);
  --mono: var(--vscode-editor-font-family, 'Cascadia Code', monospace);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--fg);font-family:var(--font);font-size:13px}

/* Layout: side panel + main canvas */
.layout{display:flex;height:100%}
.side-panel{width:220px;background:var(--panel-bg);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;transition:width .2s}
.side-panel.collapsed{width:0;border-right:none}
.side-toggle{position:absolute;top:8px;left:8px;z-index:10;width:28px;height:28px;border:1px solid var(--border);border-radius:4px;background:var(--panel-bg);color:var(--fg-muted);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;line-height:1}
.side-toggle:hover{color:var(--fg);background:var(--hover)}
.side-panel.collapsed~.main-area .side-toggle{left:8px}
.side-panel:not(.collapsed)~.main-area .side-toggle{display:none}

/* Side panel sections */
.panel-header{padding:10px 12px 6px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--fg-muted);display:flex;align-items:center;justify-content:space-between}
.panel-header .close-btn{cursor:pointer;opacity:.5;font-size:14px}
.panel-header .close-btn:hover{opacity:1}
.panel-search{padding:0 8px 8px}
.panel-search input{width:100%;padding:4px 8px;border:1px solid var(--border);border-radius:3px;background:var(--bg);color:var(--fg);font-size:12px;font-family:var(--font);outline:none}
.panel-search input:focus{border-color:var(--accent)}
.comp-list{flex:1;overflow-y:auto;padding:0 4px}
.comp-item{display:flex;align-items:center;gap:6px;padding:5px 8px;border-radius:3px;cursor:pointer;font-size:12px;transition:background .1s}
.comp-item:hover{background:var(--hover)}
.comp-item.active{background:var(--select);color:#fff}
.comp-item .des{font-family:var(--mono);color:var(--accent);font-size:11px;min-width:24px}
.comp-item .name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.comp-item .cnt{font-size:10px;color:var(--fg-muted)}

/* Legend */
.legend-section{border-top:1px solid var(--border);padding:8px}
.legend-title{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--fg-muted);margin-bottom:6px}
.legend-grid{display:flex;flex-wrap:wrap;gap:2px}
.legend-chip{display:flex;align-items:center;gap:4px;padding:2px 6px;border-radius:2px;font-size:10px;color:var(--fg-muted);cursor:pointer}
.legend-chip:hover{background:var(--hover)}
.legend-chip.active{background:var(--select);color:#fff}
.legend-swatch{width:8px;height:8px;border-radius:2px;flex-shrink:0}

/* Main area */
.main-area{flex:1;position:relative;overflow:auto;display:flex;align-items:center;justify-content:center}
svg.chip-svg{max-width:100%;max-height:100%}

/* SVG styles */
.chip-body-rect{fill:#3c3c3c;stroke:#666;stroke-width:.3}
.chip-body-label{fill:var(--fg-muted);font-family:var(--mono);font-size:3px;text-anchor:middle;dominant-baseline:central;pointer-events:none}
.pin1-dot{fill:var(--fg-muted)}
.pad-rect{cursor:pointer;transition:opacity .15s}
.pad-rect:hover{filter:brightness(1.3)}
.pad-rect.faded{opacity:.2}
.pad-rect.highlighted{filter:brightness(1.4);stroke:#fff;stroke-width:.15}
.pin-label{font-family:var(--mono);font-size:1.8px;fill:var(--fg);pointer-events:none;dominant-baseline:central}
.pin-label.left{text-anchor:end}
.pin-label.right{text-anchor:start}
.pin-label.top,.pin-label.bottom{text-anchor:end}
.fn-label{font-family:var(--font);font-size:1.5px;fill:var(--fg-muted);pointer-events:none;dominant-baseline:central}
.fn-label.left{text-anchor:start}
.fn-label.right{text-anchor:end}
.fn-label.top,.fn-label.bottom{text-anchor:start}

/* Detail tooltip */
.detail-popup{position:fixed;z-index:100;background:var(--panel-bg);border:1px solid var(--border);border-radius:6px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.5);min-width:200px;max-width:320px;font-size:12px;pointer-events:auto}
.detail-popup .dp-header{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.detail-popup .dp-pin{font-family:var(--mono);font-weight:600;font-size:13px}
.detail-popup .dp-name{font-family:var(--mono);color:var(--accent)}
.detail-popup .dp-type{font-size:10px;padding:1px 5px;border-radius:2px;color:#fff}
.detail-popup .dp-section{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;color:var(--fg-muted);margin:6px 0 3px}
.detail-popup .dp-fn{display:flex;align-items:center;gap:5px;padding:2px 0;font-size:11px}
.detail-popup .dp-fn-dot{width:6px;height:6px;border-radius:2px;flex-shrink:0}
.detail-popup .dp-fn-name{font-family:var(--mono)}
.detail-popup .dp-fn-type{margin-left:auto;font-size:10px;color:var(--fg-muted)}
.dp-close{position:absolute;top:4px;right:8px;cursor:pointer;color:var(--fg-muted);font-size:14px}
.dp-close:hover{color:var(--fg)}
</style>
</head>
<body>
<div class="layout">
  <div class="side-panel" id="sidePanel">
    <div class="panel-header">
      <span>Components</span>
      <span class="close-btn" onclick="togglePanel()">&times;</span>
    </div>
    <div class="panel-search"><input id="searchInput" placeholder="Search..." oninput="handleSearch(this.value)"></div>
    <div class="comp-list" id="compList"></div>
    <div class="legend-section">
      <div class="legend-title">Bus Types</div>
      <div class="legend-grid" id="legendGrid"></div>
    </div>
  </div>
  <div class="main-area" id="mainArea">
    <div class="side-toggle" onclick="togglePanel()">&#9776;</div>
    <div id="svgContainer"></div>
  </div>
</div>
<div id="detailPopup" class="detail-popup" style="display:none"></div>

<script>
const DATA = ${jsonData};
const BUS_COLORS = {
  Power:'#e06c75',I2C:'#61afef',SPI:'#c678dd',UART:'#e5c07b',
  I2S:'#56b6c2',USB:'#98c379',JTAG:'#d19a66',Crystal:'#abb2bf',
  Analog:'#be5046',GPIO:'#5c6370',Control:'#d19a66',Signal:'#4b5263'
};
const TYPE_COLORS = {power:'#e06c75',ground:'#555',signal:'#888',nc:'#3e4451'};

let activeCompIdx = 0;
let selectedBus = null;
let searchText = '';
let openPin = null;

function getColor(pin) {
  if (pin.active_function) return BUS_COLORS[pin.active_function.type] || '#666';
  return TYPE_COLORS[pin.type] || '#666';
}

function togglePanel() {
  document.getElementById('sidePanel').classList.toggle('collapsed');
}

function handleSearch(v) {
  searchText = v.toLowerCase();
  renderCompList();
}

function selectComp(idx) {
  activeCompIdx = idx;
  selectedBus = null;
  openPin = null;
  document.getElementById('detailPopup').style.display = 'none';
  renderCompList();
  renderChip();
  renderLegend();
}

function selectBus(busType) {
  selectedBus = selectedBus === busType ? null : busType;
  openPin = null;
  document.getElementById('detailPopup').style.display = 'none';
  renderChip();
  renderLegend();
}

function renderCompList() {
  const el = document.getElementById('compList');
  const comps = DATA.components.filter(c =>
    !searchText ||
    c.name.toLowerCase().includes(searchText) ||
    (c.designator||'').toLowerCase().includes(searchText)
  );
  el.innerHTML = comps.map((c, i) => {
    const realIdx = DATA.components.indexOf(c);
    const active = realIdx === activeCompIdx ? ' active' : '';
    return '<div class="comp-item'+active+'" onclick="selectComp('+realIdx+')">'
      + '<span class="des">'+(c.designator||'')+'</span>'
      + '<span class="name">'+esc(c.name)+'</span>'
      + '<span class="cnt">'+c.pin_count+'</span>'
      + '</div>';
  }).join('');
}

function renderLegend() {
  const comp = DATA.components[activeCompIdx];
  if (!comp) return;
  const types = new Set();
  comp.pins.forEach(p => {
    if (p.active_function) types.add(p.active_function.type);
    if (p.type==='power'||p.type==='ground') types.add('Power');
  });
  const el = document.getElementById('legendGrid');
  el.innerHTML = Object.entries(BUS_COLORS).filter(([t])=>types.has(t)||t==='GPIO'||t==='Signal').map(([t,c])=>{
    const act = selectedBus===t?' active':'';
    return '<div class="legend-chip'+act+'" onclick="selectBus(\\''+t+'\\')">'
      +'<div class="legend-swatch" style="background:'+c+'"></div>'
      +t+'</div>';
  }).join('');
}

function renderChip() {
  const comp = DATA.components[activeCompIdx];
  if (!comp || !comp.geometry) { document.getElementById('svgContainer').innerHTML=''; return; }

  const geo = comp.geometry;
  const bbox = geo.pad_bbox;
  const LABEL_MARGIN = 12; // mm for label text space
  const PAD = 2; // extra padding

  // SVG viewport: enough room for chip + labels on all sides
  const vx = bbox.min_x - LABEL_MARGIN - PAD;
  const vy = bbox.min_y - LABEL_MARGIN - PAD;
  const vw = (bbox.max_x - bbox.min_x) + 2*LABEL_MARGIN + 2*PAD;
  const vh = (bbox.max_y - bbox.min_y) + 2*LABEL_MARGIN + 2*PAD;

  let svg = '<svg class="chip-svg" viewBox="'+vx+' '+vy+' '+vw+' '+vh+'" xmlns="http://www.w3.org/2000/svg">';

  // Chip body
  const r = 0.4;
  svg += '<rect class="chip-body-rect" x="'+geo.x+'" y="'+geo.y+'" width="'+geo.width+'" height="'+geo.height+'" rx="'+r+'"/>';

  // Pin 1 marker
  svg += '<circle class="pin1-dot" cx="'+(geo.x+1.2)+'" cy="'+(geo.y+1.2)+'" r="0.6"/>';

  // Chip label
  const cx = geo.x + geo.width/2;
  const cy = geo.y + geo.height/2;
  svg += '<text class="chip-body-label" x="'+cx+'" y="'+(cy-1)+'">'+esc(comp.designator||comp.name)+'</text>';
  if (comp.module_type) {
    svg += '<text class="chip-body-label" x="'+cx+'" y="'+(cy+2)+'" style="font-size:2px;opacity:.6">'+esc(comp.module_type)+'</text>';
  }

  // Render each pin
  comp.pins.forEach((pin, idx) => {
    if (pin.x == null || pin.y == null) return;
    const color = getColor(pin);
    const side = pin.side;
    const pw = pin.w || 0.5;
    const ph = pin.h || 0.5;

    // Determine highlight state
    let cls = 'pad-rect';
    if (selectedBus) {
      if (pin.active_function && pin.active_function.type === selectedBus) cls += ' highlighted';
      else if (pin.type==='power'&&selectedBus==='Power'||pin.type==='ground'&&selectedBus==='Power') cls += ' highlighted';
      else cls += ' faded';
    }

    // Pad rectangle
    svg += '<rect class="'+cls+'" x="'+(pin.x-pw/2)+'" y="'+(pin.y-ph/2)+'" width="'+pw+'" height="'+ph+'" rx="0.1" fill="'+color+'" onclick="pinClick('+idx+',event)"/>';

    // Pin name label (on the pad or just outside)
    const nameText = esc(pin.name);
    const fnText = pin.active_function ? esc(pin.active_function.name) : '';
    const LO = 0.8; // label offset from pad edge

    if (side === 'left') {
      // Name to the left of pad, right-aligned
      svg += '<text class="pin-label left" x="'+(pin.x-pw/2-LO)+'" y="'+pin.y+'">'+nameText+'</text>';
      if (fnText) svg += '<text class="fn-label left" x="'+(pin.x+pw/2+LO)+'" y="'+pin.y+'">'+fnText+'</text>';
    } else if (side === 'right') {
      svg += '<text class="pin-label right" x="'+(pin.x+pw/2+LO)+'" y="'+pin.y+'">'+nameText+'</text>';
      if (fnText) svg += '<text class="fn-label right" x="'+(pin.x-pw/2-LO)+'" y="'+pin.y+'">'+fnText+'</text>';
    } else if (side === 'top') {
      // Rotated label above pad
      svg += '<text class="pin-label top" x="0" y="0" transform="translate('+(pin.x)+','+(pin.y-ph/2-LO)+') rotate(-90)">'+nameText+'</text>';
      if (fnText) svg += '<text class="fn-label top" x="0" y="0" transform="translate('+(pin.x)+','+(pin.y+ph/2+LO)+') rotate(-90)">'+fnText+'</text>';
    } else if (side === 'bottom') {
      svg += '<text class="pin-label bottom" x="0" y="0" transform="translate('+(pin.x)+','+(pin.y+ph/2+LO)+') rotate(-90)">'+nameText+'</text>';
      if (fnText) svg += '<text class="fn-label bottom" x="0" y="0" transform="translate('+(pin.x)+','+(pin.y-ph/2-LO)+') rotate(-90)">'+fnText+'</text>';
    }
  });

  svg += '</svg>';
  document.getElementById('svgContainer').innerHTML = svg;
}

function pinClick(idx, event) {
  const comp = DATA.components[activeCompIdx];
  const pin = comp.pins[idx];
  if (!pin) return;

  // If clicking same pin, close
  if (openPin === idx) {
    openPin = null;
    document.getElementById('detailPopup').style.display = 'none';
    return;
  }
  openPin = idx;

  const popup = document.getElementById('detailPopup');
  const color = getColor(pin);
  let html = '<span class="dp-close" onclick="closeDetail()">&times;</span>';
  html += '<div class="dp-header">';
  html += '<span class="dp-pin">Pin '+esc(pin.number)+'</span>';
  html += '<span class="dp-name">'+esc(pin.name)+'</span>';
  html += '<span class="dp-type" style="background:'+color+'">'+esc(pin.type)+'</span>';
  html += '</div>';

  if (pin.active_function) {
    html += '<div class="dp-section">Active Function</div>';
    html += '<div class="dp-fn"><div class="dp-fn-dot" style="background:'+BUS_COLORS[pin.active_function.type]+'"></div>';
    html += '<span class="dp-fn-name">'+esc(pin.active_function.name)+'</span>';
    html += '<span class="dp-fn-type">'+esc(pin.active_function.type)+'</span></div>';
  }

  if (pin.alternate_functions && pin.alternate_functions.length > 0) {
    html += '<div class="dp-section">Alternate Functions</div>';
    pin.alternate_functions.forEach(fn => {
      html += '<div class="dp-fn"><div class="dp-fn-dot" style="background:'+(BUS_COLORS[fn.type]||'#666')+'"></div>';
      html += '<span class="dp-fn-name">'+esc(fn.name)+'</span>';
      html += '<span class="dp-fn-type">'+esc(fn.type)+'</span></div>';
    });
  }

  if (pin.pad_count && pin.pad_count > 1) {
    html += '<div style="margin-top:6px;font-size:10px;color:var(--fg-muted)">'+pin.pad_count+' pads connected</div>';
  }

  popup.innerHTML = html;
  popup.style.display = 'block';

  // Position near click
  const rect = document.getElementById('mainArea').getBoundingClientRect();
  let px = event.clientX + 12;
  let py = event.clientY - 20;
  if (px + 320 > rect.right) px = event.clientX - 320;
  if (py + 200 > rect.bottom) py = rect.bottom - 210;
  if (py < rect.top) py = rect.top + 4;
  popup.style.left = px + 'px';
  popup.style.top = py + 'px';
}

function closeDetail() {
  openPin = null;
  document.getElementById('detailPopup').style.display = 'none';
}

function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') : ''; }

// Close detail on outside click
document.addEventListener('click', e => {
  const popup = document.getElementById('detailPopup');
  if (popup.style.display !== 'none' && !popup.contains(e.target) && !e.target.classList.contains('pad-rect')) {
    closeDetail();
  }
});

// Init
renderCompList();
renderLegend();
renderChip();
</script>
</body>
</html>`;
    }
}

let pinoutExplorer: PinoutExplorerWebview | undefined;

export async function openPinoutExplorer() {
    if (!pinoutExplorer) {
        pinoutExplorer = new PinoutExplorerWebview();
    }
    await pinoutExplorer.open();
}

export function closePinoutExplorer() {
    pinoutExplorer?.dispose();
    pinoutExplorer = undefined;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onPinoutChanged((_) => {
            if (pinoutExplorer?.isOpen()) {
                openPinoutExplorer();
            }
        }),
    );
}

export function deactivate() {
    closePinoutExplorer();
}

#!/bin/bash
# Apply atopile branding to OpenVSCode Server
set -euo pipefail

BRANDING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_RESOURCES="${OPENVSCODE_SERVER_ROOT}/resources/server"
WORKBENCH_HTML="${OPENVSCODE_SERVER_ROOT}/out/vs/code/browser/workbench/workbench.html"

echo "=== Applying atopile branding ==="

# Replace icons with atopile logo
cp "${BRANDING_DIR}/ato_logo_256x256.png" "${SERVER_RESOURCES}/code-192.png"
cp "${BRANDING_DIR}/ato_logo_256x256.png" "${SERVER_RESOURCES}/code-512.png"

# Generate favicon.ico from PNG using Python (available via uv)
python3 -c "
from PIL import Image
import io, struct

img = Image.open('${BRANDING_DIR}/ato_logo_256x256.png').convert('RGBA')

# Create multi-size ICO with 16, 32, 48 pixel sizes
sizes = [(16, 16), (32, 32), (48, 48)]
ico_images = []
for size in sizes:
    resized = img.resize(size, Image.LANCZOS)
    ico_images.append(resized)

ico_images[0].save(
    '${SERVER_RESOURCES}/favicon.ico',
    format='ICO',
    sizes=[(s.width, s.height) for s in ico_images],
    append_images=ico_images[1:]
)
print('Generated favicon.ico')
" 2>/dev/null || {
    # Fallback: just copy the PNG as favicon (works in all modern browsers)
    echo "PIL not available, using PNG as favicon"
    cp "${BRANDING_DIR}/ato_logo_256x256.png" "${SERVER_RESOURCES}/favicon.ico"
}

# Replace manifest.json
cp "${BRANDING_DIR}/manifest.json" "${SERVER_RESOURCES}/manifest.json"

# Patch workbench.html: set title and use PNG favicon
sed -i 's|<link rel="icon" href="{{WORKBENCH_WEB_BASE_URL}}/resources/server/favicon.ico" type="image/x-icon" />|<link rel="icon" href="{{WORKBENCH_WEB_BASE_URL}}/resources/server/favicon.ico" type="image/x-icon" />\n\t\t<title>atopile</title>|' "${WORKBENCH_HTML}"

# Patch apple-mobile-web-app-title
sed -i 's|content="Code"|content="atopile"|' "${WORKBENCH_HTML}"

# Patch product.json: disable workspace trust prompt (this is a cloud dev environment)
# Must use top-level "disableWorkspaceTrust" key, NOT configurationDefaults —
# the trust check happens at the environment level before settings are consulted.
PRODUCT_JSON="${OPENVSCODE_SERVER_ROOT}/product.json"
if [ -f "${PRODUCT_JSON}" ]; then
    "${OPENVSCODE_SERVER_ROOT}/node" -e "
const fs = require('fs');
const p = JSON.parse(fs.readFileSync('${PRODUCT_JSON}', 'utf8'));

// Disable workspace trust prompt (cloud dev environment)
p.disableWorkspaceTrust = true;

// Force webview bootstrap assets to same-origin.
// In proxied/self-hosted deployments, relying on *.vscode-cdn.net for the
// initial webview iframe can fail due network/policy restrictions.
p.webviewContentExternalBaseUrlTemplate = '/stable-{{commit}}/static/out/vs/workbench/contrib/webview/browser/pre/';

// Remove extension marketplace — users cannot install extensions
delete p.extensionsGallery;

// Security: lock down terminal, debug, and task features via configurationDefaults
p.configurationDefaults = Object.assign(p.configurationDefaults || {}, {
    // Disable integrated terminal
    'terminal.integrated.profiles.linux': {},
    'terminal.integrated.defaultProfile.linux': null,
    'terminal.integrated.allowChords': false,
    'terminal.integrated.sendKeybindingsToShell': false,

    // Disable debug/run features
    'debug.allowBreakpointsEverywhere': false,
    'debug.showInlineBreakpointCandidates': false,
    'debug.showInStatusBar': 'never',
    'debug.toolBarLocation': 'hidden',

    // Disable task system
    'task.allowAutomaticTasks': 'never',
    'task.autoDetect': 'off',

    // Disable git (defense-in-depth; extensions also removed)
    'git.enabled': false,
    'git.autoRepositoryDetection': false,

    // Lock down extensions UI (defense-in-depth; dirs are also read-only)
    'extensions.autoUpdate': false,
    'extensions.autoCheckUpdates': false,
    'extensions.ignoreRecommendations': true,
});

fs.writeFileSync('${PRODUCT_JSON}', JSON.stringify(p, null, '\t'));
console.log('Patched product.json: security hardening applied');
"
fi

# Patch workbench.js: allow webviews to run on non-secure HTTP origins.
# Upstream hard-fails when crypto.subtle is unavailable; that blocks webviews
# on hostnames like http://code-vm even though everything else is reachable.
WORKBENCH_JS="${OPENVSCODE_SERVER_ROOT}/out/vs/code/browser/workbench/workbench.js"
if [ -f "${WORKBENCH_JS}" ]; then
    "${OPENVSCODE_SERVER_ROOT}/node" -e "
const fs = require('fs');
const p = '${WORKBENCH_JS}';
let s = fs.readFileSync(p, 'utf8');
const oldSnippet = \"async function oLt(i,e){if(!crypto.subtle)throw new Error(\\\"'crypto.subtle' is not available so webviews will not work. This is likely because the editor is not running in a secure context (https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts).\\\");const t=JSON.stringify({parentOrigin:i,salt:e}),n=new TextEncoder().encode(t),r=await crypto.subtle.digest(\\\"sha-256\\\",n);return m4i(r)}\";
const newSnippet = \"async function oLt(i,e){const t=JSON.stringify({parentOrigin:i,salt:e}),n=new TextEncoder().encode(t);if(crypto.subtle){const r=await crypto.subtle.digest(\\\"sha-256\\\",n);return m4i(r)}let r=2166136261;for(const o of n)r=Math.imul(r^o,16777619)>>>0;return r.toString(32).padStart(52,\\\"0\\\").slice(-52)}\";
if (!s.includes(oldSnippet)) {
    console.warn('workbench.js webview patch: target snippet not found, skipped');
    process.exit(0);
}
s = s.replace(oldSnippet, newSnippet);
fs.writeFileSync(p, s);
console.log('Patched workbench.js: webview crypto fallback enabled');
"
fi

echo "=== Branding applied ==="

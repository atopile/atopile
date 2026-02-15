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
});

fs.writeFileSync('${PRODUCT_JSON}', JSON.stringify(p, null, '\t'));
console.log('Patched product.json: security hardening applied');
"
fi

echo "=== Branding applied ==="

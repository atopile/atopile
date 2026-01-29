# Parts Panel Technical Review

## Overview

This review covers the prototype implementation of the parts panel in the VSCode extension. The implementation adds a complete parts search, installation, and visualization system for JLCPCB/LCSC parts.

---

## Architecture & Responsibility Split

### Frontend (UI Server)

**1. PartsSearchPanel.tsx** (`src/ui-server/src/components/PartsSearchPanel.tsx`)
- **Responsibilities:**
  - Tab-based UI with "Find Parts" and "Project" views
  - Parts search with debounced queries (250ms)
  - Display installed parts for the selected project
  - Real-time enrichment of installed parts (stock/price data)
  - Sortable table columns (MPN, description, manufacturer, stock, price)
  - Filter functionality for project parts
- **State Management:**
  - Manages search results, installed parts, loading states, errors
  - Tracks which parts are being enriched with a `Set<string>`
  - Uses `useMemo` for filtered/sorted lists
- **Dependencies:** Calls API client methods: `api.parts.search()`, `api.parts.installed()`, `api.parts.lcsc()`

**2. PartsDetailPanel.tsx** (`src/ui-server/src/components/PartsDetailPanel.tsx`)
- **Responsibilities:**
  - Displays detailed part information
  - Visual tabs: Image, Footprint (KiCanvas), 3D Model (STEP viewer)
  - Install/uninstall functionality
  - Shows part attributes, pricing tiers, stock levels
- **State Management:**
  - Tracks install/uninstall operations with separate loading/error states
  - Manages visual tab selection
  - Computes installed status from props and local state
- **Dependencies:** Uses `KiCanvasEmbed` and `StepViewer` components

**3. Supporting Components**

**KiCanvasEmbed.tsx** (`src/ui-server/src/components/KiCanvasEmbed.tsx`)
- Dynamically loads kicanvas.js custom element
- Pre-validates footprint URLs with fetch before rendering
- Multiple event listeners for load/error states
- 5-second timeout fallback for loading detection

**StepViewer.tsx** (`src/ui-server/src/components/StepViewer.tsx`)
- Dynamically imports `occt-import-js` WASM module
- Parses STEP files and renders with Three.js
- Handles per-face coloring from BREP data
- OrbitControls for 3D navigation
- Proper cleanup on unmount (animation frames, WebGL context)

**4. API Client** (`src/ui-server/src/api/client.ts`)
- Clean, typed interface for all parts endpoints
- Defines request/response types inline and imports from `types/build.ts`
- Part-specific methods under `api.parts.*`

**5. Type Definitions** (`src/ui-server/src/types/build.ts`)
- `PartSearchItem`: Full part data with attributes
- `PartSearchResponse`, `PartDetailsResponse`: API response wrappers
- `InstalledPartItem`: Installed part metadata
- `InstalledPartsResponse`: List response
- `SelectedPart`: Simplified part type for UI selection (defined in `sidebar-modules/sidebarUtils.ts:108`)

---

### Backend (Server)

**1. Routes** (`src/atopile/server/routes/parts_search.py`)
- **Responsibilities:** FastAPI route handlers that delegate to domain functions
- **Endpoints:**
  - `GET /api/parts/search` → `handle_search_parts()`
  - `GET /api/parts/{lcsc_id}/details` → `handle_get_part_details()`
  - `GET /api/parts/{lcsc_id}/footprint.kicad_pcb` → `handle_get_part_footprint()`
  - `GET /api/parts/{lcsc_id}/model` → `handle_get_part_model()`
  - `GET /api/parts/installed` → `handle_list_installed_parts()`
  - `POST /api/parts/install` → `handle_install_part()`
  - `POST /api/parts/uninstall` → `handle_uninstall_part()`
- **Pattern:** All routes use `asyncio.to_thread()` to run domain functions in thread pool
- **Error Handling:** HTTP 400 for `ValueError`, 404 for not found, wrapped exceptions in 500s

**2. Domain Logic - Main** (`src/atopile/server/domains/parts_search.py`)
- **Responsibilities:**
  - Search provider selection (atopile backend vs JLC public scraping)
  - Part installation/uninstallation via `PartLifecycle` and `AtoPart`
  - Listing installed parts from project's parts directory
  - Fetching footprint/3D model data from EasyEDA API
  - Attribute deserialization with pretty-printing of faebryk literals
- **Key Functions:**
  - `handle_search_parts()`: Routes to backend or JLC provider based on env var
  - `handle_get_part_details()`: Fetches from API client + JLC image
  - `handle_install_part()`: Downloads EasyEDA part, ingests to library
  - `handle_uninstall_part()`: Validates auto-generated flag, deletes part
  - `handle_get_part_footprint()`: Fetches, converts, wraps in kicad_pcb template
  - `handle_get_part_model()`: Fetches STEP model from EasyEDA API
  - `_pretty_attributes()`: Deserializes faebryk literals for display
- **Footprint Conversion:** Complex `_lib_fp_to_pcb_fp()` function converts library footprints to PCB format by:
  - Extracting common fields between `kicad.footprint.Footprint` and `kicad.pcb.Footprint`
  - Converting pads to PCB pad format
  - Generating UUIDs
  - Wrapping in template PCB file for kicanvas viewing

**3. Domain Logic - LCSC Data** (`src/atopile/server/domains/parts.py`)
- **Responsibilities:**
  - Fetches LCSC part data via picker API client
  - Out-of-stock logging with 24h TTL cache
  - Part data serialization
- **Key Functions:**
  - `handle_get_lcsc_parts()`: Batch fetch LCSC parts with normalization
  - `_serialize_component()`: Converts `Component` to dict (similar to `_serialize_part` in parts_search.py)
  - `_log_out_of_stock()`: Logs warnings for out-of-stock parts with build context

**4. Domain Logic - JLC Public Search** (`src/atopile/server/domains/parts_search_jlc.py`)
- **Responsibilities:** Web scraping fallback for JLC public parts search
- **Marked as "hacky"** in docstring
- **Features:**
  - Rate limiting (default 5 RPS)
  - IPv4 fallback resolution
  - Retry logic with exponential backoff
  - Configurable via environment variables:
    - `ATOPILE_PARTS_SEARCH_PROVIDER`: Switch between providers
    - `ATOPILE_JLC_TIMEOUT_S`, `ATOPILE_JLC_RPS`, `ATOPILE_JLC_RETRIES`, `ATOPILE_JLC_DEBUG`
- **Implementation:**
  - Direct HTTP POST to jlcpcb.com search API
  - Custom User-Agent and headers to mimic browser
  - Manual IPv4 resolution for connection issues
  - Image URL extraction from multiple fields

---

## API Endpoints Summary

| Method | Endpoint | Purpose | Handler |
|--------|----------|---------|---------|
| GET | `/api/parts/search` | Search parts by query | `handle_search_parts()` |
| GET | `/api/parts/{lcsc_id}/details` | Get detailed part info | `handle_get_part_details()` |
| GET | `/api/parts/{lcsc_id}/footprint.kicad_pcb` | Get footprint for kicanvas | `handle_get_part_footprint()` |
| GET | `/api/parts/{lcsc_id}/model` | Get STEP 3D model | `handle_get_part_model()` |
| GET | `/api/parts/installed` | List installed parts | `handle_list_installed_parts()` |
| POST | `/api/parts/install` | Install part to project | `handle_install_part()` |
| POST | `/api/parts/uninstall` | Uninstall part from project | `handle_uninstall_part()` |

**Additional Context Endpoints** (not new, but used):
- POST `/api/parts/lcsc` - Batch enrich LCSC data (used for installed parts enrichment)

---

## Debug/Mess Identified

### Console Statements

**KiCanvasEmbed.tsx:**
- Line 105: `console.log('[KiCanvas] Load event fired')`
- Line 109: `console.log('[KiCanvas] Error event fired', e)`
- Line 122: `console.log('[KiCanvas] Timeout reached, assuming loaded')`
- **Recommendation:** Remove or convert to proper logging framework

**StepViewer.tsx:**
- Line 52: `console.error('WASM load error:', wasmError)` - **OK** (error logging)
- Line 147-153: `console.log('[StepViewer] brep_faces debug:', {...})` - **Debug code**, should be removed
- **Recommendation:** Remove brep_faces debug logging

**PartsSearchPanel.tsx:**
- Line 121: `console.warn('Parts enrichment failed:', err)`
- **Assessment:** This is acceptable - it's a non-blocking warning for background enrichment failures

### Code Quality Issues

1. **Duplicate Serialization Logic**
   - `parts.py:_serialize_component()` (lines 27-58)
   - `parts_search.py:_serialize_part()` (lines 35-67)
   - Nearly identical functions, should be consolidated

2. **JLC Search Provider**
   - Marked as "hacky" in docstring
   - Web scraping implementation feels fragile
   - Environment variable switching between providers is implicit
   - **Recommendation:** Document when to use which provider, or remove if not needed

3. **Unused Test Function**
   - `parts_search.py:test_selftest_pretty_attributes()` (lines 445-481)
   - Docstring says "Not executed automatically; call manually if needed"
   - **Recommendation:** Convert to proper pytest test or remove

4. **Complex Footprint Conversion**
   - `_lib_fp_to_pcb_fp()` function (lines 270-298) is quite involved
   - Field mapping between footprint types could be fragile
   - **Recommendation:** Add unit tests for this conversion

---

## Architectural Concerns

### 1. Search Provider Split
- Two separate search implementations:
  1. Atopile backend via picker API (`_search_atopile_backend`)
  2. JLC public scraping (`search_jlc_parts`)
- Switched via `ATOPILE_PARTS_SEARCH_PROVIDER` environment variable
- **Concern:** No clear documentation on when/why to use each
- **Recommendation:**
  - Document the use case for each provider
  - Consider making the choice more explicit (config file vs env var)
  - If JLC scraping is temporary, add a deprecation plan

### 2. Image Fetching Strategy
- `handle_get_part_details()` calls `_fetch_jlc_image()` as a fallback
- JLC image fetch does a full search just to get the image URL
- **Concern:** Wasteful if part details already include image URL
- **Recommendation:** Check if API provides image URL and skip JLC fallback

### 3. Enrichment Flow
- Installed parts are listed with basic info
- Frontend then calls `/api/parts/lcsc` to enrich stock/price
- **Assessment:** This is a good pattern - fast initial load, progressive enhancement
- **Note:** Frontend shows spinners during enrichment

### 4. Footprint/Model Fetching
- Direct EasyEDA API calls in domain logic
- Complex conversion logic embedded in handlers
- **Recommendation:** Consider extracting to separate service modules:
  - `parts_easyeda.py` for EasyEDA API interactions
  - `parts_kicad.py` for KiCad format conversions

---

## Good Practices Observed

1. **Clean Separation of Concerns**
   - Routes delegate to domain functions
   - Domain functions don't know about HTTP
   - Type definitions centralized

2. **Async Patterns**
   - Routes properly use `asyncio.to_thread()` for blocking calls
   - Frontend uses async/await consistently

3. **Error Handling**
   - Try/catch blocks with proper error types
   - HTTP status codes map to error conditions
   - User-friendly error messages

4. **Type Safety**
   - TypeScript interfaces for all API types
   - Pydantic models for request/response validation

5. **Progressive Enhancement**
   - Parts list shows immediately, enriches in background
   - Loading states shown during enrichment

6. **Resource Cleanup**
   - StepViewer properly disposes Three.js resources
   - Animation frames cancelled on unmount
   - Fetch requests aborted on component unmount

7. **User Experience**
   - Debounced search (250ms)
   - Sortable tables
   - Filter functionality
   - Visual feedback for all operations

---

## Recommendations

### High Priority

1. **Remove Debug Console Statements**
   - Clean up KiCanvasEmbed.tsx logging
   - Remove StepViewer.tsx brep_faces debug code

2. **Consolidate Duplicate Code**
   - Merge `_serialize_component()` and `_serialize_part()` into single function
   - Share code between parts.py and parts_search.py

3. **Document Search Providers**
   - Add README or docstring explaining when to use each provider
   - Document environment variables for JLC scraping

### Medium Priority

4. **Extract EasyEDA/KiCad Logic**
   - Create separate modules for EasyEDA API and KiCad conversions
   - Makes testing easier and improves maintainability

5. **Add Tests**
   - Unit tests for footprint conversion (`_lib_fp_to_pcb_fp`)
   - Unit tests for attribute pretty-printing
   - Convert `test_selftest_pretty_attributes()` to proper pytest

6. **Optimize Image Fetching**
   - Check if picker API provides image URLs before JLC fallback
   - Cache image URLs to avoid repeated JLC searches

### Low Priority

7. **Consider Provider Architecture**
   - If both search providers are needed long-term, create a provider interface
   - Make provider selection explicit in config

8. **Add Metrics**
   - Track search latency
   - Monitor JLC scraping success rate
   - Track installation success/failure rates

---

## Security Considerations

1. **Web Scraping**
   - JLC scraping could break if they change their API
   - Rate limiting is in place (good)
   - No API key required (could be fragile)

2. **File Operations**
   - `handle_uninstall_part()` checks `auto_generated` flag before deletion (good)
   - Uses `robustly_rm_dir()` for safe deletion
   - Validates LCSC ID format before operations

3. **Input Validation**
   - LCSC ID normalization with regex (`_LCSC_RE`)
   - Query string validation (non-empty checks)

---

## Performance Notes

1. **Batch Operations**
   - Frontend batches LCSC enrichment requests (good)
   - Backend handles multiple LCSC IDs in one call

2. **Caching**
   - Out-of-stock cache (24h TTL) reduces log spam
   - No part data caching (could add if needed)

3. **Loading States**
   - Progressive loading: show immediately, enrich later
   - Debounced search reduces API calls

---

## Summary

The parts panel implementation is **functionally complete and well-structured**. The main concerns are:

1. **Debug code** left in production files (console.log statements)
2. **Duplicate serialization logic** between modules
3. **Unclear provider strategy** (atopile vs JLC scraping)
4. **Complex footprint conversion** that could use testing

The architecture follows good patterns with clean separation of concerns, proper async handling, and progressive enhancement. With the cleanup items addressed, this would be production-ready.

**Estimated cleanup effort:** 2-4 hours
- 30 mins: Remove debug statements
- 1 hour: Consolidate duplicate code
- 1 hour: Add documentation for providers
- 1-2 hours: Add tests (optional but recommended)

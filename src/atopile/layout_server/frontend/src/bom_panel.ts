import type { Editor } from "./editor";
import type { BOMComponent, BOMData, FootprintModel } from "./types";

interface BomTableRow {
    key: string;
    displayValue: string;
    designators: string[];
    uuids: string[];
    quantity: number;
    bomDetail: BOMComponent | null;
}

// Persistent state across rebuilds
let bomPanelCollapsed = false;
let selectedRowKey: string | null = null;
let searchPattern = "";
let isRegex = false;
let isCaseSensitive = false;
let bomData: BOMData | null = null;
let currentRows: BomTableRow[] = [];
let filteredRows: BomTableRow[] = [];
let syncingFromBom = false;

function naturalSort(a: string, b: string): number {
    return a.localeCompare(b, undefined, { numeric: true });
}

function buildRows(footprints: FootprintModel[]): BomTableRow[] {
    const groups = new Map<string, { designators: string[]; uuids: string[] }>();

    for (const fp of footprints) {
        const value = fp.value ?? "";
        const name = fp.name;
        const key = `${value}\0${name}`;

        let group = groups.get(key);
        if (!group) {
            group = { designators: [], uuids: [] };
            groups.set(key, group);
        }
        if (fp.reference) group.designators.push(fp.reference);
        if (fp.uuid) group.uuids.push(fp.uuid);
    }

    const rows: BomTableRow[] = [];
    for (const [key, group] of groups) {
        group.designators.sort(naturalSort);
        const value = key.split("\0")[0]!;
        const name = key.split("\0")[1]!;
        rows.push({
            key,
            displayValue: value || name,
            designators: group.designators,
            uuids: group.uuids,
            quantity: group.designators.length || group.uuids.length,
            bomDetail: null,
        });
    }

    rows.sort((a, b) => {
        const aFirst = a.designators[0] ?? "";
        const bFirst = b.designators[0] ?? "";
        return naturalSort(aFirst, bFirst);
    });

    return rows;
}

function matchBomDetails(rows: BomTableRow[], data: BOMData) {
    // Build a designator→BOMComponent map
    const designatorMap = new Map<string, BOMComponent>();
    for (const comp of data.components) {
        for (const usage of comp.usages) {
            designatorMap.set(usage.designator, comp);
        }
    }

    for (const row of rows) {
        for (const des of row.designators) {
            const comp = designatorMap.get(des);
            if (comp) {
                row.bomDetail = comp;
                // Update displayValue if it was just the footprint name
                if (!row.key.split("\0")[0] && comp.mpn) {
                    row.displayValue = comp.mpn;
                }
                break;
            }
        }
    }
}

function filterRows(rows: BomTableRow[], pattern: string, regex: boolean, caseSensitive: boolean): BomTableRow[] {
    if (!pattern) return rows;

    if (regex) {
        let re: RegExp;
        try {
            re = new RegExp(pattern, caseSensitive ? "" : "i");
        } catch {
            return rows; // invalid regex, show all
        }
        return rows.filter(row => {
            const designators = row.designators.join(", ");
            const address = row.bomDetail?.usages[0]?.address ?? "";
            return re.test(designators) || re.test(row.displayValue) || re.test(address);
        });
    }

    const needle = caseSensitive ? pattern : pattern.toLowerCase();
    return rows.filter(row => {
        const designators = row.designators.join(", ");
        const address = row.bomDetail?.usages[0]?.address ?? "";
        const haystack = caseSensitive
            ? `${designators} ${row.displayValue} ${address}`
            : `${designators} ${row.displayValue} ${address}`.toLowerCase();
        return haystack.includes(needle);
    });
}

function renderDetailPanel(container: HTMLElement, row: BomTableRow | null) {
    container.innerHTML = "";
    if (!row) {
        container.style.display = "none";
        return;
    }
    container.style.display = "block";

    const detail = row.bomDetail;
    if (!detail) {
        const loading = document.createElement("div");
        loading.className = "bom-detail-loading";
        loading.textContent = "Loading...";
        container.appendChild(loading);
        return;
    }

    const fields: [string, string | null | undefined][] = [
        ["MPN", detail.mpn],
        ["Manufacturer", detail.manufacturer],
        ["LCSC", detail.lcsc],
        ["Package", detail.package],
        ["Description", detail.description],
        ["Type", detail.type],
        ["Source", detail.source],
        ["Unit Cost", detail.unitCost != null ? `$${detail.unitCost.toFixed(4)}` : null],
        ["Stock", detail.stock != null ? detail.stock.toLocaleString() : null],
    ];

    for (const [label, value] of fields) {
        if (!value) continue;
        const row = document.createElement("div");
        row.className = "bom-detail-row";
        const labelEl = document.createElement("span");
        labelEl.className = "bom-detail-label";
        labelEl.textContent = label;
        const valueEl = document.createElement("span");
        valueEl.className = "bom-detail-value";
        valueEl.textContent = value;
        row.appendChild(labelEl);
        row.appendChild(valueEl);
        container.appendChild(row);
    }

    // Parameters
    if (detail.parameters.length > 0) {
        for (const param of detail.parameters) {
            const row = document.createElement("div");
            row.className = "bom-detail-row";
            const labelEl = document.createElement("span");
            labelEl.className = "bom-detail-label";
            labelEl.textContent = param.name;
            const valueEl = document.createElement("span");
            valueEl.className = "bom-detail-value";
            valueEl.textContent = param.unit ? `${param.value} ${param.unit}` : param.value;
            row.appendChild(labelEl);
            row.appendChild(valueEl);
            container.appendChild(row);
        }
    }
}

export function buildBomPanel(editor: Editor, baseUrl: string, apiPrefix: string) {
    const panel = document.getElementById("bom-panel");
    if (!panel) return;
    panel.innerHTML = "";

    // Rebuild rows from current model
    currentRows = buildRows(editor.getFootprints());
    if (bomData) matchBomDetails(currentRows, bomData);
    filteredRows = filterRows(currentRows, searchPattern, isRegex, isCaseSensitive);

    // --- Header ---
    const header = document.createElement("div");
    header.className = "bom-panel-header";

    const headerTitle = document.createElement("span");
    headerTitle.textContent = "BOM";

    // Expand tab
    let expandTab = document.getElementById("bom-expand-tab");
    if (!expandTab) {
        expandTab = document.createElement("div");
        expandTab.id = "bom-expand-tab";
        expandTab.className = "bom-expand-tab";
        expandTab.textContent = "BOM";
        expandTab.addEventListener("click", () => {
            bomPanelCollapsed = false;
            panel.classList.remove("collapsed");
            expandTab!.classList.remove("visible");
        });
        document.body.appendChild(expandTab);
    }

    const collapseBtn = document.createElement("span");
    collapseBtn.className = "bom-collapse-btn";
    collapseBtn.textContent = "\u25B6";
    collapseBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        bomPanelCollapsed = true;
        panel.classList.add("collapsed");
        expandTab!.classList.add("visible");
    });

    header.appendChild(headerTitle);
    header.appendChild(collapseBtn);
    panel.appendChild(header);

    // --- Search bar ---
    const searchBar = document.createElement("div");
    searchBar.className = "bom-search";

    const searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search... (/)";
    searchInput.value = searchPattern;
    searchInput.addEventListener("input", () => {
        searchPattern = searchInput.value;
        updateFilteredRows();
        renderTableBody();
        // Validate regex
        if (isRegex && searchPattern) {
            try {
                new RegExp(searchPattern);
                searchInput.classList.remove("bom-search-error");
            } catch {
                searchInput.classList.add("bom-search-error");
            }
        } else {
            searchInput.classList.remove("bom-search-error");
        }
    });
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            searchInput.blur();
            return;
        }
        // Prevent editor shortcuts (R, F, etc.) from firing while typing
        if (e.key !== "Escape") {
            e.stopPropagation();
        }
    });

    const regexToggle = document.createElement("button");
    regexToggle.className = "bom-search-toggle" + (isRegex ? " active" : "");
    regexToggle.textContent = ".*";
    regexToggle.title = "Regex search";
    regexToggle.addEventListener("click", () => {
        isRegex = !isRegex;
        regexToggle.classList.toggle("active", isRegex);
        updateFilteredRows();
        renderTableBody();
    });

    const caseToggle = document.createElement("button");
    caseToggle.className = "bom-search-toggle" + (isCaseSensitive ? " active" : "");
    caseToggle.textContent = "Aa";
    caseToggle.title = "Case sensitive";
    caseToggle.addEventListener("click", () => {
        isCaseSensitive = !isCaseSensitive;
        caseToggle.classList.toggle("active", isCaseSensitive);
        updateFilteredRows();
        renderTableBody();
    });

    searchBar.appendChild(searchInput);
    searchBar.appendChild(regexToggle);
    searchBar.appendChild(caseToggle);
    panel.appendChild(searchBar);

    // --- Table header ---
    const tableHeader = document.createElement("div");
    tableHeader.className = "bom-table-header";
    const qtyH = document.createElement("span");
    qtyH.className = "bom-qty";
    qtyH.textContent = "Qty";
    const desH = document.createElement("span");
    desH.className = "bom-designators";
    desH.textContent = "Designators";
    const valH = document.createElement("span");
    valH.className = "bom-value";
    valH.textContent = "Value";
    tableHeader.appendChild(qtyH);
    tableHeader.appendChild(desH);
    tableHeader.appendChild(valH);
    panel.appendChild(tableHeader);

    // --- Table body ---
    const tableBody = document.createElement("div");
    tableBody.className = "bom-table-body";
    panel.appendChild(tableBody);

    // --- Detail panel ---
    const detailPanel = document.createElement("div");
    detailPanel.className = "bom-detail";
    detailPanel.style.display = "none";
    panel.appendChild(detailPanel);

    function updateFilteredRows() {
        filteredRows = filterRows(currentRows, searchPattern, isRegex, isCaseSensitive);
    }

    function renderTableBody() {
        tableBody.innerHTML = "";
        for (const row of filteredRows) {
            const rowEl = document.createElement("div");
            rowEl.className = "bom-row";
            if (row.key === selectedRowKey) rowEl.classList.add("selected");

            const qty = document.createElement("span");
            qty.className = "bom-qty";
            qty.textContent = String(row.quantity);

            const des = document.createElement("span");
            des.className = "bom-designators";
            des.textContent = row.designators.join(", ");
            des.title = row.designators.join(", ");

            const val = document.createElement("span");
            val.className = "bom-value";
            val.textContent = row.displayValue;
            val.title = row.displayValue;

            rowEl.appendChild(qty);
            rowEl.appendChild(des);
            rowEl.appendChild(val);

            rowEl.addEventListener("click", () => {
                selectRow(row, rowEl);
            });

            tableBody.appendChild(rowEl);
        }
    }

    function selectRow(row: BomTableRow, rowEl?: HTMLElement) {
        selectedRowKey = row.key;

        // Update row highlighting
        const allRows = tableBody.querySelectorAll(".bom-row");
        allRows.forEach(r => r.classList.remove("selected"));
        if (rowEl) {
            rowEl.classList.add("selected");
        } else {
            // Find and highlight the row
            const rows = tableBody.querySelectorAll(".bom-row");
            for (let i = 0; i < filteredRows.length && i < rows.length; i++) {
                if (filteredRows[i]!.key === row.key) {
                    rows[i]!.classList.add("selected");
                    rows[i]!.scrollIntoView({ block: "nearest" });
                    break;
                }
            }
        }

        // Sync to canvas
        syncingFromBom = true;
        editor.selectFootprintsByUuids(row.uuids);
        syncingFromBom = false;

        // Show detail
        renderDetailPanel(detailPanel, row);

        // Lazy fetch BOM data if not yet loaded
        if (!row.bomDetail && !bomData) {
            fetchBomData();
        }
    }

    async function fetchBomData() {
        try {
            const resp = await fetch(`${baseUrl}${apiPrefix}/bom`);
            if (!resp.ok) {
                bomData = null;
                // Update detail panel to show "No detail available"
                if (selectedRowKey) {
                    const row = currentRows.find(r => r.key === selectedRowKey);
                    if (row && !row.bomDetail) {
                        const msg = document.createElement("div");
                        msg.className = "bom-detail-loading";
                        msg.textContent = "No detail available";
                        detailPanel.innerHTML = "";
                        detailPanel.appendChild(msg);
                    }
                }
                return;
            }
            bomData = await resp.json() as BOMData;
            matchBomDetails(currentRows, bomData);
            // Re-render detail if a row is selected
            if (selectedRowKey) {
                const row = currentRows.find(r => r.key === selectedRowKey);
                renderDetailPanel(detailPanel, row ?? null);
            }
            // Re-render table body to update displayValues
            filteredRows = filterRows(currentRows, searchPattern, isRegex, isCaseSensitive);
            renderTableBody();
            // Re-select previously selected row
            if (selectedRowKey) {
                const allTableRows = tableBody.querySelectorAll(".bom-row");
                for (let i = 0; i < filteredRows.length && i < allTableRows.length; i++) {
                    if (filteredRows[i]!.key === selectedRowKey) {
                        allTableRows[i]!.classList.add("selected");
                        break;
                    }
                }
            }
        } catch {
            // Silently fail — detail will show "Loading..." or "No detail available"
        }
    }

    // Render initial table
    renderTableBody();

    // Restore selection
    if (selectedRowKey) {
        const row = currentRows.find(r => r.key === selectedRowKey);
        if (row) {
            renderDetailPanel(detailPanel, row);
            // Scroll selected row into view after render
            requestAnimationFrame(() => {
                const rows = tableBody.querySelectorAll(".bom-row");
                for (let i = 0; i < filteredRows.length && i < rows.length; i++) {
                    if (filteredRows[i]!.key === selectedRowKey) {
                        rows[i]!.scrollIntoView({ block: "nearest" });
                        break;
                    }
                }
            });
        }
    }

    // Restore collapse state
    if (bomPanelCollapsed) {
        panel.classList.add("collapsed");
        expandTab!.classList.add("visible");
    }

    // --- Bidirectional selection sync (editor → BOM) ---
    editor.setOnSelectionChanged((uuids: string[]) => {
        if (syncingFromBom) return;
        if (uuids.length === 0) {
            selectedRowKey = null;
            const allTableRows = tableBody.querySelectorAll(".bom-row");
            allTableRows.forEach(r => r.classList.remove("selected"));
            renderDetailPanel(detailPanel, null);
            return;
        }

        const uuidSet = new Set(uuids);
        let matchedRow: BomTableRow | null = null;
        for (const row of filteredRows) {
            if (row.uuids.some(u => uuidSet.has(u))) {
                matchedRow = row;
                break;
            }
        }

        if (matchedRow) {
            selectedRowKey = matchedRow.key;
            const allTableRows = tableBody.querySelectorAll(".bom-row");
            allTableRows.forEach(r => r.classList.remove("selected"));
            for (let i = 0; i < filteredRows.length && i < allTableRows.length; i++) {
                if (filteredRows[i]!.key === matchedRow.key) {
                    allTableRows[i]!.classList.add("selected");
                    allTableRows[i]!.scrollIntoView({ block: "nearest" });
                    break;
                }
            }
            renderDetailPanel(detailPanel, matchedRow);
            if (!matchedRow.bomDetail && !bomData) {
                fetchBomData();
            }
        }
    });

    // --- Keyboard shortcuts ---
    // Remove previous handler if any (stored on window)
    const prevHandler = (window as any).__bomKeyHandler;
    if (prevHandler) window.removeEventListener("keydown", prevHandler);

    const keyHandler = (e: KeyboardEvent) => {
        // `/` — focus search
        if (e.key === "/" && document.activeElement !== searchInput && !(document.activeElement instanceof HTMLInputElement)) {
            e.preventDefault();
            searchInput.focus();
            return;
        }

        // Enter — select next row in filtered table
        if (e.key === "Enter") {
            if (filteredRows.length === 0) return;
            let nextIdx = 0;
            if (selectedRowKey) {
                const currentIdx = filteredRows.findIndex(r => r.key === selectedRowKey);
                nextIdx = currentIdx >= 0 ? (currentIdx + 1) % filteredRows.length : 0;
            }
            const nextRow = filteredRows[nextIdx]!;
            selectRow(nextRow);
            return;
        }
    };

    window.addEventListener("keydown", keyHandler);
    (window as any).__bomKeyHandler = keyHandler;
}

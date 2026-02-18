// BOM Table UI — vanilla JS
"use strict";

var BomUI = (function() {

function BomUI(containerId, bomData, refToBomId, renderer) {
    this.container = document.getElementById(containerId);
    this.components = bomData.components || [];
    this.refToBomId = refToBomId || {};
    this.renderer = renderer;
    this.sortCol = "quantity";
    this.sortAsc = false;
    this.filterText = "";
    this.useRegex = false;
    this.caseSensitive = false;
    this._matcher = null;
    this.selectedId = null;

    // Build id-to-component lookup
    this.byId = {};
    for (var i = 0; i < this.components.length; i++) {
        this.byId[this.components[i].id] = this.components[i];
    }

    this._buildUI();
    this.render();
}

// --- Build DOM ---

BomUI.prototype._buildUI = function() {
    var self = this;

    // Summary bar
    this.summaryEl = document.createElement("div");
    this.summaryEl.className = "bom-summary";
    this.container.appendChild(this.summaryEl);

    // Search bar
    var searchRow = document.createElement("div");
    searchRow.className = "bom-search-row";

    this.searchWrap = document.createElement("div");
    this.searchWrap.className = "bom-search-wrap";

    var searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search designators & addresses... (/)";
    searchInput.className = "bom-search";
    searchInput.id = "bom-search-input";
    searchInput.addEventListener("input", function() {
        self.filterText = this.value;
        self._updateMatcher();
        self.render();
    });
    searchInput.addEventListener("keydown", function(e) {
        if (e.key === "Escape") { this.blur(); }
        else if (e.key === "Enter") {
            e.preventDefault();
            self._navigateResult(e.shiftKey ? -1 : 1);
        }
    });
    this.searchWrap.appendChild(searchInput);

    // Case-sensitivity toggle
    var caseBtn = document.createElement("button");
    caseBtn.className = "search-toggle";
    caseBtn.textContent = "Aa";
    caseBtn.title = "Case insensitive";
    caseBtn.addEventListener("click", function() {
        self.caseSensitive = !self.caseSensitive;
        caseBtn.classList.toggle("active", self.caseSensitive);
        caseBtn.title = self.caseSensitive ? "Case sensitive" : "Case insensitive";
        self._updateMatcher();
        self.render();
    });
    this.searchWrap.appendChild(caseBtn);

    // Regex toggle
    var regexBtn = document.createElement("button");
    regexBtn.className = "search-toggle";
    regexBtn.textContent = ".*";
    regexBtn.title = "Enable regex";
    regexBtn.addEventListener("click", function() {
        self.useRegex = !self.useRegex;
        regexBtn.classList.toggle("active", self.useRegex);
        regexBtn.title = self.useRegex ? "Regex enabled" : "Enable regex";
        self._updateMatcher();
        self.render();
    });
    this.searchWrap.appendChild(regexBtn);

    searchRow.appendChild(this.searchWrap);
    this.container.appendChild(searchRow);

    // Table wrapper
    this.tableWrap = document.createElement("div");
    this.tableWrap.className = "bom-table-wrap";
    this.container.appendChild(this.tableWrap);

    // Detail panel (bottom of sidebar)
    this.detailEl = document.createElement("div");
    this.detailEl.className = "detail-panel";
    this.container.appendChild(this.detailEl);
};

// --- Render ---

BomUI.prototype.render = function() {
    var self = this;
    var filtered = this._getFiltered();
    filtered = this._getSorted(filtered);
    this._filteredIds = filtered.map(function(c) { return c.id; });

    // Update summary
    var totalQty = 0, totalCost = 0;
    for (var i = 0; i < filtered.length; i++) {
        totalQty += filtered[i].quantity;
        if (filtered[i].unitCost != null) totalCost += filtered[i].unitCost * filtered[i].quantity;
    }
    this.summaryEl.innerHTML =
        "<span><strong>" + filtered.length + "</strong> unique parts</span>" +
        "<span><strong>" + totalQty + "</strong> total components</span>" +
        (totalCost > 0 ? "<span>Est. cost: <strong>$" + totalCost.toFixed(2) + "</strong></span>" : "");

    // Build table — only Qty, Designators, Value
    var html = "<table class='bom-table'><thead><tr>";
    var cols = [
        { key: "quantity",    label: "Qty" },
        { key: "designators", label: "Designators" },
        { key: "value",       label: "Value" }
    ];
    for (var c = 0; c < cols.length; c++) {
        var arrow = "";
        if (this.sortCol === cols[c].key) arrow = this.sortAsc ? " ▲" : " ▼";
        html += "<th data-col='" + cols[c].key + "'>" + cols[c].label + arrow + "</th>";
    }
    html += "</tr></thead><tbody>";

    for (var j = 0; j < filtered.length; j++) {
        var comp = filtered[j];
        var desigs = comp.usages.map(function(u) { return u.designator; }).filter(Boolean);
        var isSelected = comp.id === this.selectedId;
        var rowClass = "bom-row" + (isSelected ? " selected" : "");

        html += "<tr class='" + rowClass + "' data-id='" + comp.id + "'>";
        html += "<td>" + comp.quantity + "</td>";
        html += "<td class='desig-cell'>" + this._formatDesignators(desigs) + "</td>";
        html += "<td>" + esc(comp.value || "") + "</td>";
        html += "</tr>";
    }

    html += "</tbody></table>";
    this.tableWrap.innerHTML = html;

    // Bind events
    var headers = this.tableWrap.querySelectorAll("th[data-col]");
    for (var h = 0; h < headers.length; h++) {
        headers[h].addEventListener("click", function() {
            var col = this.getAttribute("data-col");
            if (self.sortCol === col) self.sortAsc = !self.sortAsc;
            else { self.sortCol = col; self.sortAsc = true; }
            self.render();
        });
    }

    var rows = this.tableWrap.querySelectorAll("tr.bom-row");
    for (var r = 0; r < rows.length; r++) {
        rows[r].addEventListener("click", function(e) {
            var id = this.getAttribute("data-id");
            self._selectComponent(id);
        });
    }

    // Update detail panel
    this._renderDetailPanel();
};

BomUI.prototype._formatDesignators = function(desigs) {
    if (desigs.length <= 6) return desigs.map(esc).join(", ");
    return desigs.slice(0, 5).map(esc).join(", ") + " +" + (desigs.length - 5) + " more";
};

// --- Detail panel (bottom-right overlay) ---

BomUI.prototype._renderDetailPanel = function() {
    if (!this.detailEl) return;
    if (!this.selectedId) {
        this.detailEl.classList.remove("visible");
        return;
    }
    var comp = this.byId[this.selectedId];
    if (!comp) {
        this.detailEl.classList.remove("visible");
        return;
    }

    var desigs = comp.usages.map(function(u) { return u.designator; }).filter(Boolean);
    var html = "<div class='detail-header'>" + esc(desigs.join(", ")) + "</div>";
    html += "<table class='detail-table'>";
    html += "<tr><td class='detail-label'>Value</td><td>" + esc(comp.value || "-") + "</td></tr>";
    html += "<tr><td class='detail-label'>Package</td><td>" + esc(comp.package || "-") + "</td></tr>";
    if (comp.lcsc) html += "<tr><td class='detail-label'>LCSC</td><td><a href='https://jlcpcb.com/partdetail/" + esc(comp.lcsc) + "' target='_blank' rel='noopener'>" + esc(comp.lcsc) + "</a></td></tr>";
    if (comp.mpn) html += "<tr><td class='detail-label'>MPN</td><td>" + esc(comp.mpn) + "</td></tr>";
    if (comp.manufacturer) html += "<tr><td class='detail-label'>Manufacturer</td><td>" + esc(comp.manufacturer) + "</td></tr>";
    if (comp.description) html += "<tr><td class='detail-label'>Description</td><td>" + esc(comp.description) + "</td></tr>";
    html += "<tr><td class='detail-label'>Quantity</td><td>" + comp.quantity + "</td></tr>";
    if (comp.unitCost != null) {
        html += "<tr><td class='detail-label'>Unit cost</td><td>$" + comp.unitCost.toFixed(4) + "</td></tr>";
        html += "<tr><td class='detail-label'>Total cost</td><td>$" + (comp.unitCost * comp.quantity).toFixed(2) + "</td></tr>";
    }
    if (comp.source) html += "<tr><td class='detail-label'>Source</td><td>" + esc(comp.source) + "</td></tr>";
    if (comp.isBasic != null) html += "<tr><td class='detail-label'>Basic part</td><td>" + (comp.isBasic ? "Yes" : "No") + "</td></tr>";
    if (comp.stock != null) html += "<tr><td class='detail-label'>Stock</td><td>" + comp.stock.toLocaleString() + "</td></tr>";
    html += "</table>";

    if (comp.parameters && comp.parameters.length > 0) {
        html += "<div class='detail-section-title'>Parameters</div><table class='detail-table'>";
        for (var i = 0; i < comp.parameters.length; i++) {
            var p = comp.parameters[i];
            html += "<tr><td class='detail-label'>" + esc(p.name) + "</td><td>" + esc(p.value) + "</td></tr>";
        }
        html += "</table>";
    }

    if (comp.usages && comp.usages.length > 0) {
        html += "<div class='detail-section-title'>Addresses</div><div class='detail-addresses'>";
        for (var j = 0; j < comp.usages.length; j++) {
            var u = comp.usages[j];
            html += "<div>" + esc(u.designator) + " — <span class='detail-addr'>" + esc(u.address) + "</span></div>";
        }
        html += "</div>";
    }

    this.detailEl.innerHTML = html;
    this.detailEl.classList.add("visible");
};

// --- Filtering & sorting ---

BomUI.prototype._updateMatcher = function() {
    var pattern = this.filterText.trim();
    this._matcher = null;
    this._matcherError = false;
    if (!pattern) return;
    if (this.useRegex) {
        try {
            var flags = this.caseSensitive ? "" : "i";
            var re = new RegExp(pattern, flags);
            this._matcher = function(s) { return re.test(s); };
        } catch(e) {
            this._matcherError = true;
            this._matcher = function() { return false; };
        }
    } else {
        if (this.caseSensitive) {
            this._matcher = function(s) { return s.indexOf(pattern) >= 0; };
        } else {
            var lower = pattern.toLowerCase();
            this._matcher = function(s) { return s.toLowerCase().indexOf(lower) >= 0; };
        }
    }
    this.searchWrap.classList.toggle("search-error", this._matcherError);
};

BomUI.prototype._getFiltered = function() {
    if (!this._matcher) return this.components.slice();
    var test = this._matcher;
    return this.components.filter(function(c) {
        for (var i = 0; i < c.usages.length; i++) {
            if (test(c.usages[i].designator)) return true;
            if (test(c.usages[i].address)) return true;
        }
        return false;
    });
};

BomUI.prototype._getSorted = function(arr) {
    var col = this.sortCol;
    var asc = this.sortAsc ? 1 : -1;
    return arr.slice().sort(function(a, b) {
        var va, vb;
        if (col === "designators") {
            va = (a.usages[0] && a.usages[0].designator) || "";
            vb = (b.usages[0] && b.usages[0].designator) || "";
        } else {
            va = a[col]; vb = b[col];
        }
        if (va == null) va = "";
        if (vb == null) vb = "";
        if (typeof va === "string") return va.localeCompare(vb) * asc;
        return (va - vb) * asc;
    });
};

// --- Navigate search results with Enter/Shift+Enter ---

BomUI.prototype._navigateResult = function(direction) {
    var ids = this._filteredIds;
    if (!ids || ids.length === 0) return;
    var curIdx = this.selectedId ? ids.indexOf(this.selectedId) : -1;
    var nextIdx = curIdx + direction;
    if (nextIdx < 0) nextIdx = ids.length - 1;
    if (nextIdx >= ids.length) nextIdx = 0;
    this._selectComponent(ids[nextIdx]);
};

// --- Selection ---

BomUI.prototype._selectComponent = function(id) {
    if (this.selectedId === id) {
        this.selectedId = null;
        this.renderer.highlight([]);
    } else {
        this.selectedId = id;
        var comp = this.byId[id];
        if (comp) {
            var refs = comp.usages.map(function(u) { return u.designator; }).filter(Boolean);
            this.renderer.highlight(refs);
        }
    }
    this.render();
};

BomUI.prototype.selectByRef = function(ref) {
    if (!ref) {
        this.selectedId = null;
        this.renderer.highlight([]);
        this.render();
        return;
    }
    var bomId = this.refToBomId[ref];
    if (!bomId) return;
    var comp = this.byId[bomId];
    if (!comp) return;
    this.selectedId = bomId;
    var refs = comp.usages.map(function(u) { return u.designator; }).filter(Boolean);
    this.renderer.highlight(refs);
    this.render();
    // Scroll to selected row
    var row = this.tableWrap.querySelector("tr[data-id='" + bomId + "']");
    if (row) row.scrollIntoView({ behavior: "smooth", block: "nearest" });
};

function esc(s) {
    var d = document.createElement("span");
    d.textContent = s;
    return d.innerHTML;
}

return BomUI;
})();

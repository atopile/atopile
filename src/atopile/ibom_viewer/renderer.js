// Canvas 2D PCB Renderer — ported from painter.ts / math.ts / colors.ts / hit-test.ts
"use strict";

// ---------------------------------------------------------------------------
// Math utilities
// ---------------------------------------------------------------------------

function vec2(x, y) { return { x: x || 0, y: y || 0 }; }

function vec2Add(a, b) { return { x: a.x + b.x, y: a.y + b.y }; }
function vec2Sub(a, b) { return { x: a.x - b.x, y: a.y - b.y }; }

function bboxFromPoints(points) {
    if (points.length === 0) return { x: 0, y: 0, w: 0, h: 0 };
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (var i = 0; i < points.length; i++) {
        var p = points[i];
        if (p.x < minX) minX = p.x;
        if (p.y < minY) minY = p.y;
        if (p.x > maxX) maxX = p.x;
        if (p.y > maxY) maxY = p.y;
    }
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

function bboxGrow(b, d) {
    return { x: b.x - d, y: b.y - d, w: b.w + d * 2, h: b.h + d * 2 };
}

function bboxContains(b, p) {
    return p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
}

// ---------------------------------------------------------------------------
// Colors (from colors.ts)
// ---------------------------------------------------------------------------

var LAYER_COLORS = {
    "F.Cu":      [0.85, 0.20, 0.20, 0.8],
    "B.Cu":      [0.20, 0.40, 0.85, 0.8],
    "In1.Cu":    [0.85, 0.85, 0.20, 0.8],
    "In2.Cu":    [0.85, 0.40, 0.85, 0.8],
    "F.SilkS":   [0.0,  0.85, 0.85, 0.9],
    "B.SilkS":   [0.85, 0.0,  0.85, 0.9],
    "F.Mask":    [0.6,  0.15, 0.6,  0.4],
    "B.Mask":    [0.15, 0.6,  0.15, 0.4],
    "F.Paste":   [0.85, 0.55, 0.55, 0.5],
    "B.Paste":   [0.55, 0.55, 0.85, 0.5],
    "F.Fab":     [0.6,  0.6,  0.2,  0.7],
    "B.Fab":     [0.2,  0.2,  0.6,  0.7],
    "F.CrtYd":   [0.4,  0.4,  0.4,  0.5],
    "B.CrtYd":   [0.3,  0.3,  0.5,  0.5],
    "Edge.Cuts": [0.9,  0.85, 0.2,  1.0],
    "Dwgs.User": [0.6,  0.6,  0.6,  0.6],
    "Cmts.User": [0.4,  0.4,  0.8,  0.6]
};

var PAD_COLOR       = [0.35, 0.60, 0.35, 0.9];
var PAD_FRONT_COLOR = [0.85, 0.20, 0.20, 0.7];
var PAD_BACK_COLOR  = [0.20, 0.40, 0.85, 0.7];
var VIA_COLOR       = [0.6,  0.6,  0.6,  0.9];
var VIA_DRILL_COLOR = [0.15, 0.15, 0.15, 1.0];
var BOARD_BG        = [0.067, 0.067, 0.106, 1.0];
var ZONE_ALPHA      = 0.25;

function getLayerColor(layer) {
    if (!layer) return [0.5, 0.5, 0.5, 0.5];
    return LAYER_COLORS[layer] || [0.5, 0.5, 0.5, 0.5];
}

function getPadColor(layers) {
    var hasFront = false, hasBack = false;
    for (var i = 0; i < layers.length; i++) {
        if (layers[i] === "F.Cu" || layers[i] === "*.Cu") hasFront = true;
        if (layers[i] === "B.Cu" || layers[i] === "*.Cu") hasBack = true;
    }
    if (hasFront && hasBack) return PAD_COLOR;
    if (hasFront) return PAD_FRONT_COLOR;
    if (hasBack) return PAD_BACK_COLOR;
    return PAD_COLOR;
}

function rgba(c) {
    return "rgba(" + Math.round(c[0]*255) + "," + Math.round(c[1]*255) + "," + Math.round(c[2]*255) + "," + c[3] + ")";
}

function rgbaAlpha(c, a) {
    return "rgba(" + Math.round(c[0]*255) + "," + Math.round(c[1]*255) + "," + Math.round(c[2]*255) + "," + a + ")";
}

// ---------------------------------------------------------------------------
// Transform helpers (from painter.ts / hit-test.ts)
// ---------------------------------------------------------------------------

var DEG_TO_RAD = Math.PI / 180;

function fpTransform(fpAt, localX, localY) {
    var rad = -(fpAt.r || 0) * DEG_TO_RAD;
    var cos = Math.cos(rad), sin = Math.sin(rad);
    return { x: fpAt.x + localX * cos - localY * sin,
             y: fpAt.y + localX * sin + localY * cos };
}

function padTransform(fpAt, padAt, lx, ly) {
    var padRad = -(padAt.r || 0) * DEG_TO_RAD;
    var pc = Math.cos(padRad), ps = Math.sin(padRad);
    var px = lx * pc - ly * ps;
    var py = lx * ps + ly * pc;
    return fpTransform(fpAt, padAt.x + px, padAt.y + py);
}

function arcToPoints(start, mid, end, segments) {
    segments = segments || 32;
    var ax = start.x, ay = start.y;
    var bx = mid.x,   by = mid.y;
    var cx = end.x,    cy = end.y;

    var D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
    if (Math.abs(D) < 1e-10) return [vec2(ax, ay), vec2(bx, by), vec2(cx, cy)];

    var ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by)) / D;
    var uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax)) / D;
    var radius = Math.sqrt((ax-ux)*(ax-ux) + (ay-uy)*(ay-uy));
    var startAngle = Math.atan2(ay-uy, ax-ux);
    var midAngle   = Math.atan2(by-uy, bx-ux);
    var endAngle   = Math.atan2(cy-uy, cx-ux);

    var da1 = midAngle - startAngle;
    while (da1 > Math.PI)  da1 -= 2*Math.PI;
    while (da1 < -Math.PI) da1 += 2*Math.PI;

    var clockwise = da1 < 0;
    var sweep = endAngle - startAngle;
    if (clockwise) { while (sweep > 0) sweep -= 2*Math.PI; }
    else           { while (sweep < 0) sweep += 2*Math.PI; }

    var pts = [];
    for (var i = 0; i <= segments; i++) {
        var t = i / segments;
        var angle = startAngle + sweep * t;
        pts.push(vec2(ux + radius * Math.cos(angle), uy + radius * Math.sin(angle)));
    }
    return pts;
}

// ---------------------------------------------------------------------------
// Layer visibility (from painter.ts)
// ---------------------------------------------------------------------------

function isPadLayerVisible(padLayer, hidden, concreteLayers) {
    if (padLayer.indexOf("*") >= 0) {
        var suffix = padLayer.substring(padLayer.indexOf("."));
        for (var l of concreteLayers) {
            if (l.endsWith(suffix) && !hidden.has(l)) return true;
        }
        return false;
    }
    if (padLayer.indexOf("&") >= 0) {
        var dotIdx = padLayer.indexOf(".");
        if (dotIdx >= 0) {
            var prefixes = padLayer.substring(0, dotIdx).split("&");
            var suffix2 = padLayer.substring(dotIdx);
            return prefixes.some(function(p) { return !hidden.has(p + suffix2); });
        }
    }
    return !hidden.has(padLayer);
}

function collectConcreteLayers(model) {
    var layers = new Set();
    for (var fp of model.footprints) {
        layers.add(fp.layer);
        for (var pad of fp.pads) { for (var l of pad.layers) layers.add(l); }
        for (var d of fp.drawings) { if (d.layer) layers.add(d.layer); }
    }
    for (var t of model.tracks) { if (t.layer) layers.add(t.layer); }
    for (var a of model.arcs) { if (a.layer) layers.add(a.layer); }
    for (var z of model.zones) {
        for (var f of z.filled_polygons) layers.add(f.layer);
    }
    var toDelete = [];
    for (var ll of layers) { if (ll.indexOf("*") >= 0 || ll.indexOf("&") >= 0) toDelete.push(ll); }
    for (var dd of toDelete) layers.delete(dd);
    return layers;
}

// ---------------------------------------------------------------------------
// Hit testing (from hit-test.ts)
// ---------------------------------------------------------------------------

function footprintBBox(fp) {
    var points = [];
    for (var i = 0; i < fp.pads.length; i++) {
        var pad = fp.pads[i];
        var hw = pad.size.w / 2, hh = pad.size.h / 2;
        points.push(padTransform(fp.at, pad.at, -hw, -hh));
        points.push(padTransform(fp.at, pad.at,  hw, -hh));
        points.push(padTransform(fp.at, pad.at,  hw,  hh));
        points.push(padTransform(fp.at, pad.at, -hw,  hh));
    }
    for (var j = 0; j < fp.drawings.length; j++) {
        var d = fp.drawings[j];
        if (d.start)  points.push(fpTransform(fp.at, d.start.x, d.start.y));
        if (d.end)    points.push(fpTransform(fp.at, d.end.x, d.end.y));
        if (d.center) points.push(fpTransform(fp.at, d.center.x, d.center.y));
        if (d.points) {
            for (var k = 0; k < d.points.length; k++) {
                points.push(fpTransform(fp.at, d.points[k].x, d.points[k].y));
            }
        }
    }
    if (points.length === 0) return { x: fp.at.x - 1, y: fp.at.y - 1, w: 2, h: 2 };
    return bboxGrow(bboxFromPoints(points), 0.2);
}

function hitTestFootprints(worldPos, footprints) {
    for (var i = footprints.length - 1; i >= 0; i--) {
        if (bboxContains(footprintBBox(footprints[i]), worldPos)) return i;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Bounding box for entire model
// ---------------------------------------------------------------------------

function computeModelBBox(model) {
    var pts = [];
    for (var e of model.board.edges) {
        if (e.start)  pts.push(e.start);
        if (e.end)    pts.push(e.end);
        if (e.mid)    pts.push(e.mid);
        if (e.center) pts.push(e.center);
    }
    for (var fp of model.footprints) {
        pts.push({ x: fp.at.x, y: fp.at.y });
        for (var pad of fp.pads) pts.push(fpTransform(fp.at, pad.at.x, pad.at.y));
    }
    for (var t of model.tracks) { pts.push(t.start); pts.push(t.end); }
    for (var v of model.vias)   { pts.push(v.at); }
    if (pts.length === 0) return { x: 0, y: 0, w: 100, h: 100 };
    return bboxGrow(bboxFromPoints(pts), 5);
}

// ---------------------------------------------------------------------------
// PCB Renderer class
// ---------------------------------------------------------------------------

var PCBRenderer = (function() {

function PCBRenderer(canvasId, highlightCanvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.hlCanvas = document.getElementById(highlightCanvasId);
    this.hlCtx = this.hlCanvas.getContext("2d");
    this.model = null;
    this.hiddenLayers = new Set();
    this.concreteLayers = new Set();
    // Camera
    this.camX = 0;
    this.camY = 0;
    this.zoom = 1;
    this.rotation = 0; // 0, 90, 180, 270
    this.flipBoard = false;
    // Selection
    this.highlightedRefs = new Set();
    this.onFootprintClick = null; // callback(reference)
    // Interaction state
    this._dragging = false;
    this._dragStartX = 0;
    this._dragStartY = 0;
    this._camStartX = 0;
    this._camStartY = 0;
    this._rafPending = false;

    this._bindEvents();
}

PCBRenderer.prototype.setModel = function(model) {
    this.model = model;
    this.concreteLayers = collectConcreteLayers(model);
    this.fitView();
};

PCBRenderer.prototype.fitView = function() {
    if (!this.model) return;
    var bbox = computeModelBBox(this.model);
    var cw = this.canvas.width, ch = this.canvas.height;
    var scaleX = cw / (bbox.w || 1);
    var scaleY = ch / (bbox.h || 1);
    this.zoom = Math.min(scaleX, scaleY) * 0.9;
    this.camX = bbox.x + bbox.w / 2;
    this.camY = bbox.y + bbox.h / 2;
    this.requestRedraw();
};

PCBRenderer.prototype.resize = function() {
    var rect = this.canvas.parentElement.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.canvas.style.width = rect.width + "px";
    this.canvas.style.height = rect.height + "px";
    this.hlCanvas.width = rect.width * dpr;
    this.hlCanvas.height = rect.height * dpr;
    this.hlCanvas.style.width = rect.width + "px";
    this.hlCanvas.style.height = rect.height + "px";
    this.requestRedraw();
};

// --- Coordinate transforms ---

PCBRenderer.prototype.worldToScreen = function(wx, wy) {
    var cw = this.canvas.width, ch = this.canvas.height;
    var sx = (wx - this.camX) * this.zoom + cw / 2;
    var sy = (wy - this.camY) * this.zoom + ch / 2;
    return { x: sx, y: sy };
};

PCBRenderer.prototype.screenToWorld = function(sx, sy) {
    var cw = this.canvas.width, ch = this.canvas.height;
    var wx = (sx - cw / 2) / this.zoom + this.camX;
    var wy = (sy - ch / 2) / this.zoom + this.camY;
    return { x: wx, y: wy };
};

// --- Event binding ---

PCBRenderer.prototype._bindEvents = function() {
    var self = this;
    this.canvas.addEventListener("mousedown", function(e) { self._onMouseDown(e); });
    this.canvas.addEventListener("mousemove", function(e) { self._onMouseMove(e); });
    this.canvas.addEventListener("mouseup",   function(e) { self._onMouseUp(e); });
    this.canvas.addEventListener("wheel",     function(e) { self._onWheel(e); }, { passive: false });
    // Touch support
    this.canvas.addEventListener("touchstart", function(e) { self._onTouchStart(e); }, { passive: false });
    this.canvas.addEventListener("touchmove",  function(e) { self._onTouchMove(e); }, { passive: false });
    this.canvas.addEventListener("touchend",   function(e) { self._onTouchEnd(e); });
};

PCBRenderer.prototype._canvasCoords = function(e) {
    var rect = this.canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    return { x: (e.clientX - rect.left) * dpr, y: (e.clientY - rect.top) * dpr };
};

PCBRenderer.prototype._onMouseDown = function(e) {
    this._dragging = true;
    var c = this._canvasCoords(e);
    this._dragStartX = c.x;
    this._dragStartY = c.y;
    this._camStartX = this.camX;
    this._camStartY = this.camY;
    this.canvas.style.cursor = "grabbing";
};

PCBRenderer.prototype._onMouseMove = function(e) {
    if (!this._dragging) return;
    var c = this._canvasCoords(e);
    var dx = c.x - this._dragStartX;
    var dy = c.y - this._dragStartY;
    this.camX = this._camStartX - dx / this.zoom;
    this.camY = this._camStartY - dy / this.zoom;
    this.requestRedraw();
};

PCBRenderer.prototype._onMouseUp = function(e) {
    var c = this._canvasCoords(e);
    var wasDrag = Math.abs(c.x - this._dragStartX) > 3 || Math.abs(c.y - this._dragStartY) > 3;
    this._dragging = false;
    this.canvas.style.cursor = "grab";
    if (!wasDrag && this.model) {
        var world = this.screenToWorld(c.x, c.y);
        // If board is flipped, mirror X for hit test
        if (this.flipBoard) {
            var bbox = computeModelBBox(this.model);
            world.x = 2 * (bbox.x + bbox.w / 2) - world.x;
        }
        var idx = hitTestFootprints(world, this.model.footprints);
        if (idx >= 0) {
            var ref = this.model.footprints[idx].reference;
            if (ref && this.onFootprintClick) this.onFootprintClick(ref);
        } else {
            // Click empty space: clear selection
            if (this.onFootprintClick) this.onFootprintClick(null);
        }
    }
};

PCBRenderer.prototype._onWheel = function(e) {
    e.preventDefault();
    var c = this._canvasCoords(e);
    var worldBefore = this.screenToWorld(c.x, c.y);
    var factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    this.zoom *= factor;
    this.zoom = Math.max(0.1, Math.min(this.zoom, 10000));
    var worldAfter = this.screenToWorld(c.x, c.y);
    this.camX -= (worldAfter.x - worldBefore.x);
    this.camY -= (worldAfter.y - worldBefore.y);
    this.requestRedraw();
};

// Touch support for mobile
PCBRenderer.prototype._onTouchStart = function(e) {
    if (e.touches.length === 1) {
        e.preventDefault();
        var t = e.touches[0];
        this._onMouseDown({ clientX: t.clientX, clientY: t.clientY });
    }
};

PCBRenderer.prototype._onTouchMove = function(e) {
    if (e.touches.length === 1) {
        e.preventDefault();
        var t = e.touches[0];
        this._onMouseMove({ clientX: t.clientX, clientY: t.clientY });
    }
};

PCBRenderer.prototype._onTouchEnd = function(e) {
    if (e.changedTouches.length === 1) {
        var t = e.changedTouches[0];
        this._onMouseUp({ clientX: t.clientX, clientY: t.clientY });
    }
};

// --- Rendering ---

PCBRenderer.prototype.requestRedraw = function() {
    if (this._rafPending) return;
    this._rafPending = true;
    var self = this;
    requestAnimationFrame(function() {
        self._rafPending = false;
        self.draw();
        self.drawHighlights();
    });
};

PCBRenderer.prototype.draw = function() {
    var ctx = this.ctx;
    var cw = this.canvas.width, ch = this.canvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = rgba(BOARD_BG);
    ctx.fillRect(0, 0, cw, ch);

    if (!this.model) return;

    ctx.save();
    // Set up camera transform
    ctx.translate(cw / 2, ch / 2);
    if (this.rotation) ctx.rotate(this.rotation * DEG_TO_RAD);
    if (this.flipBoard) ctx.scale(-1, 1);
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-this.camX, -this.camY);

    var model = this.model;
    var hidden = this.hiddenLayers;

    // Draw zones
    if (model.zones.length > 0) this._drawZones(ctx, model, hidden);
    // Draw board edges
    if (!hidden.has("Edge.Cuts")) this._drawBoardEdges(ctx, model);
    // Draw tracks
    this._drawTracks(ctx, model, hidden);
    // Draw vias
    if (!hidden.has("Vias")) this._drawVias(ctx, model);
    // Draw footprints
    for (var i = 0; i < model.footprints.length; i++) {
        this._drawFootprint(ctx, model.footprints[i], hidden);
    }

    ctx.restore();
};

PCBRenderer.prototype._drawBoardEdges = function(ctx, model) {
    var c = getLayerColor("Edge.Cuts");
    ctx.strokeStyle = rgba(c);
    ctx.lineWidth = 0.15;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (var i = 0; i < model.board.edges.length; i++) {
        var edge = model.board.edges[i];
        ctx.beginPath();
        if (edge.type === "line" && edge.start && edge.end) {
            ctx.moveTo(edge.start.x, edge.start.y);
            ctx.lineTo(edge.end.x, edge.end.y);
        } else if (edge.type === "arc" && edge.start && edge.mid && edge.end) {
            var pts = arcToPoints(edge.start, edge.mid, edge.end);
            ctx.moveTo(pts[0].x, pts[0].y);
            for (var j = 1; j < pts.length; j++) ctx.lineTo(pts[j].x, pts[j].y);
        } else if (edge.type === "circle" && edge.center && edge.end) {
            var cx = edge.center.x, cy = edge.center.y;
            var rad = Math.sqrt((edge.end.x-cx)*(edge.end.x-cx) + (edge.end.y-cy)*(edge.end.y-cy));
            ctx.arc(cx, cy, rad, 0, 2 * Math.PI);
        } else if (edge.type === "rect" && edge.start && edge.end) {
            var s = edge.start, e = edge.end;
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(e.x, s.y);
            ctx.lineTo(e.x, e.y);
            ctx.lineTo(s.x, e.y);
            ctx.closePath();
        }
        ctx.stroke();
    }
};

PCBRenderer.prototype._drawZones = function(ctx, model, hidden) {
    for (var i = 0; i < model.zones.length; i++) {
        var zone = model.zones[i];
        for (var j = 0; j < zone.filled_polygons.length; j++) {
            var filled = zone.filled_polygons[j];
            if (hidden.has(filled.layer)) continue;
            var c = getLayerColor(filled.layer);
            ctx.fillStyle = rgbaAlpha(c, ZONE_ALPHA);
            var pts = filled.points;
            if (pts.length < 3) continue;
            ctx.beginPath();
            ctx.moveTo(pts[0].x, pts[0].y);
            for (var k = 1; k < pts.length; k++) ctx.lineTo(pts[k].x, pts[k].y);
            ctx.closePath();
            ctx.fill();
        }
    }
};

PCBRenderer.prototype._drawTracks = function(ctx, model, hidden) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Segment tracks grouped by layer
    var byLayer = {};
    for (var i = 0; i < model.tracks.length; i++) {
        var t = model.tracks[i];
        var ln = t.layer || "F.Cu";
        if (hidden.has(ln)) continue;
        if (!byLayer[ln]) byLayer[ln] = [];
        byLayer[ln].push(t);
    }
    for (var layerName in byLayer) {
        var c = getLayerColor(layerName);
        ctx.strokeStyle = rgba(c);
        var tracks = byLayer[layerName];
        for (var j = 0; j < tracks.length; j++) {
            var tr = tracks[j];
            ctx.lineWidth = tr.width;
            ctx.beginPath();
            ctx.moveTo(tr.start.x, tr.start.y);
            ctx.lineTo(tr.end.x, tr.end.y);
            ctx.stroke();
        }
    }

    // Arc tracks
    var arcByLayer = {};
    for (var i2 = 0; i2 < model.arcs.length; i2++) {
        var a = model.arcs[i2];
        var ln2 = a.layer || "F.Cu";
        if (hidden.has(ln2)) continue;
        if (!arcByLayer[ln2]) arcByLayer[ln2] = [];
        arcByLayer[ln2].push(a);
    }
    for (var layerName2 in arcByLayer) {
        var c2 = getLayerColor(layerName2);
        ctx.strokeStyle = rgba(c2);
        var arcs = arcByLayer[layerName2];
        for (var k = 0; k < arcs.length; k++) {
            var arc = arcs[k];
            ctx.lineWidth = arc.width;
            var pts = arcToPoints(arc.start, arc.mid, arc.end);
            ctx.beginPath();
            ctx.moveTo(pts[0].x, pts[0].y);
            for (var m = 1; m < pts.length; m++) ctx.lineTo(pts[m].x, pts[m].y);
            ctx.stroke();
        }
    }
};

PCBRenderer.prototype._drawVias = function(ctx, model) {
    for (var i = 0; i < model.vias.length; i++) {
        var via = model.vias[i];
        // Via body
        ctx.fillStyle = rgba(VIA_COLOR);
        ctx.beginPath();
        ctx.arc(via.at.x, via.at.y, via.size / 2, 0, 2 * Math.PI);
        ctx.fill();
        // Drill hole
        ctx.fillStyle = rgba(VIA_DRILL_COLOR);
        ctx.beginPath();
        ctx.arc(via.at.x, via.at.y, via.drill / 2, 0, 2 * Math.PI);
        ctx.fill();
    }
};

PCBRenderer.prototype._drawFootprint = function(ctx, fp, hidden) {
    var concreteLayers = this.concreteLayers;

    // Drawings grouped by layer
    for (var i = 0; i < fp.drawings.length; i++) {
        var drawing = fp.drawings[i];
        var ln = drawing.layer || "F.SilkS";
        if (hidden.has(ln)) continue;
        var c = getLayerColor(ln);
        this._drawDrawing(ctx, fp.at, drawing, c);
    }

    // Pads
    for (var j = 0; j < fp.pads.length; j++) {
        var pad = fp.pads[j];
        var anyVisible = false;
        for (var k = 0; k < pad.layers.length; k++) {
            if (isPadLayerVisible(pad.layers[k], hidden, concreteLayers)) { anyVisible = true; break; }
        }
        if (anyVisible) this._drawPad(ctx, fp.at, pad);
    }
};

PCBRenderer.prototype._drawDrawing = function(ctx, fpAt, drawing, color) {
    var w = drawing.width || 0.12;
    ctx.strokeStyle = rgba(color);
    ctx.lineWidth = w;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (drawing.type === "line" && drawing.start && drawing.end) {
        var p1 = fpTransform(fpAt, drawing.start.x, drawing.start.y);
        var p2 = fpTransform(fpAt, drawing.end.x, drawing.end.y);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
    } else if (drawing.type === "arc" && drawing.start && drawing.mid && drawing.end) {
        var localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
        ctx.beginPath();
        var wp0 = fpTransform(fpAt, localPts[0].x, localPts[0].y);
        ctx.moveTo(wp0.x, wp0.y);
        for (var i = 1; i < localPts.length; i++) {
            var wp = fpTransform(fpAt, localPts[i].x, localPts[i].y);
            ctx.lineTo(wp.x, wp.y);
        }
        ctx.stroke();
    } else if (drawing.type === "circle" && drawing.center && drawing.end) {
        var cx2 = drawing.center.x, cy2 = drawing.center.y;
        var rad = Math.sqrt((drawing.end.x-cx2)*(drawing.end.x-cx2) + (drawing.end.y-cy2)*(drawing.end.y-cy2));
        var pts = [];
        for (var j = 0; j <= 48; j++) {
            var angle = (j / 48) * 2 * Math.PI;
            pts.push(fpTransform(fpAt, cx2 + rad * Math.cos(angle), cy2 + rad * Math.sin(angle)));
        }
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (var k = 1; k < pts.length; k++) ctx.lineTo(pts[k].x, pts[k].y);
        ctx.stroke();
    } else if (drawing.type === "rect" && drawing.start && drawing.end) {
        var s = drawing.start, e = drawing.end;
        var c0 = fpTransform(fpAt, s.x, s.y);
        var c1 = fpTransform(fpAt, e.x, s.y);
        var c2 = fpTransform(fpAt, e.x, e.y);
        var c3 = fpTransform(fpAt, s.x, e.y);
        ctx.beginPath();
        ctx.moveTo(c0.x, c0.y);
        ctx.lineTo(c1.x, c1.y);
        ctx.lineTo(c2.x, c2.y);
        ctx.lineTo(c3.x, c3.y);
        ctx.closePath();
        ctx.stroke();
    } else if (drawing.type === "polygon" && drawing.points && drawing.points.length >= 3) {
        ctx.beginPath();
        var wp0b = fpTransform(fpAt, drawing.points[0].x, drawing.points[0].y);
        ctx.moveTo(wp0b.x, wp0b.y);
        for (var m = 1; m < drawing.points.length; m++) {
            var wpm = fpTransform(fpAt, drawing.points[m].x, drawing.points[m].y);
            ctx.lineTo(wpm.x, wpm.y);
        }
        ctx.closePath();
        ctx.stroke();
    }
};

PCBRenderer.prototype._drawPad = function(ctx, fpAt, pad) {
    var c = getPadColor(pad.layers);
    var hw = pad.size.w / 2, hh = pad.size.h / 2;

    if (pad.shape === "circle") {
        var center = fpTransform(fpAt, pad.at.x, pad.at.y);
        ctx.fillStyle = rgba(c);
        ctx.beginPath();
        ctx.arc(center.x, center.y, hw, 0, 2 * Math.PI);
        ctx.fill();
    } else if (pad.shape === "oval") {
        // Oval = thick line between focal points
        var longAxis  = Math.max(hw, hh);
        var shortAxis = Math.min(hw, hh);
        var focalDist = longAxis - shortAxis;
        var p1, p2;
        if (hw >= hh) {
            p1 = padTransform(fpAt, pad.at, -focalDist, 0);
            p2 = padTransform(fpAt, pad.at,  focalDist, 0);
        } else {
            p1 = padTransform(fpAt, pad.at, 0, -focalDist);
            p2 = padTransform(fpAt, pad.at, 0,  focalDist);
        }
        ctx.strokeStyle = rgba(c);
        ctx.lineCap = "round";
        ctx.lineWidth = shortAxis * 2;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
    } else {
        // rect / roundrect / trapezoid — draw as filled polygon
        var corners = [
            padTransform(fpAt, pad.at, -hw, -hh),
            padTransform(fpAt, pad.at,  hw, -hh),
            padTransform(fpAt, pad.at,  hw,  hh),
            padTransform(fpAt, pad.at, -hw,  hh)
        ];
        ctx.fillStyle = rgba(c);
        ctx.beginPath();
        ctx.moveTo(corners[0].x, corners[0].y);
        for (var i = 1; i < 4; i++) ctx.lineTo(corners[i].x, corners[i].y);
        ctx.closePath();
        ctx.fill();
    }

    // Drill hole
    if (pad.drill && pad.type === "thru_hole") {
        var drCenter = fpTransform(fpAt, pad.at.x, pad.at.y);
        var drillR = (pad.drill.size_x != null ? pad.drill.size_x : pad.size.w * 0.5) / 2;
        ctx.fillStyle = "rgba(38,38,38,1)";
        ctx.beginPath();
        ctx.arc(drCenter.x, drCenter.y, drillR, 0, 2 * Math.PI);
        ctx.fill();
    }
};

// --- Highlight layer ---

PCBRenderer.prototype.highlight = function(refs) {
    this.highlightedRefs = new Set(refs || []);
    this.drawHighlights();
};

PCBRenderer.prototype.drawHighlights = function() {
    var ctx = this.hlCtx;
    var cw = this.hlCanvas.width, ch = this.hlCanvas.height;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cw, ch);

    if (!this.model || this.highlightedRefs.size === 0) return;

    ctx.save();
    ctx.translate(cw / 2, ch / 2);
    if (this.rotation) ctx.rotate(this.rotation * DEG_TO_RAD);
    if (this.flipBoard) ctx.scale(-1, 1);
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-this.camX, -this.camY);

    ctx.fillStyle = "rgba(255,255,255,0.25)";

    for (var i = 0; i < this.model.footprints.length; i++) {
        var fp = this.model.footprints[i];
        if (!fp.reference || !this.highlightedRefs.has(fp.reference)) continue;
        var bbox = footprintBBox(fp);
        bbox = bboxGrow(bbox, 0.3);
        ctx.fillRect(bbox.x, bbox.y, bbox.w, bbox.h);

        // Draw a brighter border
        ctx.strokeStyle = "rgba(255,255,100,0.7)";
        ctx.lineWidth = 0.15;
        ctx.strokeRect(bbox.x, bbox.y, bbox.w, bbox.h);
    }

    ctx.restore();
};

// --- Layer controls ---

PCBRenderer.prototype.setLayerVisibility = function(layer, visible) {
    if (visible) this.hiddenLayers.delete(layer);
    else this.hiddenLayers.add(layer);
    this.requestRedraw();
};

PCBRenderer.prototype.toggleFlip = function() {
    this.flipBoard = !this.flipBoard;
    this.requestRedraw();
};

PCBRenderer.prototype.setRotation = function(deg) {
    this.rotation = deg;
    this.requestRedraw();
};

return PCBRenderer;
})();

import { Vec2, Matrix3, BBox } from "../math";
import { ShaderProgram, VertexArray, Buffer } from "./helpers";
import { polygon_vert, polygon_frag, polyline_vert, polyline_frag, point_vert, point_frag, blit_vert, blit_frag } from "./shaders";
import {
    tessellate_polyline, tessellate_circle, triangulate_polygon,
    type TessPolylineResult, type TessCircleResult, type TessPolygonResult,
} from "./tessellator";

/** A set of GPU-uploaded primitives for one render layer */
class PrimitiveSet {
    #polyline_data: TessPolylineResult[] = [];
    #circle_data: TessCircleResult[] = [];
    #polygon_data: TessPolygonResult[] = [];

    // committed GPU state
    #poly_vao?: VertexArray;
    #poly_pos_buf?: Buffer;
    #poly_color_buf?: Buffer;
    #poly_vertex_count = 0;

    #line_vao?: VertexArray;
    #line_pos_buf?: Buffer;
    #line_cap_buf?: Buffer;
    #line_color_buf?: Buffer;
    #line_vertex_count = 0;

    constructor(private gl: WebGL2RenderingContext) {}

    add_polyline(points: Vec2[], width: number, r: number, g: number, b: number, a: number) {
        if (points.length < 2) return;
        this.#polyline_data.push(tessellate_polyline(points, width, r, g, b, a));
    }

    add_circle(cx: number, cy: number, radius: number, r: number, g: number, b: number, a: number) {
        this.#circle_data.push(tessellate_circle(cx, cy, radius, r, g, b, a));
    }

    add_polygon(points: Vec2[], r: number, g: number, b: number, a: number) {
        if (points.length < 3) return;
        this.#polygon_data.push(triangulate_polygon(points, r, g, b, a));
    }

    /** Upload all collected data to GPU */
    commit(polylineShader: ShaderProgram, polygonShader: ShaderProgram) {
        // Merge and upload polylines + circles (share the same shader)
        const lineItems = [...this.#polyline_data, ...this.#circle_data];
        if (lineItems.length > 0) {
            let totalVerts = 0;
            for (const item of lineItems) totalVerts += item.vertexCount;

            const pos = new Float32Array(totalVerts * 2);
            const cap = new Float32Array(totalVerts);
            const col = new Float32Array(totalVerts * 4);
            let pi = 0, ci = 0, coli = 0;

            for (const item of lineItems) {
                pos.set(item.positions, pi); pi += item.positions.length;
                cap.set(item.caps, ci); ci += item.caps.length;
                col.set(item.colors, coli); coli += item.colors.length;
            }

            this.#line_vao = new VertexArray(this.gl);
            this.#line_pos_buf = this.#line_vao.buffer(polylineShader.attribs["a_position"]!, 2);
            this.#line_pos_buf.set(pos);
            this.#line_cap_buf = this.#line_vao.buffer(polylineShader.attribs["a_cap_region"]!, 1);
            this.#line_cap_buf.set(cap);
            this.#line_color_buf = this.#line_vao.buffer(polylineShader.attribs["a_color"]!, 4);
            this.#line_color_buf.set(col);
            this.#line_vertex_count = totalVerts;
        }

        // Merge and upload polygons
        if (this.#polygon_data.length > 0) {
            let totalVerts = 0;
            for (const item of this.#polygon_data) totalVerts += item.vertexCount;

            const pos = new Float32Array(totalVerts * 2);
            const col = new Float32Array(totalVerts * 4);
            let pi = 0, coli = 0;

            for (const item of this.#polygon_data) {
                pos.set(item.positions, pi); pi += item.positions.length;
                col.set(item.colors, coli); coli += item.colors.length;
            }

            this.#poly_vao = new VertexArray(this.gl);
            this.#poly_pos_buf = this.#poly_vao.buffer(polygonShader.attribs["a_position"]!, 2);
            this.#poly_pos_buf.set(pos);
            this.#poly_color_buf = this.#poly_vao.buffer(polygonShader.attribs["a_color"]!, 4);
            this.#poly_color_buf.set(col);
            this.#poly_vertex_count = totalVerts;
        }

        // Free CPU data
        this.#polyline_data = [];
        this.#circle_data = [];
        this.#polygon_data = [];
    }

    render(polylineShader: ShaderProgram, polygonShader: ShaderProgram, matrix: Matrix3, depth: number, alpha: number) {
        if (this.#poly_vertex_count > 0) {
            polygonShader.bind();
            polygonShader.uniforms["u_matrix"]!.mat3f(false, matrix.elements);
            polygonShader.uniforms["u_depth"]!.f1(depth);
            polygonShader.uniforms["u_alpha"]!.f1(alpha);
            this.#poly_vao!.bind();
            this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#poly_vertex_count);
        }

        if (this.#line_vertex_count > 0) {
            polylineShader.bind();
            polylineShader.uniforms["u_matrix"]!.mat3f(false, matrix.elements);
            polylineShader.uniforms["u_depth"]!.f1(depth);
            polylineShader.uniforms["u_alpha"]!.f1(alpha);
            this.#line_vao!.bind();
            this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#line_vertex_count);
        }
    }

    dispose() {
        this.#poly_vao?.dispose();
        this.#line_vao?.dispose();
    }
}

/** A named render layer with its own PrimitiveSet */
export class RenderLayer {
    geometry: PrimitiveSet;
    depth: number;
    visible: boolean = true;
    transform: Matrix3 | null = null;

    constructor(
        private gl: WebGL2RenderingContext,
        public name: string,
        depth: number,
    ) {
        this.geometry = new PrimitiveSet(gl);
        this.depth = depth;
    }

    commit(polylineShader: ShaderProgram, polygonShader: ShaderProgram) {
        this.geometry.commit(polylineShader, polygonShader);
    }

    render(polylineShader: ShaderProgram, polygonShader: ShaderProgram, matrix: Matrix3, alpha = 1) {
        if (!this.visible) return;
        const m = this.transform ? matrix.multiply(this.transform) : matrix;
        this.geometry.render(polylineShader, polygonShader, m, this.depth, alpha);
    }

    dispose() {
        this.geometry.dispose();
    }
}

/** Retained-mode WebGL2 renderer */
export class Renderer {
    gl: WebGL2RenderingContext;
    canvas: HTMLCanvasElement;
    layers: Map<string, RenderLayer> = new Map();
    dynamicLayers: RenderLayer[] = [];
    dynamicLayersMap: Map<string, RenderLayer> = new Map();
    isDynamicContext: boolean = false;
    projection_matrix: Matrix3 = Matrix3.identity();

    private polylineShader!: ShaderProgram;
    private polygonShader!: ShaderProgram;
    private pointShader!: ShaderProgram;
    private blitShader!: ShaderProgram;
    private static readonly DEPTH_STEP = 0.0001;
    private static readonly DYNAMIC_DEPTH_LIFT = 0.2;
    private nextDepth = Renderer.DEPTH_STEP;
    private dynamicFallbackDepth = 0.8;
    private gridVao: VertexArray | null = null;
    private gridPosBuf: Buffer | null = null;
    private gridVertexCount = 0;
    private blitVao: VertexArray | null = null;
    private dragCacheTex: WebGLTexture | null = null;
    private dragCacheWidth = 0;
    private dragCacheHeight = 0;
    private useDragCache = false;

    constructor(canvas: HTMLCanvasElement) {
        this.canvas = canvas;
        const gl = canvas.getContext("webgl2", { alpha: false });
        if (!gl) throw new Error("WebGL2 not available");
        this.gl = gl;
    }

    setup() {
        const gl = this.gl;
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.enable(gl.DEPTH_TEST);
        gl.depthFunc(gl.GREATER);
        gl.clearColor(0.03, 0.05, 0.08, 1);
        gl.clearDepth(0);

        this.polylineShader = new ShaderProgram(gl, polyline_vert, polyline_frag);
        this.polygonShader = new ShaderProgram(gl, polygon_vert, polygon_frag);
        this.pointShader = new ShaderProgram(gl, point_vert, point_frag);
        this.blitShader = new ShaderProgram(gl, blit_vert, blit_frag);

        this.update_size();
    }

    update_size() {
        const dpr = window.devicePixelRatio;
        const rect = this.canvas.getBoundingClientRect();
        const pw = Math.round(rect.width * dpr);
        const ph = Math.round(rect.height * dpr);
        if (this.canvas.width === pw && this.canvas.height === ph) return;
        this.canvas.width = pw;
        this.canvas.height = ph;
        this.gl.viewport(0, 0, pw, ph);
        this.projection_matrix = Matrix3.orthographic(rect.width, rect.height);
        this.useDragCache = false;
        this.dragCacheWidth = 0;
        this.dragCacheHeight = 0;
    }

    clear() {
        this.update_size();
        this.gl.clear(this.gl.COLOR_BUFFER_BIT | this.gl.DEPTH_BUFFER_BIT);
    }

    /** Remove all layers and free GPU resources */
    dispose_layers() {
        for (const layer of this.layers.values()) layer.dispose();
        this.layers.clear();
        this.nextDepth = Renderer.DEPTH_STEP;
        this.dispose_dynamic_layers();
    }

    dispose_dynamic_layers() {
        for (const layer of this.dynamicLayers) layer.dispose();
        this.dynamicLayers = [];
        this.dynamicLayersMap.clear();
        this.dynamicFallbackDepth = 0.8;
    }

    dispose_dynamic_overlays() {
        const contextLayers = new Set(this.dynamicLayersMap.values());
        const remaining: RenderLayer[] = [];
        for (const layer of this.dynamicLayers) {
            if (contextLayers.has(layer)) {
                remaining.push(layer);
            } else {
                layer.dispose();
            }
        }
        this.dynamicLayers = remaining;
    }

    get_layer(name: string): RenderLayer {
        if (this.isDynamicContext) {
            let layer = this.dynamicLayersMap.get(name);
            if (!layer) {
                const staticDepth = this.layers.get(name)?.depth;
                const liftedDepth = staticDepth !== undefined
                    ? Math.min(0.9998, staticDepth + Renderer.DYNAMIC_DEPTH_LIFT)
                    : this.dynamicFallbackDepth;
                this.dynamicFallbackDepth = Math.min(0.9998, this.dynamicFallbackDepth + Renderer.DEPTH_STEP);
                layer = new RenderLayer(this.gl, "dyn_" + name, liftedDepth);
                this.dynamicLayersMap.set(name, layer);
                this.dynamicLayers.push(layer);
            }
            return layer;
        }
        let layer = this.layers.get(name);
        if (!layer) {
            layer = new RenderLayer(this.gl, name, this.nextDepth);
            this.nextDepth = Math.min(0.9999, this.nextDepth + Renderer.DEPTH_STEP);
            this.layers.set(name, layer);
        }
        return layer;
    }

    set_layer_visible(name: string, visible: boolean) {
        for (const [layerName, layer] of this.layers) {
            if (
                layerName === name
                || layerName === `zone:${name}`
            ) {
                layer.visible = visible;
            }
        }
    }

    set_layer_transform(name: string, transform: Matrix3 | null) {
        const layer = this.layers.get(name);
        if (layer) layer.transform = transform;
    }

    commit_all_layers() {
        for (const layer of this.layers.values()) {
            layer.commit(this.polylineShader, this.polygonShader);
        }
    }

    start_dynamic_layer(name: string): RenderLayer {
        const layer = new RenderLayer(this.gl, name, 1.0); // Draw on top
        this.dynamicLayers.push(layer);
        return layer;
    }

    commit_dynamic_layer(layer: RenderLayer) {
        layer.commit(this.polylineShader, this.polygonShader);
    }

    commit_dynamic_context_layers() {
        for (const layer of this.dynamicLayersMap.values()) {
            layer.commit(this.polylineShader, this.polygonShader);
        }
    }

    begin_fast_drag_cache() {
        this.update_size();
        const gl = this.gl;
        const w = this.canvas.width;
        const h = this.canvas.height;
        if (w <= 0 || h <= 0) {
            this.useDragCache = false;
            return;
        }
        if (!this.dragCacheTex) {
            this.dragCacheTex = gl.createTexture();
            if (!this.dragCacheTex) {
                this.useDragCache = false;
                return;
            }
        }
        gl.bindTexture(gl.TEXTURE_2D, this.dragCacheTex);
        if (this.dragCacheWidth !== w || this.dragCacheHeight !== h) {
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
            this.dragCacheWidth = w;
            this.dragCacheHeight = h;
        }
        gl.copyTexSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 0, 0, w, h);
        gl.bindTexture(gl.TEXTURE_2D, null);
        this.useDragCache = true;
    }

    end_fast_drag_cache() {
        this.useDragCache = false;
    }

    private ensure_blit_vao() {
        if (this.blitVao) return;
        const vao = new VertexArray(this.gl);
        const posBuf = vao.buffer(this.blitShader.attribs["a_position"]!, 2);
        posBuf.set(new Float32Array([
            -1, -1,
             1, -1,
            -1,  1,
            -1,  1,
             1, -1,
             1,  1,
        ]));
        const uvBuf = vao.buffer(this.blitShader.attribs["a_uv"]!, 2);
        uvBuf.set(new Float32Array([
            0, 0,
            1, 0,
            0, 1,
            0, 1,
            1, 0,
            1, 1,
        ]));
        this.blitVao = vao;
    }

    private draw_drag_cache() {
        if (!this.useDragCache || !this.dragCacheTex) return false;
        const gl = this.gl;
        this.ensure_blit_vao();
        gl.disable(gl.DEPTH_TEST);
        this.blitShader.bind();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.dragCacheTex);
        gl.uniform1i(gl.getUniformLocation(this.blitShader.program, "u_tex"), 0);
        this.blitVao!.bind();
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        gl.bindTexture(gl.TEXTURE_2D, null);
        gl.enable(gl.DEPTH_TEST);
        gl.clear(gl.DEPTH_BUFFER_BIT);
        return true;
    }

    /** Build grid vertex data for the visible area */
    updateGrid(viewBBox: BBox, spacing: number) {
        const maxDots = 100000;
        const cols = Math.floor(viewBBox.w / spacing) + 2;
        const rows = Math.floor(viewBBox.h / spacing) + 2;
        if (cols * rows > maxDots || cols <= 0 || rows <= 0) {
            this.gridVertexCount = 0;
            return;
        }

        const startX = Math.floor(viewBBox.x / spacing) * spacing;
        const startY = Math.floor(viewBBox.y / spacing) * spacing;
        const data = new Float32Array(cols * rows * 2);
        let i = 0;
        for (let r = 0; r < rows; r++) {
            const y = startY + r * spacing;
            for (let c = 0; c < cols; c++) {
                data[i++] = startX + c * spacing;
                data[i++] = y;
            }
        }

        if (!this.gridVao) {
            this.gridVao = new VertexArray(this.gl);
            this.gridPosBuf = this.gridVao.buffer(this.pointShader.attribs["a_position"]!, 2);
        }
        this.gridPosBuf!.set(data.subarray(0, i));
        this.gridVertexCount = i / 2;
    }

    /** Draw all layers with the given camera transform */
    draw(cameraMatrix: Matrix3) {
        this.clear();
        const total = this.projection_matrix.multiply(cameraMatrix);

        const drewCache = this.draw_drag_cache();
        if (!drewCache) {
            // Draw grid dots behind everything
            if (this.gridVertexCount > 0) {
                this.pointShader.bind();
                this.pointShader.uniforms["u_matrix"]!.mat3f(false, total.elements);
                this.pointShader.uniforms["u_pointSize"]!.f1(2.0 * window.devicePixelRatio);
                this.pointShader.uniforms["u_color"]!.f4(1.0, 1.0, 1.0, 0.15);
                this.gridVao!.bind();
                this.gl.drawArrays(this.gl.POINTS, 0, this.gridVertexCount);
            }

            for (const layer of this.layers.values()) {
                layer.render(this.polylineShader, this.polygonShader, total, 1.0);
            }
        }
        for (const layer of this.dynamicLayers) {
            layer.render(this.polylineShader, this.polygonShader, total, 1.0);
        }
    }
}

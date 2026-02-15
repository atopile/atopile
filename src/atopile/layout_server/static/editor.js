// src/math.ts
var Vec2 = class _Vec2 {
  x;
  y;
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
  }
  copy() {
    return new _Vec2(this.x, this.y);
  }
  *[Symbol.iterator]() {
    yield this.x;
    yield this.y;
  }
  get magnitude() {
    return Math.sqrt(this.x ** 2 + this.y ** 2);
  }
  get normal() {
    return new _Vec2(-this.y, this.x);
  }
  normalize() {
    const l = this.magnitude;
    if (l === 0)
      return new _Vec2(0, 0);
    return new _Vec2(this.x / l, this.y / l);
  }
  add(b) {
    return new _Vec2(this.x + b.x, this.y + b.y);
  }
  sub(b) {
    return new _Vec2(this.x - b.x, this.y - b.y);
  }
  multiply(s) {
    return new _Vec2(this.x * s, this.y * s);
  }
};
var Matrix3 = class _Matrix3 {
  elements;
  constructor(elements) {
    this.elements = new Float32Array(elements);
  }
  static identity() {
    return new _Matrix3([1, 0, 0, 0, 1, 0, 0, 0, 1]);
  }
  static orthographic(width, height) {
    return new _Matrix3([2 / width, 0, 0, 0, -2 / height, 0, -1, 1, 1]);
  }
  static translation(x, y) {
    return new _Matrix3([1, 0, 0, 0, 1, 0, x, y, 1]);
  }
  static scaling(x, y) {
    return new _Matrix3([x, 0, 0, 0, y, 0, 0, 0, 1]);
  }
  static rotation(radians) {
    const c = Math.cos(radians);
    const s = Math.sin(radians);
    return new _Matrix3([c, -s, 0, s, c, 0, 0, 0, 1]);
  }
  copy() {
    return new _Matrix3(this.elements);
  }
  transform(vec) {
    const e = this.elements;
    const x = vec.x * e[0] + vec.y * e[3] + e[6];
    const y = vec.x * e[1] + vec.y * e[4] + e[7];
    return new Vec2(x, y);
  }
  multiply_self(b) {
    const a = this.elements;
    const be = b.elements;
    const a00 = a[0], a01 = a[1], a02 = a[2];
    const a10 = a[3], a11 = a[4], a12 = a[5];
    const a20 = a[6], a21 = a[7], a22 = a[8];
    const b00 = be[0], b01 = be[1], b02 = be[2];
    const b10 = be[3], b11 = be[4], b12 = be[5];
    const b20 = be[6], b21 = be[7], b22 = be[8];
    a[0] = b00 * a00 + b01 * a10 + b02 * a20;
    a[1] = b00 * a01 + b01 * a11 + b02 * a21;
    a[2] = b00 * a02 + b01 * a12 + b02 * a22;
    a[3] = b10 * a00 + b11 * a10 + b12 * a20;
    a[4] = b10 * a01 + b11 * a11 + b12 * a21;
    a[5] = b10 * a02 + b11 * a12 + b12 * a22;
    a[6] = b20 * a00 + b21 * a10 + b22 * a20;
    a[7] = b20 * a01 + b21 * a11 + b22 * a21;
    a[8] = b20 * a02 + b21 * a12 + b22 * a22;
    return this;
  }
  multiply(b) {
    return this.copy().multiply_self(b);
  }
  translate_self(x, y) {
    return this.multiply_self(_Matrix3.translation(x, y));
  }
  scale_self(x, y) {
    return this.multiply_self(_Matrix3.scaling(x, y));
  }
  inverse() {
    const e = this.elements;
    const a00 = e[0], a01 = e[1], a02 = e[2];
    const a10 = e[3], a11 = e[4], a12 = e[5];
    const a20 = e[6], a21 = e[7], a22 = e[8];
    const b01 = a22 * a11 - a12 * a21;
    const b11 = -a22 * a10 + a12 * a20;
    const b21 = a21 * a10 - a11 * a20;
    const det = a00 * b01 + a01 * b11 + a02 * b21;
    const inv = 1 / det;
    return new _Matrix3([
      b01 * inv,
      (-a22 * a01 + a02 * a21) * inv,
      (a12 * a01 - a02 * a11) * inv,
      b11 * inv,
      (a22 * a00 - a02 * a20) * inv,
      (-a12 * a00 + a02 * a10) * inv,
      b21 * inv,
      (-a21 * a00 + a01 * a20) * inv,
      (a11 * a00 - a01 * a10) * inv
    ]);
  }
};
var BBox = class _BBox {
  constructor(x = 0, y = 0, w = 0, h = 0) {
    this.x = x;
    this.y = y;
    this.w = w;
    this.h = h;
    if (this.w < 0) {
      this.w *= -1;
      this.x -= this.w;
    }
    if (this.h < 0) {
      this.h *= -1;
      this.y -= this.h;
    }
  }
  get x2() {
    return this.x + this.w;
  }
  get y2() {
    return this.y + this.h;
  }
  get center() {
    return new Vec2(this.x + this.w / 2, this.y + this.h / 2);
  }
  static from_points(points) {
    if (points.length === 0)
      return new _BBox();
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of points) {
      if (p.x < minX)
        minX = p.x;
      if (p.y < minY)
        minY = p.y;
      if (p.x > maxX)
        maxX = p.x;
      if (p.y > maxY)
        maxY = p.y;
    }
    return new _BBox(minX, minY, maxX - minX, maxY - minY);
  }
  static combine(boxes) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const b of boxes) {
      if (b.w === 0 && b.h === 0)
        continue;
      if (b.x < minX)
        minX = b.x;
      if (b.y < minY)
        minY = b.y;
      if (b.x2 > maxX)
        maxX = b.x2;
      if (b.y2 > maxY)
        maxY = b.y2;
    }
    if (minX === Infinity)
      return new _BBox();
    return new _BBox(minX, minY, maxX - minX, maxY - minY);
  }
  contains_point(v) {
    return v.x >= this.x && v.x <= this.x2 && v.y >= this.y && v.y <= this.y2;
  }
  grow(d) {
    return new _BBox(this.x - d, this.y - d, this.w + d * 2, this.h + d * 2);
  }
};

// src/camera.ts
var Camera2 = class {
  viewport_size = new Vec2(0, 0);
  center = new Vec2(0, 0);
  zoom = 1;
  get matrix() {
    const mx = this.viewport_size.x / 2;
    const my = this.viewport_size.y / 2;
    const dx = this.center.x - this.center.x * this.zoom;
    const dy = this.center.y - this.center.y * this.zoom;
    const left = -(this.center.x - mx) + dx;
    const top = -(this.center.y - my) + dy;
    return Matrix3.identity().translate_self(left, top).scale_self(this.zoom, this.zoom);
  }
  get bbox() {
    const m = this.matrix.inverse();
    const start = m.transform(new Vec2(0, 0));
    const end = m.transform(new Vec2(this.viewport_size.x, this.viewport_size.y));
    return new BBox(start.x, start.y, end.x - start.x, end.y - start.y);
  }
  set bbox(bbox) {
    const zoom_w = this.viewport_size.x / bbox.w;
    const zoom_h = this.viewport_size.y / bbox.h;
    this.zoom = Math.min(zoom_w, zoom_h);
    this.center = bbox.center;
  }
  translate(delta) {
    this.center = this.center.add(delta);
  }
  screen_to_world(v) {
    return this.matrix.inverse().transform(v);
  }
  world_to_screen(v) {
    return this.matrix.transform(v);
  }
};

// src/pan-and-zoom.ts
var zoom_speed = 5e-3;
var pan_speed = 1;
var line_delta_multiplier = 8;
var page_delta_multiplier = 24;
var PanAndZoom = class {
  constructor(target, camera, callback, min_zoom = 0.1, max_zoom = 100) {
    this.target = target;
    this.camera = camera;
    this.callback = callback;
    this.min_zoom = min_zoom;
    this.max_zoom = max_zoom;
    this.target.addEventListener("wheel", (e) => this.#on_wheel(e), { passive: false });
    let dragStart = null;
    let dragging = false;
    this.target.addEventListener("mousedown", (e) => {
      if (e.button === 1 || e.button === 2) {
        e.preventDefault();
        dragging = true;
        dragStart = new Vec2(e.clientX, e.clientY);
      }
    });
    this.target.addEventListener("mousemove", (e) => {
      if (dragging && dragStart) {
        const cur = new Vec2(e.clientX, e.clientY);
        const delta = cur.sub(dragStart);
        this.#handle_pan(-delta.x, -delta.y);
        dragStart = cur;
      }
    });
    this.target.addEventListener("mouseup", (e) => {
      if (e.button === 1 || e.button === 2) {
        dragging = false;
        dragStart = null;
      }
    });
    this.target.addEventListener("contextmenu", (e) => e.preventDefault());
    let touchStart = null;
    let pinchDist = null;
    this.target.addEventListener("touchstart", (e) => {
      if (e.touches.length === 2) {
        pinchDist = this.#touchDistance(e.touches);
      } else if (e.touches.length === 1) {
        touchStart = e.touches;
      }
    });
    this.target.addEventListener("touchmove", (e) => {
      if (e.touches.length === 2 && pinchDist !== null) {
        const cur = this.#touchDistance(e.touches);
        const scale = cur / pinchDist * 4;
        this.#handle_zoom(pinchDist < cur ? -scale : scale);
        pinchDist = cur;
      } else if (e.touches.length === 1 && touchStart !== null) {
        const sx = touchStart[0].clientX, sy = touchStart[0].clientY;
        const ex = e.touches[0].clientX, ey = e.touches[0].clientY;
        this.#handle_pan(sx - ex, sy - ey);
        touchStart = e.touches;
      }
    });
    this.target.addEventListener("touchend", () => {
      pinchDist = null;
      touchStart = null;
    });
  }
  #touchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }
  #on_wheel(e) {
    e.preventDefault();
    let dy = e.deltaY;
    if (e.deltaMode === WheelEvent.DOM_DELTA_LINE)
      dy *= line_delta_multiplier;
    else if (e.deltaMode === WheelEvent.DOM_DELTA_PAGE)
      dy *= page_delta_multiplier;
    dy = Math.sign(dy) * Math.min(page_delta_multiplier, Math.abs(dy));
    if (e.ctrlKey || e.shiftKey) {
      let dx = e.deltaX;
      if (e.deltaMode === WheelEvent.DOM_DELTA_LINE)
        dx *= line_delta_multiplier;
      dx = Math.sign(dx) * Math.min(page_delta_multiplier, Math.abs(dx));
      this.#handle_pan(dx, dy);
    } else {
      const rect = this.target.getBoundingClientRect();
      const mouse = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
      this.#handle_zoom(dy, mouse);
    }
  }
  #handle_pan(dx, dy) {
    const delta = new Vec2(dx * pan_speed, dy * pan_speed).multiply(1 / this.camera.zoom);
    this.camera.translate(delta);
    this.callback();
  }
  #handle_zoom(delta, mouse) {
    const worldBefore = mouse ? this.camera.screen_to_world(mouse) : null;
    this.camera.zoom *= Math.exp(delta * -zoom_speed);
    this.camera.zoom = Math.min(this.max_zoom, Math.max(this.camera.zoom, this.min_zoom));
    if (worldBefore && mouse) {
      const worldAfter = this.camera.screen_to_world(mouse);
      this.camera.translate(worldBefore.sub(worldAfter));
    }
    this.callback();
  }
};

// src/webgl/helpers.ts
var Uniform = class {
  constructor(gl, name, location) {
    this.gl = gl;
    this.name = name;
    this.location = location;
  }
  f1(x) {
    this.gl.uniform1f(this.location, x);
  }
  mat3f(transpose, data) {
    this.gl.uniformMatrix3fv(this.location, transpose, data);
  }
};
var ShaderProgram = class _ShaderProgram {
  constructor(gl, vert_src, frag_src) {
    this.gl = gl;
    const vert = _ShaderProgram.compile(gl, gl.VERTEX_SHADER, vert_src);
    const frag = _ShaderProgram.compile(gl, gl.FRAGMENT_SHADER, frag_src);
    this.program = _ShaderProgram.link(gl, vert, frag);
    this.#discover_uniforms();
    this.#discover_attribs();
  }
  program;
  uniforms = {};
  attribs = {};
  static compile(gl, type, src) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const info = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compile error: ${info}`);
    }
    return shader;
  }
  static link(gl, vert, frag) {
    const prog = gl.createProgram();
    gl.attachShader(prog, vert);
    gl.attachShader(prog, frag);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      const info = gl.getProgramInfoLog(prog);
      gl.deleteProgram(prog);
      throw new Error(`Shader link error: ${info}`);
    }
    return prog;
  }
  #discover_uniforms() {
    const count = this.gl.getProgramParameter(this.program, this.gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < count; i++) {
      const info = this.gl.getActiveUniform(this.program, i);
      const loc = this.gl.getUniformLocation(this.program, info.name);
      this.uniforms[info.name] = new Uniform(this.gl, info.name, loc);
    }
  }
  #discover_attribs() {
    const count = this.gl.getProgramParameter(this.program, this.gl.ACTIVE_ATTRIBUTES);
    for (let i = 0; i < count; i++) {
      const info = this.gl.getActiveAttrib(this.program, i);
      this.attribs[info.name] = this.gl.getAttribLocation(this.program, info.name);
    }
  }
  bind() {
    this.gl.useProgram(this.program);
  }
};
var Buffer = class {
  constructor(gl, target) {
    this.gl = gl;
    this.target = target ?? gl.ARRAY_BUFFER;
    this.#buf = gl.createBuffer();
  }
  #buf;
  target;
  dispose() {
    this.gl.deleteBuffer(this.#buf);
  }
  bind() {
    this.gl.bindBuffer(this.target, this.#buf);
  }
  set(data, usage) {
    this.bind();
    this.gl.bufferData(this.target, data, usage ?? this.gl.STATIC_DRAW);
  }
};
var VertexArray = class {
  constructor(gl) {
    this.gl = gl;
    this.vao = gl.createVertexArray();
    this.bind();
  }
  vao;
  buffers = [];
  dispose() {
    this.gl.deleteVertexArray(this.vao);
    for (const buf of this.buffers)
      buf.dispose();
  }
  bind() {
    this.gl.bindVertexArray(this.vao);
  }
  buffer(attrib, size) {
    const b = new Buffer(this.gl);
    b.bind();
    this.gl.vertexAttribPointer(attrib, size, this.gl.FLOAT, false, 0, 0);
    this.gl.enableVertexAttribArray(attrib);
    this.buffers.push(b);
    return b;
  }
};

// src/webgl/shaders.ts
var polygon_vert = `#version 300 es
uniform mat3 u_matrix;
in vec2 a_position;
in vec4 a_color;
out vec4 v_color;
void main() {
    v_color = a_color;
    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);
}`;
var polygon_frag = `#version 300 es
precision highp float;
uniform float u_depth;
uniform float u_alpha;
in vec4 v_color;
out vec4 o_color;
void main() {
    vec4 c = v_color;
    c.a *= u_alpha;
    o_color = c;
    gl_FragDepth = u_depth;
}`;
var polyline_vert = `#version 300 es
uniform mat3 u_matrix;
in vec2 a_position;
in vec4 a_color;
in float a_cap_region;
out vec2 v_linespace;
out float v_cap_region;
out vec4 v_color;
vec2 c_linespace[6] = vec2[](
    vec2(-1, -1), vec2( 1, -1), vec2(-1,  1),
    vec2(-1,  1), vec2( 1, -1), vec2( 1,  1)
);
void main() {
    int vi = int(gl_VertexID % 6);
    v_linespace = c_linespace[vi];
    v_cap_region = a_cap_region;
    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);
    v_color = a_color;
}`;
var polyline_frag = `#version 300 es
precision highp float;
uniform float u_depth;
uniform float u_alpha;
in vec2 v_linespace;
in float v_cap_region;
in vec4 v_color;
out vec4 outColor;
void main() {
    vec4 c = v_color;
    c.a *= u_alpha;
    float x = v_linespace.x;
    float y = v_linespace.y;
    if(x < (-1.0 + v_cap_region)) {
        float a = (1.0 + x) / v_cap_region;
        x = mix(-1.0, 0.0, a);
        if(x*x + y*y >= 1.0) discard;
    } else if (x > (1.0 - v_cap_region)) {
        float a = (x - (1.0 - v_cap_region)) / v_cap_region;
        x = mix(0.0, 1.0, a);
        if(x*x + y*y >= 1.0) discard;
    }
    outColor = c;
    gl_FragDepth = u_depth;
}`;

// node_modules/earcut/src/earcut.js
function earcut(data, holeIndices, dim = 2) {
  const hasHoles = holeIndices && holeIndices.length;
  const outerLen = hasHoles ? holeIndices[0] * dim : data.length;
  let outerNode = linkedList(data, 0, outerLen, dim, true);
  const triangles = [];
  if (!outerNode || outerNode.next === outerNode.prev)
    return triangles;
  let minX, minY, invSize;
  if (hasHoles)
    outerNode = eliminateHoles(data, holeIndices, outerNode, dim);
  if (data.length > 80 * dim) {
    minX = data[0];
    minY = data[1];
    let maxX = minX;
    let maxY = minY;
    for (let i = dim; i < outerLen; i += dim) {
      const x = data[i];
      const y = data[i + 1];
      if (x < minX)
        minX = x;
      if (y < minY)
        minY = y;
      if (x > maxX)
        maxX = x;
      if (y > maxY)
        maxY = y;
    }
    invSize = Math.max(maxX - minX, maxY - minY);
    invSize = invSize !== 0 ? 32767 / invSize : 0;
  }
  earcutLinked(outerNode, triangles, dim, minX, minY, invSize, 0);
  return triangles;
}
function linkedList(data, start, end, dim, clockwise) {
  let last;
  if (clockwise === signedArea(data, start, end, dim) > 0) {
    for (let i = start; i < end; i += dim)
      last = insertNode(i / dim | 0, data[i], data[i + 1], last);
  } else {
    for (let i = end - dim; i >= start; i -= dim)
      last = insertNode(i / dim | 0, data[i], data[i + 1], last);
  }
  if (last && equals(last, last.next)) {
    removeNode(last);
    last = last.next;
  }
  return last;
}
function filterPoints(start, end) {
  if (!start)
    return start;
  if (!end)
    end = start;
  let p = start, again;
  do {
    again = false;
    if (!p.steiner && (equals(p, p.next) || area(p.prev, p, p.next) === 0)) {
      removeNode(p);
      p = end = p.prev;
      if (p === p.next)
        break;
      again = true;
    } else {
      p = p.next;
    }
  } while (again || p !== end);
  return end;
}
function earcutLinked(ear, triangles, dim, minX, minY, invSize, pass) {
  if (!ear)
    return;
  if (!pass && invSize)
    indexCurve(ear, minX, minY, invSize);
  let stop = ear;
  while (ear.prev !== ear.next) {
    const prev = ear.prev;
    const next = ear.next;
    if (invSize ? isEarHashed(ear, minX, minY, invSize) : isEar(ear)) {
      triangles.push(prev.i, ear.i, next.i);
      removeNode(ear);
      ear = next.next;
      stop = next.next;
      continue;
    }
    ear = next;
    if (ear === stop) {
      if (!pass) {
        earcutLinked(filterPoints(ear), triangles, dim, minX, minY, invSize, 1);
      } else if (pass === 1) {
        ear = cureLocalIntersections(filterPoints(ear), triangles);
        earcutLinked(ear, triangles, dim, minX, minY, invSize, 2);
      } else if (pass === 2) {
        splitEarcut(ear, triangles, dim, minX, minY, invSize);
      }
      break;
    }
  }
}
function isEar(ear) {
  const a = ear.prev, b = ear, c = ear.next;
  if (area(a, b, c) >= 0)
    return false;
  const ax = a.x, bx = b.x, cx = c.x, ay = a.y, by = b.y, cy = c.y;
  const x0 = Math.min(ax, bx, cx), y0 = Math.min(ay, by, cy), x1 = Math.max(ax, bx, cx), y1 = Math.max(ay, by, cy);
  let p = c.next;
  while (p !== a) {
    if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1 && pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, p.x, p.y) && area(p.prev, p, p.next) >= 0)
      return false;
    p = p.next;
  }
  return true;
}
function isEarHashed(ear, minX, minY, invSize) {
  const a = ear.prev, b = ear, c = ear.next;
  if (area(a, b, c) >= 0)
    return false;
  const ax = a.x, bx = b.x, cx = c.x, ay = a.y, by = b.y, cy = c.y;
  const x0 = Math.min(ax, bx, cx), y0 = Math.min(ay, by, cy), x1 = Math.max(ax, bx, cx), y1 = Math.max(ay, by, cy);
  const minZ = zOrder(x0, y0, minX, minY, invSize), maxZ = zOrder(x1, y1, minX, minY, invSize);
  let p = ear.prevZ, n = ear.nextZ;
  while (p && p.z >= minZ && n && n.z <= maxZ) {
    if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1 && p !== a && p !== c && pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, p.x, p.y) && area(p.prev, p, p.next) >= 0)
      return false;
    p = p.prevZ;
    if (n.x >= x0 && n.x <= x1 && n.y >= y0 && n.y <= y1 && n !== a && n !== c && pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, n.x, n.y) && area(n.prev, n, n.next) >= 0)
      return false;
    n = n.nextZ;
  }
  while (p && p.z >= minZ) {
    if (p.x >= x0 && p.x <= x1 && p.y >= y0 && p.y <= y1 && p !== a && p !== c && pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, p.x, p.y) && area(p.prev, p, p.next) >= 0)
      return false;
    p = p.prevZ;
  }
  while (n && n.z <= maxZ) {
    if (n.x >= x0 && n.x <= x1 && n.y >= y0 && n.y <= y1 && n !== a && n !== c && pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, n.x, n.y) && area(n.prev, n, n.next) >= 0)
      return false;
    n = n.nextZ;
  }
  return true;
}
function cureLocalIntersections(start, triangles) {
  let p = start;
  do {
    const a = p.prev, b = p.next.next;
    if (!equals(a, b) && intersects(a, p, p.next, b) && locallyInside(a, b) && locallyInside(b, a)) {
      triangles.push(a.i, p.i, b.i);
      removeNode(p);
      removeNode(p.next);
      p = start = b;
    }
    p = p.next;
  } while (p !== start);
  return filterPoints(p);
}
function splitEarcut(start, triangles, dim, minX, minY, invSize) {
  let a = start;
  do {
    let b = a.next.next;
    while (b !== a.prev) {
      if (a.i !== b.i && isValidDiagonal(a, b)) {
        let c = splitPolygon(a, b);
        a = filterPoints(a, a.next);
        c = filterPoints(c, c.next);
        earcutLinked(a, triangles, dim, minX, minY, invSize, 0);
        earcutLinked(c, triangles, dim, minX, minY, invSize, 0);
        return;
      }
      b = b.next;
    }
    a = a.next;
  } while (a !== start);
}
function eliminateHoles(data, holeIndices, outerNode, dim) {
  const queue = [];
  for (let i = 0, len = holeIndices.length; i < len; i++) {
    const start = holeIndices[i] * dim;
    const end = i < len - 1 ? holeIndices[i + 1] * dim : data.length;
    const list = linkedList(data, start, end, dim, false);
    if (list === list.next)
      list.steiner = true;
    queue.push(getLeftmost(list));
  }
  queue.sort(compareXYSlope);
  for (let i = 0; i < queue.length; i++) {
    outerNode = eliminateHole(queue[i], outerNode);
  }
  return outerNode;
}
function compareXYSlope(a, b) {
  let result = a.x - b.x;
  if (result === 0) {
    result = a.y - b.y;
    if (result === 0) {
      const aSlope = (a.next.y - a.y) / (a.next.x - a.x);
      const bSlope = (b.next.y - b.y) / (b.next.x - b.x);
      result = aSlope - bSlope;
    }
  }
  return result;
}
function eliminateHole(hole, outerNode) {
  const bridge = findHoleBridge(hole, outerNode);
  if (!bridge) {
    return outerNode;
  }
  const bridgeReverse = splitPolygon(bridge, hole);
  filterPoints(bridgeReverse, bridgeReverse.next);
  return filterPoints(bridge, bridge.next);
}
function findHoleBridge(hole, outerNode) {
  let p = outerNode;
  const hx = hole.x;
  const hy = hole.y;
  let qx = -Infinity;
  let m;
  if (equals(hole, p))
    return p;
  do {
    if (equals(hole, p.next))
      return p.next;
    else if (hy <= p.y && hy >= p.next.y && p.next.y !== p.y) {
      const x = p.x + (hy - p.y) * (p.next.x - p.x) / (p.next.y - p.y);
      if (x <= hx && x > qx) {
        qx = x;
        m = p.x < p.next.x ? p : p.next;
        if (x === hx)
          return m;
      }
    }
    p = p.next;
  } while (p !== outerNode);
  if (!m)
    return null;
  const stop = m;
  const mx = m.x;
  const my = m.y;
  let tanMin = Infinity;
  p = m;
  do {
    if (hx >= p.x && p.x >= mx && hx !== p.x && pointInTriangle(hy < my ? hx : qx, hy, mx, my, hy < my ? qx : hx, hy, p.x, p.y)) {
      const tan = Math.abs(hy - p.y) / (hx - p.x);
      if (locallyInside(p, hole) && (tan < tanMin || tan === tanMin && (p.x > m.x || p.x === m.x && sectorContainsSector(m, p)))) {
        m = p;
        tanMin = tan;
      }
    }
    p = p.next;
  } while (p !== stop);
  return m;
}
function sectorContainsSector(m, p) {
  return area(m.prev, m, p.prev) < 0 && area(p.next, m, m.next) < 0;
}
function indexCurve(start, minX, minY, invSize) {
  let p = start;
  do {
    if (p.z === 0)
      p.z = zOrder(p.x, p.y, minX, minY, invSize);
    p.prevZ = p.prev;
    p.nextZ = p.next;
    p = p.next;
  } while (p !== start);
  p.prevZ.nextZ = null;
  p.prevZ = null;
  sortLinked(p);
}
function sortLinked(list) {
  let numMerges;
  let inSize = 1;
  do {
    let p = list;
    let e;
    list = null;
    let tail = null;
    numMerges = 0;
    while (p) {
      numMerges++;
      let q = p;
      let pSize = 0;
      for (let i = 0; i < inSize; i++) {
        pSize++;
        q = q.nextZ;
        if (!q)
          break;
      }
      let qSize = inSize;
      while (pSize > 0 || qSize > 0 && q) {
        if (pSize !== 0 && (qSize === 0 || !q || p.z <= q.z)) {
          e = p;
          p = p.nextZ;
          pSize--;
        } else {
          e = q;
          q = q.nextZ;
          qSize--;
        }
        if (tail)
          tail.nextZ = e;
        else
          list = e;
        e.prevZ = tail;
        tail = e;
      }
      p = q;
    }
    tail.nextZ = null;
    inSize *= 2;
  } while (numMerges > 1);
  return list;
}
function zOrder(x, y, minX, minY, invSize) {
  x = (x - minX) * invSize | 0;
  y = (y - minY) * invSize | 0;
  x = (x | x << 8) & 16711935;
  x = (x | x << 4) & 252645135;
  x = (x | x << 2) & 858993459;
  x = (x | x << 1) & 1431655765;
  y = (y | y << 8) & 16711935;
  y = (y | y << 4) & 252645135;
  y = (y | y << 2) & 858993459;
  y = (y | y << 1) & 1431655765;
  return x | y << 1;
}
function getLeftmost(start) {
  let p = start, leftmost = start;
  do {
    if (p.x < leftmost.x || p.x === leftmost.x && p.y < leftmost.y)
      leftmost = p;
    p = p.next;
  } while (p !== start);
  return leftmost;
}
function pointInTriangle(ax, ay, bx, by, cx, cy, px, py) {
  return (cx - px) * (ay - py) >= (ax - px) * (cy - py) && (ax - px) * (by - py) >= (bx - px) * (ay - py) && (bx - px) * (cy - py) >= (cx - px) * (by - py);
}
function pointInTriangleExceptFirst(ax, ay, bx, by, cx, cy, px, py) {
  return !(ax === px && ay === py) && pointInTriangle(ax, ay, bx, by, cx, cy, px, py);
}
function isValidDiagonal(a, b) {
  return a.next.i !== b.i && a.prev.i !== b.i && !intersectsPolygon(a, b) && // doesn't intersect other edges
  (locallyInside(a, b) && locallyInside(b, a) && middleInside(a, b) && // locally visible
  (area(a.prev, a, b.prev) || area(a, b.prev, b)) || // does not create opposite-facing sectors
  equals(a, b) && area(a.prev, a, a.next) > 0 && area(b.prev, b, b.next) > 0);
}
function area(p, q, r) {
  return (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
}
function equals(p1, p2) {
  return p1.x === p2.x && p1.y === p2.y;
}
function intersects(p1, q1, p2, q2) {
  const o1 = sign(area(p1, q1, p2));
  const o2 = sign(area(p1, q1, q2));
  const o3 = sign(area(p2, q2, p1));
  const o4 = sign(area(p2, q2, q1));
  if (o1 !== o2 && o3 !== o4)
    return true;
  if (o1 === 0 && onSegment(p1, p2, q1))
    return true;
  if (o2 === 0 && onSegment(p1, q2, q1))
    return true;
  if (o3 === 0 && onSegment(p2, p1, q2))
    return true;
  if (o4 === 0 && onSegment(p2, q1, q2))
    return true;
  return false;
}
function onSegment(p, q, r) {
  return q.x <= Math.max(p.x, r.x) && q.x >= Math.min(p.x, r.x) && q.y <= Math.max(p.y, r.y) && q.y >= Math.min(p.y, r.y);
}
function sign(num) {
  return num > 0 ? 1 : num < 0 ? -1 : 0;
}
function intersectsPolygon(a, b) {
  let p = a;
  do {
    if (p.i !== a.i && p.next.i !== a.i && p.i !== b.i && p.next.i !== b.i && intersects(p, p.next, a, b))
      return true;
    p = p.next;
  } while (p !== a);
  return false;
}
function locallyInside(a, b) {
  return area(a.prev, a, a.next) < 0 ? area(a, b, a.next) >= 0 && area(a, a.prev, b) >= 0 : area(a, b, a.prev) < 0 || area(a, a.next, b) < 0;
}
function middleInside(a, b) {
  let p = a;
  let inside = false;
  const px = (a.x + b.x) / 2;
  const py = (a.y + b.y) / 2;
  do {
    if (p.y > py !== p.next.y > py && p.next.y !== p.y && px < (p.next.x - p.x) * (py - p.y) / (p.next.y - p.y) + p.x)
      inside = !inside;
    p = p.next;
  } while (p !== a);
  return inside;
}
function splitPolygon(a, b) {
  const a2 = createNode(a.i, a.x, a.y), b2 = createNode(b.i, b.x, b.y), an = a.next, bp = b.prev;
  a.next = b;
  b.prev = a;
  a2.next = an;
  an.prev = a2;
  b2.next = a2;
  a2.prev = b2;
  bp.next = b2;
  b2.prev = bp;
  return b2;
}
function insertNode(i, x, y, last) {
  const p = createNode(i, x, y);
  if (!last) {
    p.prev = p;
    p.next = p;
  } else {
    p.next = last.next;
    p.prev = last;
    last.next.prev = p;
    last.next = p;
  }
  return p;
}
function removeNode(p) {
  p.next.prev = p.prev;
  p.prev.next = p.next;
  if (p.prevZ)
    p.prevZ.nextZ = p.nextZ;
  if (p.nextZ)
    p.nextZ.prevZ = p.prevZ;
}
function createNode(i, x, y) {
  return {
    i,
    // vertex index in coordinates array
    x,
    y,
    // vertex coordinates
    prev: null,
    // previous and next vertex nodes in a polygon ring
    next: null,
    z: 0,
    // z-order curve value
    prevZ: null,
    // previous and next nodes in z-order
    nextZ: null,
    steiner: false
    // indicates whether this is a steiner point
  };
}
function signedArea(data, start, end, dim) {
  let sum = 0;
  for (let i = start, j = end - dim; i < end; i += dim) {
    sum += (data[j] - data[i]) * (data[i + 1] + data[j + 1]);
    j = i;
  }
  return sum;
}

// src/webgl/tessellator.ts
var VERTS_PER_QUAD = 6;
function quad_to_triangles(a, b, c, d) {
  return [a.x, a.y, c.x, c.y, b.x, b.y, b.x, b.y, c.x, c.y, d.x, d.y];
}
function fill_color(dest, r, g, b, a, offset, count) {
  for (let i = 0; i < count; i++) {
    dest[offset + i * 4] = r;
    dest[offset + i * 4 + 1] = g;
    dest[offset + i * 4 + 2] = b;
    dest[offset + i * 4 + 3] = a;
  }
}
function tessellate_polyline(points, width, r, g, b, a) {
  const segCount = points.length - 1;
  const maxVerts = segCount * VERTS_PER_QUAD;
  const positions = new Float32Array(maxVerts * 2);
  const caps = new Float32Array(maxVerts);
  const colors = new Float32Array(maxVerts * 4);
  let vi = 0;
  for (let i = 1; i < points.length; i++) {
    const p1 = points[i - 1];
    const p2 = points[i];
    const line = p2.sub(p1);
    const len = line.magnitude;
    if (len === 0)
      continue;
    const norm = line.normal.normalize();
    const n = norm.multiply(width / 2);
    const n2 = n.normal;
    const qa = p1.add(n).add(n2);
    const qb = p1.sub(n).add(n2);
    const qc = p2.add(n).sub(n2);
    const qd = p2.sub(n).sub(n2);
    const cap_region = width / (len + width);
    positions.set(quad_to_triangles(qa, qb, qc, qd), vi * 2);
    for (let j = 0; j < VERTS_PER_QUAD; j++)
      caps[vi + j] = cap_region;
    fill_color(colors, r, g, b, a, vi * 4, VERTS_PER_QUAD);
    vi += VERTS_PER_QUAD;
  }
  return {
    positions: positions.subarray(0, vi * 2),
    caps: caps.subarray(0, vi),
    colors: colors.subarray(0, vi * 4),
    vertexCount: vi
  };
}
function tessellate_circle(cx, cy, radius, r, g, b, a) {
  const positions = new Float32Array(VERTS_PER_QUAD * 2);
  const caps = new Float32Array(VERTS_PER_QUAD);
  const colors = new Float32Array(VERTS_PER_QUAD * 4);
  const n = new Vec2(radius, 0);
  const n2 = n.normal;
  const c = new Vec2(cx, cy);
  const qa = c.add(n).add(n2);
  const qb = c.sub(n).add(n2);
  const qc = c.add(n).sub(n2);
  const qd = c.sub(n).sub(n2);
  positions.set(quad_to_triangles(qa, qb, qc, qd), 0);
  for (let i = 0; i < VERTS_PER_QUAD; i++)
    caps[i] = 1;
  fill_color(colors, r, g, b, a, 0, VERTS_PER_QUAD);
  return { positions, caps, colors, vertexCount: VERTS_PER_QUAD };
}
function triangulate_polygon(points, r, g, b, a) {
  const flat = new Array(points.length * 2);
  for (let i = 0; i < points.length; i++) {
    flat[i * 2] = points[i].x;
    flat[i * 2 + 1] = points[i].y;
  }
  const indices = earcut(flat);
  const positions = new Float32Array(indices.length * 2);
  for (let i = 0; i < indices.length; i++) {
    positions[i * 2] = flat[indices[i] * 2];
    positions[i * 2 + 1] = flat[indices[i] * 2 + 1];
  }
  const vertexCount = indices.length;
  const colors = new Float32Array(vertexCount * 4);
  fill_color(colors, r, g, b, a, 0, vertexCount);
  return { positions, colors, vertexCount };
}

// src/webgl/renderer.ts
var PrimitiveSet = class {
  constructor(gl) {
    this.gl = gl;
  }
  #polyline_data = [];
  #circle_data = [];
  #polygon_data = [];
  // committed GPU state
  #poly_vao;
  #poly_pos_buf;
  #poly_color_buf;
  #poly_vertex_count = 0;
  #line_vao;
  #line_pos_buf;
  #line_cap_buf;
  #line_color_buf;
  #line_vertex_count = 0;
  add_polyline(points, width, r, g, b, a) {
    if (points.length < 2)
      return;
    this.#polyline_data.push(tessellate_polyline(points, width, r, g, b, a));
  }
  add_circle(cx, cy, radius, r, g, b, a) {
    this.#circle_data.push(tessellate_circle(cx, cy, radius, r, g, b, a));
  }
  add_polygon(points, r, g, b, a) {
    if (points.length < 3)
      return;
    this.#polygon_data.push(triangulate_polygon(points, r, g, b, a));
  }
  /** Upload all collected data to GPU */
  commit(polylineShader, polygonShader) {
    const lineItems = [...this.#polyline_data, ...this.#circle_data];
    if (lineItems.length > 0) {
      let totalVerts = 0;
      for (const item of lineItems)
        totalVerts += item.vertexCount;
      const pos = new Float32Array(totalVerts * 2);
      const cap = new Float32Array(totalVerts);
      const col = new Float32Array(totalVerts * 4);
      let pi = 0, ci = 0, coli = 0;
      for (const item of lineItems) {
        pos.set(item.positions, pi);
        pi += item.positions.length;
        cap.set(item.caps, ci);
        ci += item.caps.length;
        col.set(item.colors, coli);
        coli += item.colors.length;
      }
      this.#line_vao = new VertexArray(this.gl);
      this.#line_pos_buf = this.#line_vao.buffer(polylineShader.attribs["a_position"], 2);
      this.#line_pos_buf.set(pos);
      this.#line_cap_buf = this.#line_vao.buffer(polylineShader.attribs["a_cap_region"], 1);
      this.#line_cap_buf.set(cap);
      this.#line_color_buf = this.#line_vao.buffer(polylineShader.attribs["a_color"], 4);
      this.#line_color_buf.set(col);
      this.#line_vertex_count = totalVerts;
    }
    if (this.#polygon_data.length > 0) {
      let totalVerts = 0;
      for (const item of this.#polygon_data)
        totalVerts += item.vertexCount;
      const pos = new Float32Array(totalVerts * 2);
      const col = new Float32Array(totalVerts * 4);
      let pi = 0, coli = 0;
      for (const item of this.#polygon_data) {
        pos.set(item.positions, pi);
        pi += item.positions.length;
        col.set(item.colors, coli);
        coli += item.colors.length;
      }
      this.#poly_vao = new VertexArray(this.gl);
      this.#poly_pos_buf = this.#poly_vao.buffer(polygonShader.attribs["a_position"], 2);
      this.#poly_pos_buf.set(pos);
      this.#poly_color_buf = this.#poly_vao.buffer(polygonShader.attribs["a_color"], 4);
      this.#poly_color_buf.set(col);
      this.#poly_vertex_count = totalVerts;
    }
    this.#polyline_data = [];
    this.#circle_data = [];
    this.#polygon_data = [];
  }
  render(polylineShader, polygonShader, matrix, depth, alpha) {
    if (this.#poly_vertex_count > 0) {
      polygonShader.bind();
      polygonShader.uniforms["u_matrix"].mat3f(false, matrix.elements);
      polygonShader.uniforms["u_depth"].f1(depth);
      polygonShader.uniforms["u_alpha"].f1(alpha);
      this.#poly_vao.bind();
      this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#poly_vertex_count);
    }
    if (this.#line_vertex_count > 0) {
      polylineShader.bind();
      polylineShader.uniforms["u_matrix"].mat3f(false, matrix.elements);
      polylineShader.uniforms["u_depth"].f1(depth);
      polylineShader.uniforms["u_alpha"].f1(alpha);
      this.#line_vao.bind();
      this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#line_vertex_count);
    }
  }
  dispose() {
    this.#poly_vao?.dispose();
    this.#line_vao?.dispose();
  }
};
var RenderLayer = class {
  constructor(gl, name, depth) {
    this.gl = gl;
    this.name = name;
    this.geometry = new PrimitiveSet(gl);
    this.depth = depth;
  }
  geometry;
  depth;
  commit(polylineShader, polygonShader) {
    this.geometry.commit(polylineShader, polygonShader);
  }
  render(polylineShader, polygonShader, matrix, alpha = 1) {
    this.geometry.render(polylineShader, polygonShader, matrix, this.depth, alpha);
  }
  dispose() {
    this.geometry.dispose();
  }
};
var Renderer = class {
  gl;
  canvas;
  layers = [];
  projection_matrix = Matrix3.identity();
  polylineShader;
  polygonShader;
  activeLayer = null;
  nextDepth = 0.01;
  constructor(canvas2) {
    this.canvas = canvas2;
    const gl = canvas2.getContext("webgl2", { alpha: false });
    if (!gl)
      throw new Error("WebGL2 not available");
    this.gl = gl;
  }
  setup() {
    const gl = this.gl;
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.GREATER);
    gl.clearColor(0.12, 0.12, 0.12, 1);
    gl.clearDepth(0);
    this.polylineShader = new ShaderProgram(gl, polyline_vert, polyline_frag);
    this.polygonShader = new ShaderProgram(gl, polygon_vert, polygon_frag);
    this.update_size();
  }
  update_size() {
    const dpr = window.devicePixelRatio;
    const rect = this.canvas.getBoundingClientRect();
    const pw = Math.round(rect.width * dpr);
    const ph = Math.round(rect.height * dpr);
    if (this.canvas.width === pw && this.canvas.height === ph)
      return;
    this.canvas.width = pw;
    this.canvas.height = ph;
    this.gl.viewport(0, 0, pw, ph);
    this.projection_matrix = Matrix3.orthographic(rect.width, rect.height);
  }
  clear() {
    this.update_size();
    this.gl.clear(this.gl.COLOR_BUFFER_BIT | this.gl.DEPTH_BUFFER_BIT);
  }
  /** Remove all layers and free GPU resources */
  dispose_layers() {
    for (const layer of this.layers)
      layer.dispose();
    this.layers = [];
    this.nextDepth = 0.01;
  }
  start_layer(name) {
    const layer = new RenderLayer(this.gl, name, this.nextDepth);
    this.nextDepth += 0.01;
    this.activeLayer = layer;
    return layer;
  }
  end_layer() {
    if (!this.activeLayer)
      throw new Error("No active layer");
    this.activeLayer.commit(this.polylineShader, this.polygonShader);
    this.layers.push(this.activeLayer);
    const l = this.activeLayer;
    this.activeLayer = null;
    return l;
  }
  /** Get current active layer's PrimitiveSet for drawing */
  get active() {
    return this.activeLayer.geometry;
  }
  /** Draw all layers with the given camera transform */
  draw(cameraMatrix) {
    this.clear();
    const total = this.projection_matrix.multiply(cameraMatrix);
    for (const layer of this.layers) {
      layer.render(this.polylineShader, this.polygonShader, total);
    }
  }
};

// src/colors.ts
var LAYER_COLORS = {
  "F.Cu": [0.85, 0.2, 0.2, 0.8],
  "B.Cu": [0.2, 0.4, 0.85, 0.8],
  "In1.Cu": [0.85, 0.85, 0.2, 0.8],
  "In2.Cu": [0.85, 0.4, 0.85, 0.8],
  "F.SilkS": [0, 0.85, 0.85, 0.9],
  "B.SilkS": [0.85, 0, 0.85, 0.9],
  "F.Mask": [0.6, 0.15, 0.6, 0.4],
  "B.Mask": [0.15, 0.6, 0.15, 0.4],
  "F.Paste": [0.85, 0.55, 0.55, 0.5],
  "B.Paste": [0.55, 0.55, 0.85, 0.5],
  "F.Fab": [0.6, 0.6, 0.2, 0.7],
  "B.Fab": [0.2, 0.2, 0.6, 0.7],
  "F.CrtYd": [0.4, 0.4, 0.4, 0.5],
  "B.CrtYd": [0.3, 0.3, 0.5, 0.5],
  "Edge.Cuts": [0.9, 0.85, 0.2, 1],
  "Dwgs.User": [0.6, 0.6, 0.6, 0.6],
  "Cmts.User": [0.4, 0.4, 0.8, 0.6]
};
var PAD_COLOR = [0.35, 0.6, 0.35, 0.9];
var PAD_FRONT_COLOR = [0.85, 0.2, 0.2, 0.7];
var PAD_BACK_COLOR = [0.2, 0.4, 0.85, 0.7];
var VIA_COLOR = [0.6, 0.6, 0.6, 0.9];
var VIA_DRILL_COLOR = [0.15, 0.15, 0.15, 1];
var SELECTION_COLOR = [1, 1, 1, 0.3];
var ZONE_COLOR_ALPHA = 0.25;
function getLayerColor(layer) {
  if (!layer)
    return [0.5, 0.5, 0.5, 0.5];
  return LAYER_COLORS[layer] ?? [0.5, 0.5, 0.5, 0.5];
}
function getPadColor(layers) {
  const hasFront = layers.some((l) => l === "F.Cu" || l === "*.Cu");
  const hasBack = layers.some((l) => l === "B.Cu" || l === "*.Cu");
  if (hasFront && hasBack)
    return PAD_COLOR;
  if (hasFront)
    return PAD_FRONT_COLOR;
  if (hasBack)
    return PAD_BACK_COLOR;
  return PAD_COLOR;
}

// src/painter.ts
var DEG_TO_RAD = Math.PI / 180;
function p2v(p) {
  return new Vec2(p.x, p.y);
}
function fpTransform(fpAt, localX, localY) {
  const rad = -(fpAt.r || 0) * DEG_TO_RAD;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return new Vec2(
    fpAt.x + localX * cos - localY * sin,
    fpAt.y + localX * sin + localY * cos
  );
}
function padTransform(fpAt, padAt, lx, ly) {
  const padRad = -(padAt.r || 0) * DEG_TO_RAD;
  const pc = Math.cos(padRad), ps = Math.sin(padRad);
  const px = lx * pc - ly * ps;
  const py = lx * ps + ly * pc;
  return fpTransform(fpAt, padAt.x + px, padAt.y + py);
}
function arcToPoints(start, mid, end, segments = 32) {
  const ax = start.x, ay = start.y;
  const bx = mid.x, by = mid.y;
  const cx = end.x, cy = end.y;
  const D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
  if (Math.abs(D) < 1e-10) {
    return [new Vec2(ax, ay), new Vec2(bx, by), new Vec2(cx, cy)];
  }
  const ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D;
  const uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D;
  const radius = Math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2);
  const startAngle = Math.atan2(ay - uy, ax - ux);
  const midAngle = Math.atan2(by - uy, bx - ux);
  const endAngle = Math.atan2(cy - uy, cx - ux);
  let da1 = midAngle - startAngle;
  while (da1 > Math.PI)
    da1 -= 2 * Math.PI;
  while (da1 < -Math.PI)
    da1 += 2 * Math.PI;
  const clockwise = da1 < 0;
  let sweep = endAngle - startAngle;
  if (clockwise) {
    while (sweep > 0)
      sweep -= 2 * Math.PI;
  } else {
    while (sweep < 0)
      sweep += 2 * Math.PI;
  }
  const points = [];
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const angle = startAngle + sweep * t;
    points.push(new Vec2(ux + radius * Math.cos(angle), uy + radius * Math.sin(angle)));
  }
  return points;
}
function paintAll(renderer, model, hiddenLayers) {
  const hidden = hiddenLayers ?? /* @__PURE__ */ new Set();
  renderer.dispose_layers();
  if (!hidden.has("Edge.Cuts"))
    paintBoardEdges(renderer, model);
  paintZones(renderer, model, hidden);
  paintTracks(renderer, model, hidden);
  if (!hidden.has("Vias"))
    paintVias(renderer, model);
  for (const fp of model.footprints) {
    paintFootprint(renderer, fp, hidden);
  }
}
function paintBoardEdges(renderer, model) {
  const layer = renderer.start_layer("Edge.Cuts");
  const [r, g, b, a] = getLayerColor("Edge.Cuts");
  for (const edge of model.board.edges) {
    if (edge.type === "line" && edge.start && edge.end) {
      layer.geometry.add_polyline([p2v(edge.start), p2v(edge.end)], 0.15, r, g, b, a);
    } else if (edge.type === "arc" && edge.start && edge.mid && edge.end) {
      layer.geometry.add_polyline(arcToPoints(edge.start, edge.mid, edge.end), 0.15, r, g, b, a);
    } else if (edge.type === "circle" && edge.center && edge.end) {
      const cx = edge.center.x, cy = edge.center.y;
      const rad = Math.sqrt((edge.end.x - cx) ** 2 + (edge.end.y - cy) ** 2);
      const pts = [];
      for (let i = 0; i <= 64; i++) {
        const angle = i / 64 * 2 * Math.PI;
        pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
      }
      layer.geometry.add_polyline(pts, 0.15, r, g, b, a);
    } else if (edge.type === "rect" && edge.start && edge.end) {
      const s = edge.start, e = edge.end;
      layer.geometry.add_polyline([
        new Vec2(s.x, s.y),
        new Vec2(e.x, s.y),
        new Vec2(e.x, e.y),
        new Vec2(s.x, e.y),
        new Vec2(s.x, s.y)
      ], 0.15, r, g, b, a);
    }
  }
  renderer.end_layer();
}
function paintZones(renderer, model, hidden) {
  for (const zone of model.zones) {
    for (const filled of zone.filled_polygons) {
      if (hidden.has(filled.layer))
        continue;
      const [r, g, b] = getLayerColor(filled.layer);
      const layer = renderer.start_layer(`zone_${zone.uuid ?? ""}:${filled.layer}`);
      const pts = filled.points.map(p2v);
      if (pts.length >= 3) {
        layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA);
      }
      renderer.end_layer();
    }
  }
}
function paintTracks(renderer, model, hidden) {
  const byLayer = /* @__PURE__ */ new Map();
  for (const track of model.tracks) {
    const ln = track.layer ?? "F.Cu";
    if (hidden.has(ln))
      continue;
    let arr = byLayer.get(ln);
    if (!arr) {
      arr = [];
      byLayer.set(ln, arr);
    }
    arr.push(track);
  }
  for (const [layerName, tracks] of byLayer) {
    const [r, g, b, a] = getLayerColor(layerName);
    const layer = renderer.start_layer(`tracks:${layerName}`);
    for (const track of tracks) {
      layer.geometry.add_polyline([p2v(track.start), p2v(track.end)], track.width, r, g, b, a);
    }
    renderer.end_layer();
  }
  if (model.arcs.length > 0) {
    const arcByLayer = /* @__PURE__ */ new Map();
    for (const arc of model.arcs) {
      const ln = arc.layer ?? "F.Cu";
      if (hidden.has(ln))
        continue;
      let arr = arcByLayer.get(ln);
      if (!arr) {
        arr = [];
        arcByLayer.set(ln, arr);
      }
      arr.push(arc);
    }
    for (const [layerName, arcs] of arcByLayer) {
      const [r, g, b, a] = getLayerColor(layerName);
      const layer = renderer.start_layer(`arc_tracks:${layerName}`);
      for (const arc of arcs) {
        layer.geometry.add_polyline(arcToPoints(arc.start, arc.mid, arc.end), arc.width, r, g, b, a);
      }
      renderer.end_layer();
    }
  }
}
function paintVias(renderer, model) {
  if (model.vias.length === 0)
    return;
  const layer = renderer.start_layer("vias");
  for (const via of model.vias) {
    const [vr, vg, vb, va] = VIA_COLOR;
    layer.geometry.add_circle(via.at.x, via.at.y, via.size / 2, vr, vg, vb, va);
    const [dr, dg, db, da] = VIA_DRILL_COLOR;
    layer.geometry.add_circle(via.at.x, via.at.y, via.drill / 2, dr, dg, db, da);
  }
  renderer.end_layer();
}
function paintFootprint(renderer, fp, hidden) {
  const drawingsByLayer = /* @__PURE__ */ new Map();
  for (const drawing of fp.drawings) {
    const ln = drawing.layer ?? "F.SilkS";
    if (hidden.has(ln))
      continue;
    let arr = drawingsByLayer.get(ln);
    if (!arr) {
      arr = [];
      drawingsByLayer.set(ln, arr);
    }
    arr.push(drawing);
  }
  for (const [layerName, drawings] of drawingsByLayer) {
    const [r, g, b, a] = getLayerColor(layerName);
    const layer = renderer.start_layer(`fp:${fp.uuid}:${layerName}`);
    for (const drawing of drawings) {
      paintDrawing(layer, fp.at, drawing, r, g, b, a);
    }
    renderer.end_layer();
  }
  if (fp.pads.length > 0) {
    const anyVisible = fp.pads.some((pad) => pad.layers.some((l) => !hidden.has(l)));
    if (anyVisible) {
      const layer = renderer.start_layer(`fp:${fp.uuid}:pads`);
      for (const pad of fp.pads) {
        if (pad.layers.some((l) => !hidden.has(l))) {
          paintPad(layer, fp.at, pad);
        }
      }
      renderer.end_layer();
    }
  }
}
function paintDrawing(layer, fpAt, drawing, r, g, b, a) {
  const w = drawing.width || 0.12;
  if (drawing.type === "line" && drawing.start && drawing.end) {
    const p1 = fpTransform(fpAt, drawing.start.x, drawing.start.y);
    const p2 = fpTransform(fpAt, drawing.end.x, drawing.end.y);
    layer.geometry.add_polyline([p1, p2], w, r, g, b, a);
  } else if (drawing.type === "arc" && drawing.start && drawing.mid && drawing.end) {
    const localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
    const worldPts = localPts.map((p) => fpTransform(fpAt, p.x, p.y));
    layer.geometry.add_polyline(worldPts, w, r, g, b, a);
  } else if (drawing.type === "circle" && drawing.center && drawing.end) {
    const cx = drawing.center.x, cy = drawing.center.y;
    const rad = Math.sqrt((drawing.end.x - cx) ** 2 + (drawing.end.y - cy) ** 2);
    const pts = [];
    for (let i = 0; i <= 48; i++) {
      const angle = i / 48 * 2 * Math.PI;
      pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
    }
    layer.geometry.add_polyline(pts.map((p) => fpTransform(fpAt, p.x, p.y)), w, r, g, b, a);
  } else if (drawing.type === "rect" && drawing.start && drawing.end) {
    const s = drawing.start, e = drawing.end;
    const corners = [
      fpTransform(fpAt, s.x, s.y),
      fpTransform(fpAt, e.x, s.y),
      fpTransform(fpAt, e.x, e.y),
      fpTransform(fpAt, s.x, e.y),
      fpTransform(fpAt, s.x, s.y)
    ];
    layer.geometry.add_polyline(corners, w, r, g, b, a);
  } else if (drawing.type === "polygon" && drawing.points) {
    const worldPts = drawing.points.map((p) => fpTransform(fpAt, p.x, p.y));
    if (worldPts.length >= 3) {
      worldPts.push(worldPts[0].copy());
      layer.geometry.add_polyline(worldPts, w, r, g, b, a);
    }
  }
}
function paintPad(layer, fpAt, pad) {
  const [cr, cg, cb, ca] = getPadColor(pad.layers);
  const hw = pad.size.w / 2;
  const hh = pad.size.h / 2;
  if (pad.shape === "circle") {
    const center = fpTransform(fpAt, pad.at.x, pad.at.y);
    layer.geometry.add_circle(center.x, center.y, hw, cr, cg, cb, ca);
  } else if (pad.shape === "oval") {
    const longAxis = Math.max(hw, hh);
    const shortAxis = Math.min(hw, hh);
    const focalDist = longAxis - shortAxis;
    let p1, p2;
    if (hw >= hh) {
      p1 = padTransform(fpAt, pad.at, -focalDist, 0);
      p2 = padTransform(fpAt, pad.at, focalDist, 0);
    } else {
      p1 = padTransform(fpAt, pad.at, 0, -focalDist);
      p2 = padTransform(fpAt, pad.at, 0, focalDist);
    }
    layer.geometry.add_polyline([p1, p2], shortAxis * 2, cr, cg, cb, ca);
  } else {
    const corners = [
      padTransform(fpAt, pad.at, -hw, -hh),
      padTransform(fpAt, pad.at, hw, -hh),
      padTransform(fpAt, pad.at, hw, hh),
      padTransform(fpAt, pad.at, -hw, hh)
    ];
    layer.geometry.add_polygon(corners, cr, cg, cb, ca);
  }
  if (pad.drill && pad.type === "thru_hole") {
    const center = fpTransform(fpAt, pad.at.x, pad.at.y);
    const drillR = (pad.drill.size_x ?? pad.size.w * 0.5) / 2;
    layer.geometry.add_circle(center.x, center.y, drillR, 0.15, 0.15, 0.15, 1);
  }
}
function paintSelection(renderer, fp) {
  const layer = renderer.start_layer("selection");
  const [r, g, b, a] = SELECTION_COLOR;
  const allPoints = [];
  for (const pad of fp.pads) {
    const center = fpTransform(fp.at, pad.at.x, pad.at.y);
    const hw = pad.size.w / 2, hh = pad.size.h / 2;
    allPoints.push(center.add(new Vec2(-hw, -hh)));
    allPoints.push(center.add(new Vec2(hw, hh)));
  }
  for (const drawing of fp.drawings) {
    if (drawing.start)
      allPoints.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
    if (drawing.end)
      allPoints.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
    if (drawing.center)
      allPoints.push(fpTransform(fp.at, drawing.center.x, drawing.center.y));
  }
  if (allPoints.length > 0) {
    const bbox = BBox.from_points(allPoints).grow(0.5);
    layer.geometry.add_polygon([
      new Vec2(bbox.x, bbox.y),
      new Vec2(bbox.x2, bbox.y),
      new Vec2(bbox.x2, bbox.y2),
      new Vec2(bbox.x, bbox.y2)
    ], r, g, b, a);
  }
  renderer.end_layer();
  return layer;
}
function computeBBox(model) {
  const points = [];
  for (const edge of model.board.edges) {
    if (edge.start)
      points.push(p2v(edge.start));
    if (edge.end)
      points.push(p2v(edge.end));
    if (edge.mid)
      points.push(p2v(edge.mid));
    if (edge.center)
      points.push(p2v(edge.center));
  }
  for (const fp of model.footprints) {
    points.push(new Vec2(fp.at.x, fp.at.y));
    for (const pad of fp.pads) {
      points.push(fpTransform(fp.at, pad.at.x, pad.at.y));
    }
  }
  for (const track of model.tracks) {
    points.push(p2v(track.start));
    points.push(p2v(track.end));
  }
  for (const via of model.vias) {
    points.push(p2v(via.at));
  }
  if (points.length === 0)
    return new BBox(0, 0, 100, 100);
  return BBox.from_points(points).grow(5);
}

// src/hit-test.ts
var DEG_TO_RAD2 = Math.PI / 180;
function fpTransform2(fpAt, localX, localY) {
  const rad = -(fpAt.r || 0) * DEG_TO_RAD2;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return new Vec2(
    fpAt.x + localX * cos - localY * sin,
    fpAt.y + localX * sin + localY * cos
  );
}
function footprintBBox(fp) {
  const points = [];
  for (const pad of fp.pads) {
    const center = fpTransform2(fp.at, pad.at.x, pad.at.y);
    const hw = pad.size.w / 2;
    const hh = pad.size.h / 2;
    points.push(center.add(new Vec2(-hw, -hh)));
    points.push(center.add(new Vec2(hw, hh)));
  }
  for (const drawing of fp.drawings) {
    if (drawing.start)
      points.push(fpTransform2(fp.at, drawing.start.x, drawing.start.y));
    if (drawing.end)
      points.push(fpTransform2(fp.at, drawing.end.x, drawing.end.y));
    if (drawing.center)
      points.push(fpTransform2(fp.at, drawing.center.x, drawing.center.y));
    if (drawing.points) {
      for (const p of drawing.points) {
        points.push(fpTransform2(fp.at, p.x, p.y));
      }
    }
  }
  if (points.length === 0) {
    return new BBox(fp.at.x - 1, fp.at.y - 1, 2, 2);
  }
  return BBox.from_points(points).grow(0.2);
}
function hitTestFootprints(worldPos, footprints) {
  for (let i = footprints.length - 1; i >= 0; i--) {
    const bbox = footprintBBox(footprints[i]);
    if (bbox.contains_point(worldPos)) {
      return i;
    }
  }
  return -1;
}

// src/editor.ts
var Editor = class {
  canvas;
  renderer;
  camera;
  panAndZoom;
  model = null;
  baseUrl;
  ws = null;
  // Selection & drag state
  selectedFpIndex = -1;
  isDragging = false;
  dragStartWorld = null;
  dragStartFpPos = null;
  needsRedraw = true;
  // Layer visibility
  hiddenLayers = /* @__PURE__ */ new Set();
  onLayersChanged = null;
  // Track current mouse position
  lastMouseScreen = new Vec2(0, 0);
  constructor(canvas2, baseUrl2) {
    this.canvas = canvas2;
    this.baseUrl = baseUrl2;
    this.renderer = new Renderer(canvas2);
    this.camera = new Camera2();
    this.panAndZoom = new PanAndZoom(canvas2, this.camera, () => this.requestRedraw());
    this.setupMouseHandlers();
    this.setupKeyboardHandlers();
    this.setupResizeHandler();
    this.renderer.setup();
    this.startRenderLoop();
  }
  async init() {
    await this.fetchAndPaint();
    this.connectWebSocket();
  }
  async fetchAndPaint() {
    const resp = await fetch(`${this.baseUrl}/api/render-model`);
    this.applyModel(await resp.json(), true);
  }
  applyModel(model, fitToView = false) {
    this.model = model;
    this.paint();
    this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
    if (fitToView) {
      this.camera.bbox = computeBBox(this.model);
    }
    this.requestRedraw();
  }
  paint() {
    if (!this.model)
      return;
    paintAll(this.renderer, this.model, this.hiddenLayers);
    if (this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
      paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]);
    }
  }
  connectWebSocket() {
    const wsUrl = this.baseUrl.replace(/^http/, "ws") + "/ws";
    this.ws = new WebSocket(wsUrl);
    this.ws.onopen = () => console.log("WS connected");
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "layout_updated" && msg.model) {
        this.applyModel(msg.model);
      }
    };
    this.ws.onerror = (err) => console.error("WS error:", err);
    this.ws.onclose = () => {
      setTimeout(() => this.connectWebSocket(), 2e3);
    };
  }
  setupMouseHandlers() {
    this.canvas.addEventListener("mousedown", (e) => {
      if (e.button !== 0)
        return;
      const rect = this.canvas.getBoundingClientRect();
      const screenPos = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
      const worldPos = this.camera.screen_to_world(screenPos);
      if (!this.model)
        return;
      const hitIdx = hitTestFootprints(worldPos, this.model.footprints);
      if (hitIdx >= 0) {
        this.selectedFpIndex = hitIdx;
        const fp = this.model.footprints[hitIdx];
        this.isDragging = true;
        this.dragStartWorld = worldPos;
        this.dragStartFpPos = { x: fp.at.x, y: fp.at.y };
        this.repaintWithSelection();
      } else {
        if (this.selectedFpIndex >= 0) {
          this.selectedFpIndex = -1;
          this.paint();
          this.requestRedraw();
        }
      }
    });
    this.canvas.addEventListener("mousemove", (e) => {
      const rect = this.canvas.getBoundingClientRect();
      this.lastMouseScreen = new Vec2(e.clientX - rect.left, e.clientY - rect.top);
      if (!this.isDragging || !this.model || this.selectedFpIndex < 0)
        return;
      const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
      const delta = worldPos.sub(this.dragStartWorld);
      const fp = this.model.footprints[this.selectedFpIndex];
      fp.at.x = this.dragStartFpPos.x + delta.x;
      fp.at.y = this.dragStartFpPos.y + delta.y;
      this.paint();
      this.requestRedraw();
    });
    this.canvas.addEventListener("mouseup", async (e) => {
      if (e.button !== 0 || !this.isDragging)
        return;
      this.isDragging = false;
      if (!this.model || this.selectedFpIndex < 0 || !this.dragStartFpPos)
        return;
      const fp = this.model.footprints[this.selectedFpIndex];
      const dx = fp.at.x - this.dragStartFpPos.x;
      const dy = fp.at.y - this.dragStartFpPos.y;
      if (Math.abs(dx) < 1e-3 && Math.abs(dy) < 1e-3)
        return;
      await this.executeAction("move", {
        uuid: fp.uuid,
        x: fp.at.x,
        y: fp.at.y,
        r: fp.at.r || null
      });
    });
  }
  setupKeyboardHandlers() {
    window.addEventListener("keydown", async (e) => {
      if (e.key === "r" || e.key === "R") {
        if (e.ctrlKey || e.metaKey || e.altKey)
          return;
        await this.actionOnSelected("rotate", (fp) => ({ uuid: fp.uuid, delta_degrees: 90 }));
        return;
      }
      if (e.key === "f" || e.key === "F") {
        if (e.ctrlKey || e.metaKey || e.altKey)
          return;
        await this.actionOnSelected("flip", (fp) => ({ uuid: fp.uuid }));
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        await this.serverAction("/api/undo");
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && e.shiftKey || (e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        await this.serverAction("/api/redo");
        return;
      }
    });
  }
  setupResizeHandler() {
    window.addEventListener("resize", () => {
      this.requestRedraw();
    });
  }
  async actionOnSelected(type, detailsFn) {
    if (!this.model || this.selectedFpIndex < 0)
      return;
    const fp = this.model.footprints[this.selectedFpIndex];
    await this.executeAction(type, detailsFn(fp));
  }
  async executeAction(type, details) {
    try {
      const resp = await fetch(`${this.baseUrl}/api/execute-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, details })
      });
      const data = await resp.json();
      if (data.model)
        this.applyModel(data.model);
    } catch (err) {
      console.error("Failed to execute action:", err);
    }
  }
  async serverAction(endpoint) {
    try {
      const resp = await fetch(`${this.baseUrl}${endpoint}`, { method: "POST" });
      const data = await resp.json();
      if (data.model)
        this.applyModel(data.model);
    } catch (err) {
      console.error(`Failed ${endpoint}:`, err);
    }
  }
  // --- Layer visibility ---
  setLayerVisible(layer, visible) {
    if (visible) {
      this.hiddenLayers.delete(layer);
    } else {
      this.hiddenLayers.add(layer);
    }
    this.paint();
    this.requestRedraw();
  }
  isLayerVisible(layer) {
    return !this.hiddenLayers.has(layer);
  }
  getLayers() {
    if (!this.model)
      return [];
    const layers = /* @__PURE__ */ new Set();
    for (const fp of this.model.footprints) {
      layers.add(fp.layer);
      for (const pad of fp.pads) {
        for (const l of pad.layers)
          layers.add(l);
      }
      for (const d of fp.drawings) {
        if (d.layer)
          layers.add(d.layer);
      }
    }
    for (const t of this.model.tracks) {
      if (t.layer)
        layers.add(t.layer);
    }
    for (const a of this.model.arcs) {
      if (a.layer)
        layers.add(a.layer);
    }
    for (const z of this.model.zones) {
      for (const fp of z.filled_polygons)
        layers.add(fp.layer);
    }
    layers.add("Edge.Cuts");
    layers.add("Vias");
    return [...layers].sort();
  }
  setOnLayersChanged(cb) {
    this.onLayersChanged = cb;
  }
  repaintWithSelection() {
    this.paint();
    this.requestRedraw();
  }
  requestRedraw() {
    this.needsRedraw = true;
  }
  startRenderLoop() {
    const loop = () => {
      if (this.needsRedraw) {
        this.needsRedraw = false;
        this.camera.viewport_size = new Vec2(this.canvas.clientWidth, this.canvas.clientHeight);
        this.renderer.draw(this.camera.matrix);
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
};

// src/main.ts
var canvas = document.getElementById("editor-canvas");
if (!canvas) {
  throw new Error("Canvas element #editor-canvas not found");
}
var baseUrl = window.location.origin;
var editor = new Editor(canvas, baseUrl);
function buildLayerPanel() {
  const panel = document.getElementById("layer-panel");
  if (!panel)
    return;
  panel.innerHTML = "";
  const layers = editor.getLayers();
  for (const layerName of layers) {
    const row = document.createElement("label");
    row.className = "layer-row";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = editor.isLayerVisible(layerName);
    cb.addEventListener("change", () => {
      editor.setLayerVisible(layerName, cb.checked);
    });
    const swatch = document.createElement("span");
    swatch.className = "layer-swatch";
    const [r, g, b] = getLayerColor(layerName);
    swatch.style.background = `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;
    const label = document.createElement("span");
    label.textContent = layerName;
    row.appendChild(cb);
    row.appendChild(swatch);
    row.appendChild(label);
    panel.appendChild(row);
  }
}
editor.init().then(() => {
  buildLayerPanel();
  editor.setOnLayersChanged(buildLayerPanel);
}).catch((err) => {
  console.error("Failed to initialize editor:", err);
});
//# sourceMappingURL=editor.js.map

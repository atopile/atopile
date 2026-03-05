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
    return new _Matrix3([c, s, 0, -s, c, 0, 0, 0, 1]);
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
  /** this = this * other */
  multiply_self(other) {
    const a = this.elements;
    const b = other.elements;
    const a00 = a[0], a01 = a[1], a02 = a[2];
    const a10 = a[3], a11 = a[4], a12 = a[5];
    const a20 = a[6], a21 = a[7], a22 = a[8];
    const b00 = b[0], b01 = b[1], b02 = b[2];
    const b10 = b[3], b11 = b[4], b12 = b[5];
    const b20 = b[6], b21 = b[7], b22 = b[8];
    a[0] = a00 * b00 + a10 * b01 + a20 * b02;
    a[1] = a01 * b00 + a11 * b01 + a21 * b02;
    a[2] = a02 * b00 + a12 * b01 + a22 * b02;
    a[3] = a00 * b10 + a10 * b11 + a20 * b12;
    a[4] = a01 * b10 + a11 * b11 + a21 * b12;
    a[5] = a02 * b10 + a12 * b11 + a22 * b12;
    a[6] = a00 * b20 + a10 * b21 + a20 * b22;
    a[7] = a01 * b20 + a11 * b21 + a21 * b22;
    a[8] = a02 * b20 + a12 * b21 + a22 * b22;
    return this;
  }
  multiply(other) {
    return this.copy().multiply_self(other);
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
  constructor(x = 0, y = 0, w2 = 0, h = 0) {
    this.x = x;
    this.y = y;
    this.w = w2;
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
  constructor(target, camera, callback, min_zoom = 0.1, max_zoom = 400) {
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
    window.addEventListener("mouseup", (e) => {
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
  f4(x, y, z, w2) {
    this.gl.uniform4f(this.location, x, y, z, w2);
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
var point_vert = `#version 300 es
uniform mat3 u_matrix;
uniform float u_pointSize;
in vec2 a_position;
void main() {
    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);
    gl_PointSize = u_pointSize;
}`;
var point_frag = `#version 300 es
precision highp float;
uniform vec4 u_color;
out vec4 o_color;
void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (dot(coord, coord) > 0.25) discard;
    o_color = u_color;
    gl_FragDepth = 0.00001;
}`;
var blit_vert = `#version 300 es
in vec2 a_position;
in vec2 a_uv;
out vec2 v_uv;
void main() {
    v_uv = a_uv;
    gl_Position = vec4(a_position, 0.0, 1.0);
}`;
var blit_frag = `#version 300 es
precision highp float;
uniform sampler2D u_tex;
in vec2 v_uv;
out vec4 o_color;
void main() {
    o_color = texture(u_tex, v_uv);
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
  #line_chunks = [];
  #poly_chunks = [];
  add_polyline(points, width, r, g, b, a, ownerId = null) {
    if (points.length < 2)
      return;
    this.#polyline_data.push({ data: tessellate_polyline(points, width, r, g, b, a), ownerId });
  }
  add_circle(cx, cy, radius, r, g, b, a, ownerId = null) {
    this.#circle_data.push({ data: tessellate_circle(cx, cy, radius, r, g, b, a), ownerId });
  }
  add_polygon(points, r, g, b, a, ownerId = null) {
    if (points.length < 3)
      return;
    this.#polygon_data.push({ data: triangulate_polygon(points, r, g, b, a), ownerId });
  }
  /** Upload all collected data to GPU */
  commit(polylineShader, polygonShader) {
    const lineItems = [...this.#polyline_data, ...this.#circle_data];
    this.#line_chunks = [];
    if (lineItems.length > 0) {
      let totalVerts = 0;
      for (const item of lineItems)
        totalVerts += item.data.vertexCount;
      const pos = new Float32Array(totalVerts * 2);
      const cap = new Float32Array(totalVerts);
      const col = new Float32Array(totalVerts * 4);
      let pi = 0, ci = 0, coli = 0, vi = 0;
      for (const item of lineItems) {
        const data = item.data;
        pos.set(data.positions, pi);
        pi += data.positions.length;
        cap.set(data.caps, ci);
        ci += data.caps.length;
        col.set(data.colors, coli);
        coli += data.colors.length;
        this.#line_chunks.push({ offset: vi, count: data.vertexCount, ownerId: item.ownerId });
        vi += data.vertexCount;
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
    this.#poly_chunks = [];
    if (this.#polygon_data.length > 0) {
      let totalVerts = 0;
      for (const item of this.#polygon_data)
        totalVerts += item.data.vertexCount;
      const pos = new Float32Array(totalVerts * 2);
      const col = new Float32Array(totalVerts * 4);
      let pi = 0, coli = 0, vi = 0;
      for (const item of this.#polygon_data) {
        const data = item.data;
        pos.set(data.positions, pi);
        pi += data.positions.length;
        col.set(data.colors, coli);
        coli += data.colors.length;
        this.#poly_chunks.push({ offset: vi, count: data.vertexCount, ownerId: item.ownerId });
        vi += data.vertexCount;
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
  draw_filtered_chunks(chunks, skippedOwners) {
    let runStart = -1;
    let runCount = 0;
    const flush = () => {
      if (runCount <= 0)
        return;
      this.gl.drawArrays(this.gl.TRIANGLES, runStart, runCount);
      runStart = -1;
      runCount = 0;
    };
    for (const chunk of chunks) {
      const shouldSkip = chunk.ownerId !== null && skippedOwners.has(chunk.ownerId);
      if (shouldSkip) {
        flush();
        continue;
      }
      if (runCount === 0) {
        runStart = chunk.offset;
        runCount = chunk.count;
        continue;
      }
      if (runStart + runCount === chunk.offset) {
        runCount += chunk.count;
        continue;
      }
      flush();
      runStart = chunk.offset;
      runCount = chunk.count;
    }
    flush();
  }
  render(polylineShader, polygonShader, matrix, depth, alpha, skippedOwners) {
    const hasSkips = !!skippedOwners && skippedOwners.size > 0;
    if (this.#poly_vertex_count > 0) {
      polygonShader.bind();
      polygonShader.uniforms["u_matrix"].mat3f(false, matrix.elements);
      polygonShader.uniforms["u_depth"].f1(depth);
      polygonShader.uniforms["u_alpha"].f1(alpha);
      this.#poly_vao.bind();
      if (!hasSkips) {
        this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#poly_vertex_count);
      } else {
        this.draw_filtered_chunks(this.#poly_chunks, skippedOwners);
      }
    }
    if (this.#line_vertex_count > 0) {
      polylineShader.bind();
      polylineShader.uniforms["u_matrix"].mat3f(false, matrix.elements);
      polylineShader.uniforms["u_depth"].f1(depth);
      polylineShader.uniforms["u_alpha"].f1(alpha);
      this.#line_vao.bind();
      if (!hasSkips) {
        this.gl.drawArrays(this.gl.TRIANGLES, 0, this.#line_vertex_count);
      } else {
        this.draw_filtered_chunks(this.#line_chunks, skippedOwners);
      }
    }
  }
  dispose() {
    this.#poly_vao?.dispose();
    this.#line_vao?.dispose();
  }
  stats() {
    return {
      lineVertices: this.#line_vertex_count,
      polyVertices: this.#poly_vertex_count
    };
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
  visible = true;
  transform = null;
  commit(polylineShader, polygonShader) {
    this.geometry.commit(polylineShader, polygonShader);
  }
  render(polylineShader, polygonShader, matrix, alpha = 1, skippedOwners) {
    if (!this.visible)
      return;
    const m = this.transform ? matrix.multiply(this.transform) : matrix;
    this.geometry.render(polylineShader, polygonShader, m, this.depth, alpha, skippedOwners);
  }
  dispose() {
    this.geometry.dispose();
  }
  stats() {
    return this.geometry.stats();
  }
};
var Renderer = class _Renderer {
  gl;
  canvas;
  layers = /* @__PURE__ */ new Map();
  dynamicLayers = [];
  dynamicLayersMap = /* @__PURE__ */ new Map();
  isDynamicContext = false;
  projection_matrix = Matrix3.identity();
  polylineShader;
  polygonShader;
  pointShader;
  blitShader;
  static DEPTH_STEP = 1e-4;
  static DYNAMIC_DEPTH_LIFT = 0.2;
  nextDepth = _Renderer.DEPTH_STEP;
  dynamicFallbackDepth = 0.8;
  gridVao = null;
  gridPosBuf = null;
  gridVertexCount = 0;
  blitVao = null;
  dragCacheTex = null;
  dragCacheFbo = null;
  dragCacheDepth = null;
  dragCacheWidth = 0;
  dragCacheHeight = 0;
  useDragCache = false;
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
    if (this.canvas.width === pw && this.canvas.height === ph)
      return;
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
    for (const layer of this.layers.values())
      layer.dispose();
    this.layers.clear();
    this.nextDepth = _Renderer.DEPTH_STEP;
    this.end_fast_drag_cache();
    this.dispose_dynamic_layers();
  }
  dispose_dynamic_layers() {
    for (const layer of this.dynamicLayers)
      layer.dispose();
    this.dynamicLayers = [];
    this.dynamicLayersMap.clear();
    this.dynamicFallbackDepth = 0.8;
  }
  dispose_dynamic_overlays() {
    const contextLayers = new Set(this.dynamicLayersMap.values());
    const remaining = [];
    for (const layer of this.dynamicLayers) {
      if (contextLayers.has(layer)) {
        remaining.push(layer);
      } else {
        layer.dispose();
      }
    }
    this.dynamicLayers = remaining;
  }
  get_layer(name) {
    if (this.isDynamicContext) {
      let layer2 = this.dynamicLayersMap.get(name);
      if (!layer2) {
        const staticDepth = this.layers.get(name)?.depth;
        const liftedDepth = staticDepth !== void 0 ? Math.min(0.9998, staticDepth + _Renderer.DYNAMIC_DEPTH_LIFT) : this.dynamicFallbackDepth;
        this.dynamicFallbackDepth = Math.min(0.9998, this.dynamicFallbackDepth + _Renderer.DEPTH_STEP);
        layer2 = new RenderLayer(this.gl, "dyn_" + name, liftedDepth);
        this.dynamicLayersMap.set(name, layer2);
        this.dynamicLayers.push(layer2);
      }
      return layer2;
    }
    let layer = this.layers.get(name);
    if (!layer) {
      layer = new RenderLayer(this.gl, name, this.nextDepth);
      this.nextDepth = Math.min(0.9999, this.nextDepth + _Renderer.DEPTH_STEP);
      this.layers.set(name, layer);
    }
    return layer;
  }
  set_layer_visible(name, visible) {
    for (const [layerName, layer] of this.layers) {
      if (layerName === name || layerName === `zone:${name}`) {
        layer.visible = visible;
      }
    }
  }
  set_layer_transform(name, transform) {
    const layer = this.layers.get(name);
    if (layer)
      layer.transform = transform;
  }
  commit_all_layers() {
    for (const layer of this.layers.values()) {
      layer.commit(this.polylineShader, this.polygonShader);
    }
  }
  start_dynamic_layer(name) {
    const layer = new RenderLayer(this.gl, name, 1);
    this.dynamicLayers.push(layer);
    return layer;
  }
  commit_dynamic_layer(layer) {
    layer.commit(this.polylineShader, this.polygonShader);
  }
  commit_dynamic_context_layers() {
    for (const layer of this.dynamicLayersMap.values()) {
      layer.commit(this.polylineShader, this.polygonShader);
    }
  }
  get_layer_stats() {
    const stats = {};
    for (const [name, layer] of this.layers.entries()) {
      const layerStats = layer.stats();
      stats[name] = {
        lineVertices: layerStats.lineVertices,
        polyVertices: layerStats.polyVertices,
        visible: layer.visible,
        depth: layer.depth
      };
    }
    return stats;
  }
  ensure_drag_cache_target(w2, h) {
    const gl = this.gl;
    if (!this.dragCacheTex) {
      this.dragCacheTex = gl.createTexture();
    }
    if (!this.dragCacheFbo) {
      this.dragCacheFbo = gl.createFramebuffer();
    }
    if (!this.dragCacheDepth) {
      this.dragCacheDepth = gl.createRenderbuffer();
    }
    if (!this.dragCacheTex || !this.dragCacheFbo || !this.dragCacheDepth) {
      return false;
    }
    if (this.dragCacheWidth === w2 && this.dragCacheHeight === h) {
      return true;
    }
    gl.bindTexture(gl.TEXTURE_2D, this.dragCacheTex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w2, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.bindRenderbuffer(gl.RENDERBUFFER, this.dragCacheDepth);
    gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w2, h);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.dragCacheFbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.dragCacheTex, 0);
    gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, this.dragCacheDepth);
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.bindTexture(gl.TEXTURE_2D, null);
    gl.bindRenderbuffer(gl.RENDERBUFFER, null);
    if (status !== gl.FRAMEBUFFER_COMPLETE) {
      return false;
    }
    this.dragCacheWidth = w2;
    this.dragCacheHeight = h;
    return true;
  }
  begin_fast_drag_cache(cameraMatrix, skippedOwners) {
    this.update_size();
    const gl = this.gl;
    const w2 = this.canvas.width;
    const h = this.canvas.height;
    if (w2 <= 0 || h <= 0) {
      this.useDragCache = false;
      return false;
    }
    if (!this.ensure_drag_cache_target(w2, h) || !this.dragCacheFbo) {
      this.useDragCache = false;
      return false;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.dragCacheFbo);
    gl.viewport(0, 0, w2, h);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const total = this.projection_matrix.multiply(cameraMatrix);
    this.render_static_scene(total, skippedOwners);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, w2, h);
    this.useDragCache = true;
    return true;
  }
  end_fast_drag_cache() {
    this.useDragCache = false;
  }
  ensure_blit_vao() {
    if (this.blitVao)
      return;
    const vao = new VertexArray(this.gl);
    const posBuf = vao.buffer(this.blitShader.attribs["a_position"], 2);
    posBuf.set(new Float32Array([
      -1,
      -1,
      1,
      -1,
      -1,
      1,
      -1,
      1,
      1,
      -1,
      1,
      1
    ]));
    const uvBuf = vao.buffer(this.blitShader.attribs["a_uv"], 2);
    uvBuf.set(new Float32Array([
      0,
      0,
      1,
      0,
      0,
      1,
      0,
      1,
      1,
      0,
      1,
      1
    ]));
    this.blitVao = vao;
  }
  draw_drag_cache() {
    if (!this.useDragCache || !this.dragCacheTex)
      return false;
    const gl = this.gl;
    this.ensure_blit_vao();
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    this.blitShader.bind();
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.dragCacheTex);
    gl.uniform1i(gl.getUniformLocation(this.blitShader.program, "u_tex"), 0);
    this.blitVao.bind();
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    gl.bindTexture(gl.TEXTURE_2D, null);
    gl.enable(gl.BLEND);
    gl.enable(gl.DEPTH_TEST);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    return true;
  }
  render_static_scene(total, skippedOwners) {
    if (this.gridVertexCount > 0) {
      this.pointShader.bind();
      this.pointShader.uniforms["u_matrix"].mat3f(false, total.elements);
      this.pointShader.uniforms["u_pointSize"].f1(2 * window.devicePixelRatio);
      this.pointShader.uniforms["u_color"].f4(1, 1, 1, 0.15);
      this.gridVao.bind();
      this.gl.drawArrays(this.gl.POINTS, 0, this.gridVertexCount);
    }
    for (const layer of this.layers.values()) {
      layer.render(this.polylineShader, this.polygonShader, total, 1, skippedOwners);
    }
  }
  /** Build grid vertex data for the visible area */
  updateGrid(viewBBox, spacing) {
    const maxDots = 1e5;
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
      this.gridPosBuf = this.gridVao.buffer(this.pointShader.attribs["a_position"], 2);
    }
    this.gridPosBuf.set(data.subarray(0, i));
    this.gridVertexCount = i / 2;
  }
  /** Draw all layers with the given camera transform */
  draw(cameraMatrix) {
    this.clear();
    const total = this.projection_matrix.multiply(cameraMatrix);
    const drewCache = this.draw_drag_cache();
    if (!drewCache) {
      this.render_static_scene(total);
    }
    for (const layer of this.dynamicLayers) {
      layer.render(this.polylineShader, this.polygonShader, total, 1);
    }
  }
};

// src/geometry.ts
var DEG_TO_RAD = Math.PI / 180;
function fpTransform(fpAt, localX, localY) {
  const rad = -(fpAt.r || 0) * DEG_TO_RAD;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return new Vec2(
    fpAt.x + localX * cos - localY * sin,
    fpAt.y + localX * sin + localY * cos
  );
}
function padTransform(fpAt, padAt, localX, localY) {
  const padRad = -(padAt.r || 0) * DEG_TO_RAD;
  const cos = Math.cos(padRad);
  const sin = Math.sin(padRad);
  const px = localX * cos - localY * sin;
  const py = localX * sin + localY * cos;
  return fpTransform(fpAt, padAt.x + px, padAt.y + py);
}
function rotatedRectExtents(width, height, rotationDeg) {
  const theta = -(rotationDeg || 0) * DEG_TO_RAD;
  const absCos = Math.abs(Math.cos(theta));
  const absSin = Math.abs(Math.sin(theta));
  return [
    width * absCos + height * absSin,
    width * absSin + height * absCos
  ];
}

// src/colors.ts
var UNKNOWN_LAYER_COLOR = [0.5, 0.5, 0.5, 0.5];
var ZONE_COLOR_ALPHA = 0.25;
function getLayerColor(layer, layerById) {
  if (!layer)
    return UNKNOWN_LAYER_COLOR;
  const fromModel = layerById?.get(layer)?.color;
  if (fromModel)
    return fromModel;
  return UNKNOWN_LAYER_COLOR;
}

// src/hit-test.ts
var bboxCache = /* @__PURE__ */ new WeakMap();
function footprintBBox(fp) {
  const cached = bboxCache.get(fp);
  if (cached && cached.x === fp.at.x && cached.y === fp.at.y && cached.r === fp.at.r) {
    return cached.bbox;
  }
  const points = [];
  for (const pad of fp.pads) {
    const hw = pad.size.w / 2;
    const hh = pad.size.h / 2;
    points.push(padTransform(fp.at, pad.at, -hw, -hh));
    points.push(padTransform(fp.at, pad.at, hw, -hh));
    points.push(padTransform(fp.at, pad.at, hw, hh));
    points.push(padTransform(fp.at, pad.at, -hw, hh));
  }
  for (const drawing of fp.drawings) {
    switch (drawing.type) {
      case "line":
        points.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
        points.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        break;
      case "arc":
        points.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
        points.push(fpTransform(fp.at, drawing.mid.x, drawing.mid.y));
        points.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        break;
      case "circle":
        points.push(fpTransform(fp.at, drawing.center.x, drawing.center.y));
        points.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        break;
      case "rect":
        points.push(fpTransform(fp.at, drawing.start.x, drawing.start.y));
        points.push(fpTransform(fp.at, drawing.end.x, drawing.end.y));
        break;
      case "polygon":
      case "curve":
        for (const p of drawing.points) {
          points.push(fpTransform(fp.at, p.x, p.y));
        }
        break;
    }
  }
  const bbox = points.length === 0 ? new BBox(fp.at.x - 1, fp.at.y - 1, 2, 2) : BBox.from_points(points).grow(0.2);
  bboxCache.set(fp, { x: fp.at.x, y: fp.at.y, r: fp.at.r, bbox });
  return bbox;
}
function bboxIntersects(a, b) {
  return !(a.x2 < b.x || b.x2 < a.x || a.y2 < b.y || b.y2 < a.y);
}
function hitTestFootprintsInBox(selectionBox, footprints) {
  const hits = [];
  for (let i = 0; i < footprints.length; i++) {
    const bbox = footprintBBox(footprints[i]);
    if (bboxIntersects(selectionBox, bbox)) {
      hits.push(i);
    }
  }
  return hits;
}

// src/pad_annotations.ts
var PAD_ANNOTATION_BOX_RATIO = 0.78;
var PAD_ANNOTATION_MAJOR_FIT = 0.96;
var PAD_ANNOTATION_MINOR_FIT = 0.88;
var PAD_ANNOTATION_CHAR_SCALE = 0.6;
var PAD_ANNOTATION_MIN_CHAR_H = 0.02;
var PAD_ANNOTATION_CHAR_W_RATIO = 0.72;
var PAD_ANNOTATION_LINE_SPACING = 1.08;
var PAD_ANNOTATION_STROKE_SCALE = 0.22;
var PAD_ANNOTATION_STROKE_MIN = 0.02;
var PAD_ANNOTATION_STROKE_MAX = 0.16;
var PAD_NUMBER_BADGE_SIZE_RATIO = 0.36;
var PAD_NUMBER_BADGE_MARGIN_RATIO = 0.05;
var PAD_NUMBER_CHAR_SCALE = 0.8;
var PAD_NUMBER_MIN_CHAR_H = 0.04;
function estimateStrokeTextAdvance(text) {
  if (!text)
    return 0.6;
  const narrow = /* @__PURE__ */ new Set(["1", "I", "i", "l", "|", "!", ".", ",", ":", ";", "'", "`"]);
  const wide = /* @__PURE__ */ new Set(["M", "W", "@", "%", "#"]);
  let advance = 0;
  for (const ch of text) {
    if (ch === " ")
      advance += 0.6;
    else if (narrow.has(ch))
      advance += 0.45;
    else if (wide.has(ch))
      advance += 0.95;
    else
      advance += 0.72;
  }
  return Math.max(advance, 0.6);
}
function fitTextInsideBox(text, boxW, boxH, minCharH = PAD_ANNOTATION_MIN_CHAR_H, charScale = PAD_ANNOTATION_CHAR_SCALE) {
  if (boxW <= 0 || boxH <= 0)
    return null;
  const lines = text.split("\n").map((line) => line.trim()).filter((line) => line.length > 0);
  if (lines.length === 0)
    return null;
  const usableW = Math.max(0, boxW * PAD_ANNOTATION_BOX_RATIO);
  const usableH = Math.max(0, boxH * PAD_ANNOTATION_BOX_RATIO);
  if (usableW <= 0 || usableH <= 0)
    return null;
  const vertical = usableH > usableW;
  const major = vertical ? usableH : usableW;
  const minor = vertical ? usableW : usableH;
  const maxAdvance = Math.max(...lines.map(estimateStrokeTextAdvance));
  const lineHeightUnits = 1 + (lines.length - 1) * PAD_ANNOTATION_LINE_SPACING;
  const maxHByWidth = major / Math.max(maxAdvance * PAD_ANNOTATION_CHAR_W_RATIO, 1e-6);
  const maxHByHeight = minor / Math.max(lineHeightUnits, 1e-6);
  let charH = Math.min(
    maxHByWidth * PAD_ANNOTATION_MAJOR_FIT,
    maxHByHeight * PAD_ANNOTATION_MINOR_FIT
  );
  charH *= charScale;
  if (charH < minCharH)
    return null;
  const charW = charH * PAD_ANNOTATION_CHAR_W_RATIO;
  const thickness = Math.min(
    PAD_ANNOTATION_STROKE_MAX,
    Math.max(PAD_ANNOTATION_STROKE_MIN, charH * PAD_ANNOTATION_STROKE_SCALE)
  );
  return [charW, charH, thickness];
}
function fitPadNameLabel(text, boxW, boxH) {
  const displayText = text.trim();
  if (!displayText)
    return null;
  const candidates = [displayText];
  const dashIndexes = [];
  for (let i = 0; i < displayText.length; i++) {
    if (displayText[i] === "-")
      dashIndexes.push(i);
  }
  for (const idx of dashIndexes) {
    const left = displayText.slice(0, idx).trim();
    const right = displayText.slice(idx + 1).trim();
    if (!left || !right)
      continue;
    candidates.push(`${left}
${right}`);
  }
  let best = null;
  for (const candidate of candidates) {
    const fit = fitTextInsideBox(candidate, boxW, boxH);
    if (!fit)
      continue;
    if (!best || fit[1] > best[1][1]) {
      best = [candidate, fit];
    }
  }
  return best;
}
function padLabelWorldRotation(totalPadRotationDeg, padW, padH) {
  if (padW <= 0 || padH <= 0)
    return 0;
  if (Math.abs(padW - padH) <= 1e-6)
    return 0;
  const longAxisDeg = padW > padH ? totalPadRotationDeg : totalPadRotationDeg + 90;
  const axisX = Math.abs(Math.cos(longAxisDeg * Math.PI / 180));
  const axisY = Math.abs(Math.sin(longAxisDeg * Math.PI / 180));
  return axisY > axisX ? 90 : 0;
}
function resolvePad(fp, padIndex, padName) {
  const byIndex = fp.pads[padIndex];
  if (byIndex && byIndex.name === padName) {
    return byIndex;
  }
  for (const pad of fp.pads) {
    if (pad.name === padName)
      return pad;
  }
  return null;
}
var annotationCache = /* @__PURE__ */ new WeakMap();
function buildPadAnnotationGeometry(fp, hiddenLayers) {
  const hidden = hiddenLayers ?? /* @__PURE__ */ new Set();
  const cached = annotationCache.get(fp);
  let layerGeometry = cached?.layerGeometry;
  const cacheValid = !!cached && cached.x === fp.at.x && cached.y === fp.at.y && cached.r === fp.at.r;
  if (!cacheValid || !layerGeometry) {
    layerGeometry = /* @__PURE__ */ new Map();
    const ensureLayerGeometry = (layerName) => {
      let entry = layerGeometry.get(layerName);
      if (!entry) {
        entry = { names: [], numbers: [] };
        layerGeometry.set(layerName, entry);
      }
      return entry;
    };
    for (const annotation of fp.pad_names) {
      if (!annotation.text.trim())
        continue;
      const pad = resolvePad(fp, annotation.pad_index, annotation.pad);
      if (!pad)
        continue;
      const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
      const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
      const fitted = fitPadNameLabel(annotation.text, bboxW, bboxH);
      if (!fitted)
        continue;
      const [displayText, [charW, charH, thickness]] = fitted;
      const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
      const textRotation = padLabelWorldRotation(totalRotation, pad.size.w, pad.size.h);
      for (const layerName of annotation.layer_ids) {
        ensureLayerGeometry(layerName).names.push({
          text: displayText,
          x: worldCenter.x,
          y: worldCenter.y,
          rotation: textRotation,
          charW,
          charH,
          thickness
        });
      }
    }
    for (const annotation of fp.pad_numbers) {
      if (!annotation.text.trim())
        continue;
      const pad = resolvePad(fp, annotation.pad_index, annotation.pad);
      if (!pad)
        continue;
      const totalRotation = (fp.at.r || 0) + (pad.at.r || 0);
      const [bboxW, bboxH] = rotatedRectExtents(pad.size.w, pad.size.h, totalRotation);
      const badgeDiameter = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_SIZE_RATIO, 0.18);
      const badgeRadius = badgeDiameter / 2;
      const margin = Math.max(Math.min(bboxW, bboxH) * PAD_NUMBER_BADGE_MARGIN_RATIO, 0.03);
      const worldCenter = fpTransform(fp.at, pad.at.x, pad.at.y);
      const badgeCenterX = worldCenter.x - bboxW / 2 + margin + badgeRadius;
      const badgeCenterY = worldCenter.y - bboxH / 2 + margin + badgeRadius;
      const labelFit = fitTextInsideBox(
        annotation.text,
        badgeDiameter * 0.92,
        badgeDiameter * 0.92,
        PAD_NUMBER_MIN_CHAR_H,
        PAD_NUMBER_CHAR_SCALE
      );
      for (const layerName of annotation.layer_ids) {
        ensureLayerGeometry(layerName).numbers.push({
          text: annotation.text,
          badgeCenterX,
          badgeCenterY,
          badgeRadius,
          labelFit
        });
      }
    }
    annotationCache.set(fp, {
      x: fp.at.x,
      y: fp.at.y,
      r: fp.at.r,
      layerGeometry
    });
  }
  if (hidden.size === 0)
    return layerGeometry;
  const filtered = /* @__PURE__ */ new Map();
  for (const [layerName, geom] of layerGeometry.entries()) {
    if (!hidden.has(layerName)) {
      filtered.set(layerName, geom);
    }
  }
  return filtered;
}

// src/kicad_newstroke_glyphs.ts
var shared_glyphs = ["E_JSZS", "G][EI`", "H\\KFXFQNTNVOWPXRXWWYVZT[N[LZKY", "I[MUWU RK[RFY[", "G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP", "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH", "H[MPTP RW[M[MFWF", "G]L[LF RLPXP RX[XF", "MWR[RF", "G\\L[LF RX[OO RXFLR", "F^K[KFRUYFY[", "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF", "G\\L[LFTFVGWHXJXMWOVPTQLQ", "JZLFXF RR[RF", "H\\KFY[ RYFK[", "I[RQR[ RKFRQYF", "NVPESH", "HZVZT[P[NZMYLWLQMONNPMTMVN", "MWRMR_QaObNb RRFQGRHSGRFRH", "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[", "JZMMR[WM", "G]JMN[RQV[ZM", "H\\RbRD", "F^K[KFYFY[K[", "RR", "NVTEQH", "JZRRQSRTSSRRRT", "MWR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA", "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RIPQP", "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEQH", "I[MUWU RK[RFY[ RN>O@QASAU@V>", "IZNMN[ RPSV[ RVMNU", "G]KPYP RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF", "I[NNPMTMVNWPWXVZT[P[NZMXMVWT", "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[", "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN", "MXRMRXSZU[", "H[LTWT RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[", "G]RFRb RPMTMVNXPYRYVXXVZT[P[NZLXKVKRLPNNPM", "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEQH", "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEQH", "I\\NMN[ RNOONQMTMVNWPWb RTEQH", "MXRMRXSZU[ RTEQH", "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM", "H[MMMXNZP[S[UZVYWWWPVNUM RTEQH", "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEQH", "LXOTUT", "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RPQRPTQUSTURVPUOSPQ", "Pf"];
var glyph_data = [
  "JZ",
  "MWRYSZR[QZRYR[ RRSQGRFSGRSRF",
  "JZNFNJ RVFVJ",
  "H]LM[M RRDL_ RYVJV RS_YD",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RRCR^",
  "F^J[ZF RMFOGPIOKMLKKJIKGMF RYZZXYVWUUVTXUZW[YZ",
  "E_[[Z[XZUWPQNNMKMINGPFQFSGTITJSLRMLQKRJTJWKYLZN[Q[SZTYWUXRXP",
  "MWSFQJ",
  "KYVcUbS_R]QZPUPQQLRISGUDVC",
  "KYNcObQ_R]SZTUTQSLRIQGODNC",
  "JZRFRK RMIRKWI ROORKUO",
  "E_JSZS RR[RK",
  "MWSZS[R]Q^",
  0,
  "MWRYSZR[QZRYR[",
  1,
  "H\\QFSFUGVHWJXNXSWWVYUZS[Q[OZNYMWLSLNMJNHOGQF",
  "H\\X[L[ RR[RFPINKLL",
  "H\\LHMGOFTFVGWHXJXLWOK[X[",
  2,
  "H\\VMV[ RQELTYT",
  "H\\WFMFLPMOONTNVOWPXRXWWYVZT[O[MZLY",
  "H\\VFRFPGOHMKLOLWMYNZP[T[VZWYXWXRWPVOTNPNNOMPLR",
  "H\\KFYFP[",
  "H\\PONNMMLKLJMHNGPFTFVGWHXJXKWMVNTOPONPMQLSLWMYNZP[T[VZWYXWXSWQVPTO",
  "H\\N[R[TZUYWVXRXJWHVGTFPFNGMHLJLOMQNRPSTSVRWQXO",
  "MWRYSZR[QZRYR[ RRNSORPQORNRP",
  "MWSZS[R]Q^ RRNSORPQORNRP",
  "E_ZMJSZY",
  "E_JPZP RZVJV",
  "E_JMZSJY",
  "I[QYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS",
  "D_VQUPSOQOOPNQMSMUNWOXQYSYUXVW RVOVWWXXXZW[U[PYMVKRJNKKMIPHTIXK[N]R^V]Y[",
  3,
  4,
  5,
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[",
  6,
  "HZTPMP RM[MFWF",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR",
  7,
  8,
  "JZUFUUTXRZO[M[",
  9,
  "HYW[M[MF",
  10,
  "G]L[LFX[XF",
  11,
  12,
  "G]Z]X\\VZSWQVOV RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG",
  13,
  "G]LFLWMYNZP[T[VZWYXWXF",
  "I[KFR[YF",
  "F^IFN[RLV[[F",
  14,
  15,
  "H\\KFYFK[Y[",
  "KYVbQbQDVD",
  "KYID[_",
  "KYNbSbSDND",
  "LXNHREVH",
  "JZJ]Z]",
  16,
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ",
  17,
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT",
  "MYOMWM RR[RISGUFWF",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN",
  "H[M[MF RV[VPUNSMPMNNMO",
  "MWR[RM RRFQGRHSGRFRH",
  18,
  "IZN[NF RPSV[ RVMNU",
  "MXU[SZRXRF",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[",
  "I\\NMN[ RNOONQMTMVNWPW[",
  19,
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ",
  "I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN",
  "KXP[PM RPQQORNTMVM",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN",
  "MYOMWM RRFRXSZU[W[",
  "H[VMV[ RMMMXNZP[S[UZVY",
  20,
  21,
  "IZL[WM RLMW[",
  "JZMMR[ RWMR[P`OaMb",
  "IZLMWML[W[",
  "KYVcUcSbR`RVQTOSQRRPRFSDUCVC",
  22,
  "KYNcOcQbR`RVSTUSSRRPRFQDOCNC",
  "KZMSNRPQTSVRWQ",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "JZ",
  "MWROQNRMSNRORM RRUSaRbQaRURb",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RRJR^",
  "H[LMTM RL[W[ RO[OIPGRFUFWG",
  "H]LYOV RLLOO RVVYY RVOYL RVVTWQWOVNTNQOOQNTNVOWQWTVV",
  "F^JTZT RJMZM RRQR[ RKFRQYF",
  "MWRbRW RRFRQ",
  "I[N]P^S^U]V[UYOSNQNPONQM RVGTFQFOGNIOKUQVSVTUVSW",
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH",
  "@dVKTJPJNKLMKOKSLUNWPXTXVW RRCMDHGELDQEVH[M^R_W^\\[_V`Q_L\\GWDRC",
  "KZOEQDSDUEVGVN RVMTNQNOMNKOIQHVH",
  "H\\RMLSRY RXWTSXO",
  "E_JQZQZV",
  24,
  "@dWXRR RNXNJTJVKWMWOVQTRNR RRCMDHGELDQEVH[M^R_W^\\[_V`Q_L\\GWDRC",
  "LXMGWG",
  "JZRFPGOIPKRLTKUITGRF",
  "E_JOZO RRWRG RZ[J[",
  "JZNAP@S@UAVCVEUGNNVN",
  "JZN@V@RESEUFVHVKUMSNPNNM",
  25,
  "H^MMMb RWXXZZ[ RMXNZP[T[VZWXWM",
  "F]VMV[ ROMOXNZL[ RZMMMKNJP",
  26,
  "MWR\\T]U_TaRbOb",
  "JZVNNN RNCPBR@RN",
  "KYQNOMNKNGOEQDSDUEVGVKUMSNQN",
  "H\\RMXSRY RLWPSLO",
  "G]KQYQ RVNNN RNCPBR@RN RUYUa RQSN]W]",
  "G]KQYQ RVNNN RNCPBR@RN RNTPSSSUTVVVXUZNaVa",
  "G]KQYQ RN@V@RESEUFVHVKUMSNPNNM RUYUa RQSN]W]",
  "I[SORNSMTNSOSM RWaUbPbNaM_M]N[OZQYRXSVSU",
  "I[MUWU RK[RFY[ RP>SA",
  "I[MUWU RK[RFY[ RT>QA",
  "I[MUWU RK[RFY[ RNAR>VA",
  "I[MUWU RK[RFY[ RMAN@P?TAV@W?",
  "I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "I[MUWU RK[RFY[ RRFPEOCPAR@TAUCTERF",
  "F`JURU RRPYP RH[OF\\F RRFR[\\[",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb",
  "H[MPTP RW[M[MFWF RP>SA",
  "H[MPTP RW[M[MFWF RT>QA",
  "H[MPTP RW[M[MFWF RNAR>VA",
  "H[MPTP RW[M[MFWF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "MWR[RF RP>SA",
  "MWR[RF RT>QA",
  "MWR[RF RNAR>VA",
  27,
  28,
  "G]L[LFX[XF RMAN@P?TAV@W?",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RP>SA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RT>QA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W?",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "E_LMXY RXMLY",
  "G]ZFJ[ RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[",
  "G]LFLWMYNZP[T[VZWYXWXF RP>SA",
  "G]LFLWMYNZP[T[VZWYXWXF RT>QA",
  "G]LFLWMYNZP[T[VZWYXWXF RNAR>VA",
  "G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "I[RQR[ RKFRQYF RT>QA",
  "G\\LFL[ RLKTKVLWMXOXRWTVUTVLV",
  "F]K[KJLHMGOFRFTGUHVJVMSMQNPPPQQSSTVTXUYWYXXZV[R[PZ",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RPESH",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RTEQH",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RMHNGPFTHVGWF",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRHPGOEPCRBTCUETGRH",
  "D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RPESH",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RTEQH",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "MWR[RM RPESH",
  "MWR[RM RTEQH",
  "LXNHREVH RR[RM",
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RR[RM",
  "I\\SCQI RWNUMQMONNOMQMXNZP[T[VZWXWLVITGRFNE",
  "I\\NMN[ RNOONQMTMVNWPW[ RMHNGPFTHVGWF",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RPESH",
  29,
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "E_ZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN",
  "H[XMK[ RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[",
  "H[VMV[ RMMMXNZP[S[UZVY RPESH",
  "H[VMV[ RMMMXNZP[S[UZVY RTEQH",
  "H[VMV[ RMMMXNZP[S[UZVY RNHREVH",
  "H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "JZMMR[ RWMR[P`OaMb RTEQH",
  "H[MFMb RMNOMSMUNVOWQWWVYUZS[O[MZ",
  "JZMMR[ RWMR[P`OaMb RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I[MUWU RK[RFY[ RM@W@",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RMGWG",
  30,
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE",
  "I[MUWU RK[RFY[ RY[W]V_WaYb[b",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RW[U]T_UaWbYb",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RT>QA",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RTEQH",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RNAR>VA",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RNHREVH",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR?Q@RAS@R?RA",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RRFQGRHSGRFRH",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RN>RAV>",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RNERHVE",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RN>RAV>",
  "IfW[WF RWZU[Q[OZNYMWMQNOONQMUMWN RbF`J",
  28,
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RRHZH",
  "H[MPTP RW[M[MFWF RM@W@",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG",
  "H[MPTP RW[M[MFWF RN>O@QASAU@V>",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNEOGQHSHUGVE",
  "H[MPTP RW[M[MFWF RR?Q@RAS@R?RA",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRFQGRHSGRFRH",
  "H[MPTP RW[M[MFWF RR[P]O_PaRbTb",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR[P]O_PaRbTb",
  "H[MPTP RW[M[MFWF RN>RAV>",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNERHVE",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RNAR>VA",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNHREVH",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RN>O@QASAU@V>",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNEOGQHSHUGVE",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RR?Q@RAS@R?RA",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RRFQGRHSGRFRH",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RR\\T]U_TaRbOb",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RRGPFODPBRAUA",
  "G]L[LF RLPXP RX[XF RNAR>VA",
  "H[M[MF RV[VPUNSMPMNNMO RIAM>QA",
  "G]IJ[J RL[LF RLPXP RX[XF",
  "H[M[MF RV[VPUNSMPMNNMO RJHRH",
  "MWR[RF RMAN@P?TAV@W?",
  "MWR[RM RMHNGPFTHVGWF",
  "MWR[RF RM@W@",
  "MWR[RM RMGWG",
  "MWR[RF RN>O@QASAU@V>",
  "MWR[RM RNEOGQHSHUGVE",
  "MWR[RF RR[P]O_PaRbTb",
  "MWR[RM RR[P]O_PaRbTb",
  "MWR[RF RR?Q@RAS@R?RA",
  "MWR[RM",
  "MgR[RF RbFbUaX_Z\\[Z[",
  "MaR[RM RRFQGRHSGRFRH R\\M\\_[aYbXb R\\F[G\\H]G\\F\\H",
  "JZUFUUTXRZO[M[ RQAU>YA",
  "MWRMR_QaObNb RNHREVH",
  "G\\L[LF RX[OO RXFLR RR\\T]U_TaRbOb",
  "IZN[NF RPSV[ RVMNU RR\\T]U_TaRbOb",
  31,
  "HYW[M[MF RO>LA",
  "MXU[SZRXRF RTEQH",
  "HYW[M[MF RR\\T]U_TaRbOb",
  "MXU[SZRXRF RR\\T]U_TaRbOb",
  "HYW[M[MF RVHSK",
  "M^U[SZRXRF RZFXJ",
  "HYW[M[MF RUNTOUPVOUNUP",
  "M\\U[SZRXRF RYOZPYQXPYOYQ",
  "HYW[M[MF RJQPM",
  "MXU[SZRXRF ROQUM",
  "G]L[LFX[XF RT>QA",
  "I\\NMN[ RNOONQMTMVNWPW[ RTEQH",
  "G]L[LFX[XF RR\\T]U_TaRbOb",
  "I\\NMN[ RNOONQMTMVNWPW[ RR\\T]U_TaRbOb",
  "G]L[LFX[XF RN>RAV>",
  "I\\NMN[ RNOONQMTMVNWPW[ RNERHVE",
  "MjSFQJ R\\M\\[ R\\O]N_MbMdNePe[",
  "G]LFL[ RLINGPFTFVGWHXJX^W`VaTbQb",
  "I\\NMN[ RNOONQMTMVNWPW_VaTbRb",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN>O@QASAU@V>",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNEOGQHSHUGVE",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RQ>NA RX>UA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQENH RXEUH",
  "E`RPYP RRFR[ R\\FNFLGJIIMITJXLZN[\\[",
  "C`[ZY[U[SZRXRPSNUMYM[N\\P\\RRT RRQQOPNNMKMINHOGQGWHYIZK[N[PZQYRW",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RT>QA",
  "KXP[PM RPQQORNTMVM RTEQH",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RR\\T]U_TaRbOb",
  "KXP[PM RPQQORNTMVM RR\\T]U_TaRbOb",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RN>RAV>",
  "KXP[PM RPQQORNTMVM RNERHVE",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RT>QA",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RTEQH",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RNAR>VA",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNHREVH",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR\\T]U_TaRbOb",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RR\\T]U_TaRbOb",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RN>RAV>",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNERHVE",
  "JZLFXF RR[RF RR\\T]U_TaRbOb",
  "MYOMWM RRFRXSZU[W[ RR\\T]U_TaRbOb",
  "JZLFXF RR[RF RN>RAV>",
  "M[OMWM RYFXI RRFRXSZU[W[",
  "JZLFXF RR[RF RNQVQ",
  "MYOMWM RRFRXSZU[W[ ROSUS",
  "G]LFLWMYNZP[T[VZWYXWXF RMAN@P?TAV@W?",
  "H[VMV[ RMMMXNZP[S[UZVY RMHNGPFTHVGWF",
  "G]LFLWMYNZP[T[VZWYXWXF RM@W@",
  "H[VMV[ RMMMXNZP[S[UZVY RMGWG",
  "G]LFLWMYNZP[T[VZWYXWXF RN>O@QASAU@V>",
  "H[VMV[ RMMMXNZP[S[UZVY RNEOGQHSHUGVE",
  "G]LFLWMYNZP[T[VZWYXWXF RRAP@O>P<R;T<U>T@RA",
  "H[VMV[ RMMMXNZP[S[UZVY RRHPGOEPCRBTCUETGRH",
  "G]LFLWMYNZP[T[VZWYXWXF RQ>NA RX>UA",
  "H[VMV[ RMMMXNZP[S[UZVY RQENH RXEUH",
  "G]LFLWMYNZP[T[VZWYXWXF RR[P]O_PaRbTb",
  "H[VMV[ RMMMXNZP[S[UZVY RV[T]S_TaVbXb",
  "F^IFN[RLV[[F RNAR>VA",
  "G]JMN[RQV[ZM RNHREVH",
  "I[RQR[ RKFRQYF RNAR>VA",
  "JZMMR[ RWMR[P`OaMb RNHREVH",
  "JZLFXF RR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "H\\KFYFK[Y[ RT>QA",
  "IZLMWML[W[ RTEQH",
  "H\\KFYFK[Y[ RR?Q@RAS@R?RA",
  "IZLMWML[W[ RRFQGRHSGRFRH",
  "H\\KFYFK[Y[ RN>RAV>",
  "IZLMWML[W[ RNERHVE",
  "MYR[RISGUFWF",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RJHRH",
  "C\\LFL[T[VZWYXWXTWRVQSPLP RFKFIGGIFSFUGVHWJWLVNUOSP",
  "G\\VFLFL[R[UZWXXVXSWQUORNLN",
  "H[WFMFM[ RMNOMSMUNVOWQWWVYUZS[O[MZ",
  "H]MFM[S[VZXXYVYSXQVOSNMN",
  "IZNMN[S[UZVXVUUSSRNR",
  "I^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZMY",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RMHKGJEKCLB",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RTMTIUGWFYF",
  28,
  "C\\FKFIGGIFQFTGVIWKXOXRWVVXTZQ[L[LF",
  "H]NFXFX[R[OZMXLVLSMQOORNXN",
  "I\\MFWFW[ RWNUMQMONNOMQMWNYOZQ[U[WZ",
  "I\\Q[T[VZWYXWXQWOVNTMQMONNOMQMWNYOZQ[T\\V]W_VaTbPbNa",
  "I\\WPPP RM[W[WFMF",
  "F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP",
  "G[PPTP RWGUFPFNGMHLJLLMNNOPPMQLRKTKWLYMZO[U[WZ",
  "HZTPMP RM[MFWF RM[M_LaJbHb",
  "MYOMWM RR[RISGUFWF RR[R_QaObMb",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RMHKGJEKCLB",
  "I[KFU[U_TaRbPaO_O[YF",
  "D`I[IF RIOJNLMOMQNRPRXSZU[X[ZZ[Y\\W\\P[NZM",
  "MZRFRWSYTZV[X[",
  "MWR[RF RNPVP",
  "G_L[LF RX[OO RLRWGYF[G\\I\\K",
  "IZNMN[ RPSV[ RVMNU RNMNIOGQFSF",
  "MXU[SZRXRF RNOVO",
  "JZRMM[ RMFOFPGRMW[ RNLTH",
  "Ca\\F\\[ R\\XZZX[V[TZSYRWRF RRWQYPZN[L[JZIYHWHF",
  "G]L[LFX[XF RL[L_KaIbGb",
  "I\\NMN[ RNOONQMTMVNWPWb",
  32,
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH",
  "DaSGQFMFKGIIHMHTIXKZM[Q[SZUXVTVMUISGUFYF[G\\I\\b",
  "E^RNPMMMKNJOIQIWJYKZM[P[RZSYTWTQSORNTMVMXNYPYb",
  "C\\LFL[ RFKFIGGIFTFVGWHXJXMWOVPTQLQ",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RRMRISGUFWF",
  "G\\LFL[ RQVXb RLKTKVLWMXOXRWTVUTVLV",
  "H\\XZU[P[NZMYLWLUMSNRPQTPVOWNXLXJWHVGTFOFLG",
  "IZVZT[P[NZMXMWNUPTSTUSVQVPUNSMPMNN",
  "H[W[L[SPLFWF",
  "JYWbUbSaR_RIQGOFMGLIMKOLQKRI",
  "MYOMWM RRFRXSZU[W[ RW[W_VaTbRb",
  "HZR[RF RKKKILGNFXF",
  "MYOMWM RWFUFSGRIRXSZU[W[",
  "JZLFXF RR[RF RR[R_SaUbWb",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG",
  "F^ZFUFUJWKYMZPZUYXWZT[P[MZKXJUJPKMMKOJOFJF",
  "G]LFLWMYNZP[T[VZXXYVYIXGWF",
  "I`RQR[ RKFRQXGZF\\G]I]K",
  "J^MMR[ RMbOaP`R[VNXMZN[P[R",
  "H\\KFYFK[Y[ RNPVP",
  "IZLMWML[W[ RNTVT",
  2,
  "H\\YFLFSNPNNOMPLRLWMYNZP[V[XZYY",
  "JZWMNMUVRVPWOXNZN^O`PaRbUbWa",
  "JZMMVMOTSTUUVWVXUZS[Q[O\\N^N_OaQbVb",
  "H\\LHMGOFTFVGWHXJXLWOK[X[ RNSVS",
  "H\\WFMFLPMOONTNVOWPXRXWWYVZT[O[MZLY",
  "JZVMOMNSPRSRUSVUVXUZS[P[NZ",
  "J^MZP[T[WZYXZVZSYQWOTNPNPF RLITI",
  "H[MMMb RMONNPMTMVNWPWSVUM^",
  "MWRFRb",
  "JZOFOb RUFUb",
  "MWRFRb ROWUW ROQUQ",
  "MWRYSZR[QZRYR[ RRSQGRFSGRSRF",
  "GpL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_FmF_[m[ Rb>fAj>",
  "GmL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_MjM_[j[ RaEeHiE",
  "ImW[WF RWZU[Q[OZNYMWMQNOONQMUMWN R_MjM_[j[ RaEeHiE",
  "HiW[M[MF RdFdUcXaZ^[\\[",
  "HcW[M[MF R^M^_]a[bZb R^F]G^H_G^F^H",
  "MbU[SZRXRF R]M]_\\aZbYb R]F\\G]H^G]F]H",
  "GmL[LFX[XF RhFhUgXeZb[`[",
  "GgL[LFX[XF RbMb_aa_b^b RbFaGbHcGbFbH",
  "IfNMN[ RNOONQMTMVNWPW[ RaMa_`a^b]b RaF`GaHbGaFaH",
  "I[MUWU RK[RFY[ RN>RAV>",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNERHVE",
  "MWR[RF RN>RAV>",
  "MWR[RM RNERHVE",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN>RAV>",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNERHVE",
  "G]LFLWMYNZP[T[VZWYXWXF RN>RAV>",
  "H[VMV[ RMMMXNZP[S[UZVY RNERHVE",
  "G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;",
  "H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@",
  "G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RT9Q<",
  "H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  "G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RN9R<V9",
  "H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RN>RAV>",
  "G]LFLWMYNZP[T[VZWYXWXF RN?O@NAM@N?NA RV?W@VAU@V?VA RP9S<",
  "H[VMV[ RMMMXNZP[S[UZVY RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA",
  33,
  "I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@",
  "I[MUWU RK[RFY[ RR?Q@RAS@R?RA RM;W;",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRFQGRHSGRFRH RM@W@",
  "F`JURU RRPYP RH[OF\\F RRFR[\\[ RO@Y@",
  "D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX RMGWG",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RSV[V",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RS^[^",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RN>RAV>",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RNERHVE",
  "G\\L[LF RX[OO RXFLR RN>RAV>",
  "IZN[NF RPSV[ RVMNU RJANDRA",
  "G]R[P]O_PaRbTb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF",
  "H[R[P]O_PaRbTb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[",
  "G]R[P]O_PaRbTb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@",
  "H[R[P]O_PaRbTb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG",
  "H\\KFXFQNTNVOWPXRXWWYVZT[N[LZKY RN>RAV>",
  "JZMMVMOVRVTWUXVZV^U`TaRbObMa RNERHVE",
  "MWRMR_QaObNb RNERHVE",
  "GpL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_FmF_[m[",
  "GmL[LFQFTGVIWKXOXRWVVXTZQ[L[ R_MjM_[j[",
  "ImW[WF RWZU[Q[OZNYMWMQNOONQMUMWN R_MjM_[j[",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RT>QA",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RTEQH",
  "CaH[HF RHPTP RTFTXUZW[Z[\\Z]X]M",
  "G\\LFLb RLINGPFTFVGWHXJXOWRUUL^",
  "G]L[LFX[XF RP>SA",
  "I\\NMN[ RNOONQMTMVNWPW[ RPESH",
  "I[MUWU RK[RFY[ RZ9X< RR;P<O>P@RAT@U>T<R;",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RZ@XC RRBPCOEPGRHTGUETCRB",
  "F`JURU RRPYP RH[OF\\F RRFR[\\[ RV>SA",
  "D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX RTEQH",
  "G]ZFJ[ RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[ RT>QA",
  "H[XMK[ RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEQH",
  "I[MUWU RK[RFY[ ROAL> RVAS>",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR ROHLE RVHSE",
  "I[MUWU RK[RFY[ RNAO?Q>S>U?VA",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHOFQESEUFVH",
  "H[MPTP RW[M[MFWF ROAL> RVAS>",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT ROHLE RVHSE",
  "H[MPTP RW[M[MFWF RNAO?Q>S>U?VA",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHOFQESEUFVH",
  "MWR[RF ROAL> RVAS>",
  "MWR[RM ROHLE RVHSE",
  "MWR[RF RNAO?Q>S>U?VA",
  "MWR[RM RNHOFQESEUFVH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF ROAL> RVAS>",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ ROHLE RVHSE",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAO?Q>S>U?VA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHOFQESEUFVH",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ ROAL> RVAS>",
  "KXP[PM RPQQORNTMVM RPHME RWHTE",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RNAO?Q>S>U?VA",
  "KXP[PM RPQQORNTMVM ROHPFRETEVFWH",
  "G]LFLWMYNZP[T[VZWYXWXF ROAL> RVAS>",
  "H[VMV[ RMMMXNZP[S[UZVY ROHLE RVHSE",
  "G]LFLWMYNZP[T[VZWYXWXF RNAO?Q>S>U?VA",
  "H[VMV[ RMMMXNZP[S[UZVY RNHOFQESEUFVH",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RS`SaRcQd",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RS`SaRcQd",
  "JZLFXF RR[RF RS`SaRcQd",
  "MYOMWM RRFRXSZU[W[ RU`UaTcSd",
  "I]VRXTYVY[X]V_T`Lb RLHMGOFUFWGXHYJYNXPVRTSNU",
  "J[UWVXWZW]V_U`SaMb RMNOMSMUNVOWQWTVVUWSXOY",
  "G]L[LF RLPXP RX[XF RN>RAV>",
  "H[M[MF RV[VPUNSMPMNNMO RI>MAQ>",
  "G]L[LFX[XF RX[Xb",
  "IbWFWXXZZ[\\[^Z_X^V\\UZVV^ RWNUMQMONNOMQMWNYOZQ[T[VZWX",
  "G]NFLGKIKKLMMNOO RVFXGYIYKXMWNUO ROOUOWPXQYSYWXYWZU[O[MZLYKWKSLQMPOO",
  "J[MJMMNORQVOWMWJ RPQTQVRWTWXVZT[P[NZMXMTNRPQ",
  "H\\KFYFK[Y[ RY[Y_XaVbTb",
  "IZLMWML[W[ RW[W_VaTbRb",
  "I[MUWU RK[RFY[ RR?Q@RAS@R?RA",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRFQGRHSGRFRH",
  "H[MPTP RW[M[MFWF RR\\T]U_TaRbOb",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR\\T]U_TaRbOb",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA RM;W;",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH RM@W@",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RM;W;",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RM@W@",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RR?Q@RAS@R?RA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRFQGRHSGRFRH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RR?Q@RAS@R?RA RM;W;",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRFQGRHSGRFRH RM@W@",
  "I[RQR[ RKFRQYF RM@W@",
  "JZMMR[ RWMR[P`OaMb RMGWG",
  "M]RFRXSZU[W[YZZXYVWUUVQ^",
  "IbNMN[ RNOONQMTMVNWPWXXZZ[\\[^Z_X^V\\UZVV^",
  "M]OMWM RRFRXSZU[W[YZZXYVWUUVQ^",
  "MWRMR_QaObNb",
  "D`R[RF RRZP[L[JZIYHWHQIOJNLMPMRN RTMXMZN[O\\Q\\W[YZZX[T[RZ",
  "D`RMRb RRZP[L[JZIYHWHQIOJNLMPMRN RTMXMZN[O\\Q\\W[YZZX[T[RZ",
  "I[MUWU RK[RFY[ RXCL`",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RXCL`",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RWHM`",
  "HYW[M[MF RIOQO",
  "JZLFXF RR[RF RXCL`",
  "J[P[R^T_W_ RNZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN",
  "IZLMWML[N[P\\R^T_W_",
  "J^MGPFTFWGYIZKZNYPWRTSPSP[",
  "J^NNPMTMVNWOXQXSWUVVTWPWP[",
  "G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RIUOU",
  "G]IM[M RLFLWMYNZP[T[VZWYXWXF",
  "I[Y[RFK[",
  "H[MPTP RW[M[MFWF RXCL`",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RWHM`",
  "JZUFUUTXRZO[M[ RQPYP",
  "MWRMR_QaObNb ROTUT RRFQGRHSGRFRH",
  "G]XFX^Y`Za\\b^b RXIVGTFPFNGLIKMKTLXNZP[T[VZXX",
  "I\\WMW^X`Ya[b]b RWZU[Q[OZNYMWMQNOONQMUMWN",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RIQOQ",
  "KXP[PM RPQQORNTMVM RMTUT",
  "I[KIYI RRQR[ RKFRQYF",
  "JZLQXQ RMMR[ RWMR[P`OaMb",
  "H[MMMXNZP[T[VZ RMNOMTMVNWPWRVTTUOUMV",
  34,
  "G\\K[NQOOPNRMTMVNWOXRXVWYVZT[R[PZOYNWMPLNJM",
  "H[RFPFNGMIM[ RMNOMSMUNVOWQWWVYUZS[O[MZ",
  "J\\NNPMTMVNWOXQXWWYVZT[P[NZ",
  "HZVNTMPMNNMOLQLWMYNZP[S[UZVXUVSUQVM^",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RW[W_XaZb\\b",
  "I\\\\FZFXGWIW[ RWZU[Q[OZNYMWMQNOONQMUMWN",
  "I[NZP[T[VZWXWPVNTMPMNNMPMRWT",
  33,
  "IbNNPMTMVNWPWXVZT[P[NZMXMV\\S\\U]W_X`X",
  35,
  "J[TTVSWQWPVNTMPMNN RRTTTVUWWWXVZT[P[NZ",
  "JaRTTTVUWWWXVZT[P[NZ RNNPMTMVNWPWQVSTT[S[U\\W^X_X",
  "H[TTVSWQWPVNTMPMNNMOLRLVMYNZP[T[VZWXWWVUTTRT",
  "MWRMR_QaObNb ROTUT",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RWMWIXGZF\\F",
  "I\\WYVZT[P[NZMXMQNOONQMWMW^V`UaSbMb",
  "HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU",
  "JZMMU[U_TaRbPaO_O[WM",
  "JZMMTVUXTZR[PZOXPVWM",
  "I\\WMWb RNMNXOZQ[T[VZWY",
  "H[RFPFNGMIM[ RV[VPUNSMPMNNMO",
  "H[RFPFNGMIM[ RV[VPUNSMPMNNMO RV[V_UaSbQb",
  "MWR[RM ROTUT RRFQGRHSGRFRH",
  36,
  "MWR[RM RU[O[ RUMOM",
  "MXU[SZRXRF RMONNPMTOVNWM",
  "IYU[SZRXRF RRQQOONMOLQMSOTWT",
  "MXRFR_SaUbWb",
  "GZLFLXMZO[ RLMVMOVRVTWUXVZV^U`TaRbObMa",
  "D`[M[[ R[YZZX[U[SZRXRM RRXQZO[L[JZIXIM",
  "D`[M[[ R[YZZX[U[SZRXRM RRXQZO[L[JZIXIM R[[[b",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ R[[[_ZaXbVb",
  "I\\NMN[ RNOONQMTMVNWPW[ RN[N_MaKbIb",
  "I\\NMN[ RNOONQMTMVNWPW[ RW[W_XaZb\\b",
  "H[M[MMV[VM",
  37,
  "E]RTXT RRMR[ RZMMMKNJOIQIWJYKZM[Z[",
  "G]RTRXSZU[V[XZYXYQXOWNUMOMMNLOKQKXLZN[O[QZRX",
  38,
  "LYTMT[ RTWSYRZP[N[",
  "LYTMT[ RTWSYRZP[N[ RTMTF",
  "LYTMT[ RTWSYRZP[N[ RT[T_UaWbYb",
  "KXP[PM RPQQORNTMVM RP[Pb",
  "KXP[PM RPQQORNTMVM RP[P_QaSbUb",
  "KXM[S[ RVMTMRNQOPRP[",
  "LYW[Q[ RNMPMRNSOTRT[",
  "I[RUW[ RN[NMTMVNWPWRVTTUNU",
  "I[RSWM RNMN[T[VZWXWVVTTSNS",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RN[N_OaQbSb",
  "KYWFUFSGRIR_QaObMb",
  "MWRMR_QaObNb ROTUT RRMRISGUFWF",
  "KYMFOFQGRIRXSZU[W[",
  "KYWFUFSGRIR_QaObMaL_M]O\\V\\",
  "KWU[M[ RRbRPQNOMMM",
  "MYOMWM RRFR_SaUbWb",
  "H[JRYR RVMV[ RMMMXNZP[S[UZVY",
  "I\\XMUMUPWRXTXWWYVZT[Q[OZNYMWMTNRPPPMMM",
  "H[MMMXNZP[S[UZVYWWWPVNUM",
  "JZW[RMM[",
  "G]Z[VMRWNMJ[",
  "JZW[RM RM[RMTHUGWF",
  "KYRTR[ RMMRTWM",
  "IZLMWML[W[ RW[W_XaZb\\b",
  "IZLMWML[T[VZWXVVTURVN^",
  "JZMMVMOVRVTWUXVZV^U`TaRbObMa",
  "JZMMVMOVRVTWUXVZV^U`TaRbPbNaM_N]P\\R]Uc",
  "J^MGPFTFWGYIZKZNYPWRTSPSP[",
  "FZWGTFPFMGKIJKJNKPMRPSTST[",
  "J^MZP[T[WZYXZVZSYQWOTNPNPF",
  "F[WHVGSFQFNGLIKKJOJYK]L_NaQbSbVaW`",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RROQPRQSPRORQ",
  "I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT",
  "I\\PTNUMWMXNZP[T[VZWYXVXRWOVNTMPMNNMPMQNSPTRT",
  "HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU RUMUIVGXFZF",
  "H[MTVT RMMM[ RVMV[",
  "LXRMR_QaObMaL_M]O\\V\\ RRFQGRHSGRFRH",
  "J[VMVb RTUNM RN[VS",
  "JYOMO[V[",
  "I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN RWMWIXGZF\\F",
  "J^MGPFTFWGYIZKZNYPWRTSPSP[ RLXTX",
  "FZWGTFPFMGKIJKJNKPMRPSTST[ RPXXX",
  "D`R[RF RRM]MR[][ RRZP[L[JZIYHWHQIOJNLMPMRN",
  "E`RFR[ RRNPMMMKNJOIQIWJYKZM[P[RZ RRM\\MUVXVZW[X\\Z\\^[`ZaXbUbSa",
  "D`R[RF RRM]MR[Z[\\Z]X\\VZUXVT^ RRZP[L[JZIYHWHQIOJNLMPMRN",
  "G^IMQM RLFLXMZO[QZS[W[YZZXZWYUWTTTRSQQQPRNTMWMYN",
  "I[KMTM RNFNXOZQ[T[ RYFWFUGTIT_SaQbOb",
  "F^HMPM RKFKXLZN[P[RZ RZNXMTMRNQOPQPWQYRZT[W[YZZXYVWUUVQ^",
  "F]HMPMP[ RK[KILGNFPF RPOQNSMVMXNYPY_XaVbTb",
  "G^LFLXMZO[QZS[W[YZZXZWYUWTTTRSQQQPRNTMWMYN",
  "H^MM[MP[ RMFMXNZP[[[",
  "G]JSN[RUV[ZS RJFNNRHVNZF",
  "G]XXXSLSLX RXKXFLFLK",
  "I\\WMWb RNMNXOZQ[T[VZWY RNMNIMGKFIF",
  "I\\\\bZbXaW_WM RNMNXOZQ[T[VZWY RNMNIMGKFIF",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "H[MFM[ RXPMP",
  "IZNTVT RNMN[",
  "G]R[RF RKOKFYFYO",
  "I[R[RF RMOMFWFWO",
  "MWSFQJ",
  "MWS[Q_",
  "G]LFL[XFX[",
  "H\\MMM[WMW[",
  23,
  23,
  "NVR`RcSdTd",
  "J\\NZP[T[VZWYXWXQWOVNTMPMNN",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RRSQTRUSTRSRU",
  "J\\NZP[T[VZWYXWXQWOVNTMPMNN RRSQTRUSTRSRU",
  "MWSZS[R]Q^ RRNSORPQORNRP",
  23,
  23,
  23,
  23,
  23,
  25,
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  "G[MUWU RK[RFY[ RMEJH",
  26,
  "B[MPTP RW[M[MFWF RHEEH",
  "A]L[LF RLPXP RX[XF RGEDH",
  "GWR[RF RMEJH",
  24,
  "B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH",
  24,
  "@[RQR[ RKFRQYF RFECH",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH",
  "MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  3,
  4,
  "HZM[MFXF",
  "I[K[RFY[K[",
  6,
  "H\\KFYFK[Y[",
  7,
  "F^OPUP RPFTFVGXIYKZNZSYVXXVZT[P[NZLXKVJSJNKKLINGPF",
  8,
  9,
  "I[K[RFY[",
  10,
  "G]L[LFX[XF",
  "H[L[W[ RLFWF RUPNP",
  11,
  "G]L[LFXFX[",
  12,
  24,
  "H[W[L[SPLFWF",
  13,
  15,
  "G]R[RF RPITIWJYLZNZRYTWVTWPWMVKTJRJNKLMJPI",
  14,
  "G]R[RF RHFJGKIKNLQMROSUSWRXQYNYIZG\\F",
  "F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[",
  27,
  "I[RQR[ RKFRQYF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  39,
  40,
  41,
  42,
  "H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  34,
  "H[SOUPVQWSWWVYUZS[P[NZMY RKbLaM_MINGPFSFUGVIVLUNSOQO",
  "JZRYRb RLMMMNNRYWM",
  "H[SMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSMPLNKMINGPFTFVG",
  35,
  "HZMFWFPMNPMSMWNYOZQ[S[U\\V^V_UaSbRb",
  "I\\NMN[ RNOONQMTMVNWPWb",
  "H[LPWP RPFSFUGVHWKWVVYUZS[P[NZMYLVLKMHNGPF",
  36,
  31,
  "JZRMM[ RMFOFPGRMW[",
  "H^MMMb RWXXZZ[ RMXNZP[T[VZWXWM",
  "J[MMR[WPWOVM",
  "HZMFWF RQFOGNINLONQOUO RQOOPNQMSMWNYOZQ[S[U\\V^V_UaSbRb",
  19,
  "F]VMV[ ROMOXNZL[ RZMMMKNJP",
  "H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX",
  "HZVNTMPMNNMOLQLWMYNZP[S[U\\V^V_UaSb",
  "H\\YMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSM",
  "H\\LPMNOMXM RRMRXSZU[",
  "H[MMMXNZP[S[UZVYWWWPVNUM",
  "G]MMLNKPKVLXNZP[T[VZXXYVYPXNVMUMSNRPRb",
  "IZWMLb RLMNNOPT_UaWb",
  "G]RMRb RKMKVLXNZP[T[VZXXYVYM",
  43,
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RRMRXSZU[",
  "H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH",
  29,
  44,
  45,
  "G\\L[LF RXFLR ROOX[Qb",
  "H[SOUPVQWSWWVYUZS[P[NZMXMINGPFSFUGVIVLUNSOQO",
  "H[JPKQLSLVMYNZP[S[UZVYWVWKVHUGSFPFNGMHLJLLMNNOPPWP",
  "I\\KFMFOGQIRKR[ RRKSHTGVFWFYGZI",
  "NiTEQH RXFZF\\G^I_K_[ R_K`HaGcFdFfGgI",
  "I\\KFMFOGQIRKR[ RRKSHTGVFWFYGZI RN?O@NAM@N?NA RV?W@VAU@V?VA",
  38,
  "F^RTRX R[MIM RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM",
  "IZLMNNOPOXNZM[LZLXMVVRWPWNVMUNTPTXUZW[V^U`TaRb",
  "G]R[Rb RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF",
  "H[R[Rb RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[",
  "FZWFQFNGLIKKJOJRKVLXNZQ[R[T\\U^U_TaSbQb",
  "HZVMPMNNMOLQLWMYNZP[R[T\\U^U_TaRbPb",
  "HZTPMP RM[MFWF",
  "MZVPRP RWFUFSGRIR_QaOb",
  "H\\MFOGPILSXNTXUZW[",
  "I[RFMPWPR[",
  "H\\NGNL RXIULTNTW RKIMGPFTFVGXIYKZOZUYYX[",
  "H\\L[UR RR[WV RLMPNSPURWVXZXb",
  "CaRWRR R\\XY]V`SaMa RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF",
  "G]RTRX RXZW\\S`PaOa RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM",
  "G]XFXb RPFNGLIKMKTLXNZP[T[VZXX",
  "I\\WMWb RQMONNOMQMWNYOZQ[T[VZWY",
  "F]KFK[ RKQMOPNTNVOXQYTYWXZW\\U^R`Nb",
  "I[WLWMVPTRRSPSNRMPMONMPLRLTMVPWSWWVYUZS[M[",
  "F]KHLGOFTFWGXHYJYLXOVQJ[N^Q_V_Y^",
  "J[NNPMTMVNWPWRVTTVN[P]R^U^W]",
  "G]I[[[ RIFJFLGXZZ[ R[FZFXGLZJ[",
  "H[KMMNVZX[K[MZVNXM",
  "G\\XEVFOFMGLHKJKWLYMZO[T[VZWYXWXPWNVMTLNLLMKN",
  "H[WEVFTGPGNHMILKLWMYNZP[S[UZVYWWWQVOUNSMOMMNLO",
  "G]RFRb RKQKMYMYQ",
  "I[MMWM RRFRb",
  "IZLMNNOPOXNZM[LZLXMVVRWPWNVMUNTPTXUZW[",
  "H\\WbQbOaN`M^MQNOONQMTMVNWOXQXWWYVZT[Q[OZMX",
  17,
  18,
  32,
  "HZLTST RVZT[P[NZMYLWLQMONNPMTMVN",
  "J\\XTQT RNZP[T[VZWYXWXQWOVNTMPMNN",
  "G\\LFL[ RLKTKVLWMXOXRWTVUTVLV",
  "H[MFMb RMNOMSMUNVOWQWWVYUZS[O[MZ",
  5,
  "F^K[KFRMYFY[",
  "G]LbLMRSXMX[",
  "G\\J`S` RMbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX",
  "I^MYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RROQPRQSPRORQ",
  "I^MYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH RROQPRQSPRORQ",
  "H[MPTP RW[M[MFWF RP>SA",
  "H[MPTP RW[M[MFWF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "JbLFXF RR[RF RRMXM[N]P^S^\\]_[aXbVb",
  "HZM[MFXF RT>QA",
  "F[JPTP RWYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG",
  8,
  27,
  "JZUFUUTXRZO[M[",
  "AbC[D[FZGXILJILGOFRFR[X[[Z]X^V^S]Q[OXNRN",
  "AbF[FF RRFR[X[[Z]X^V^S]Q[OXNFN",
  "JbLFXF RR[RF RRMXM[N]P^S^[",
  "G\\L[LF RX[OO RXFLR RT>QA",
  "G]LFL[XFX[ RP>SA",
  "G[KFRT RYFPXNZL[K[ RN>O@QASAU@V>",
  "G]R[R` RLFL[X[XF",
  3,
  "G\\VFLFL[R[UZWXXVXSWQUORNLN",
  4,
  "HZM[MFXF",
  "F^[`[[I[I` RW[WFRFPGOHNJL[",
  6,
  "BbOOF[ RR[RF RRRFF R^[UO R^FRR",
  "I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ",
  "G]LFL[XFX[",
  "G]LFL[XFX[ RN>O@QASAU@V>",
  9,
  "F\\W[WFTFQGOINLLXKZI[H[",
  10,
  7,
  11,
  "G]L[LFXFX[",
  12,
  5,
  13,
  "G[KFRT RYFPXNZL[K[",
  "G]R[RF RPITIWJYLZNZRYTWVTWPWMVKTJRJNKLMJPI",
  14,
  "G]XFX[ RLFL[Z[Z`",
  "H\\WFW[ RLFLNMPNQPRWR",
  "CaRFR[ RHFH[\\[\\F",
  "CaRFR[ RHFH[\\[\\F R\\[^[^`",
  "F]HFMFM[S[VZXXYVYSXQVOSNMN",
  "Da\\F\\[ RIFI[O[RZTXUVUSTQROONIN",
  "H]MFM[S[VZXXYVYSXQVOSNMN",
  "I^ZQPQ RMHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZMY",
  "CaHFH[ ROPHP RTFXFZG\\I]M]T\\XZZX[T[RZPXOTOMPIRGTF",
  "G\\RQK[ RW[WFOFMGLHKJKMLOMPOQWQ",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR",
  "H[WEVFTGPGNHMILKLWMYNZP[S[UZVYWWWQVOUNSMOMMNLO",
  "I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT",
  "JYO[OMWM",
  "H[WOVNTMPMNNMOLQLWMYNZP[S[UZVYWWWJVHUGSFOFMG",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT",
  "F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU",
  "K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ",
  "H\\MMM[WMW[",
  "H\\MMM[WMW[ RNEOGQHSHUGVE",
  31,
  "I[V[VMSMQNPPOXNZL[",
  "G]L[LMRXXMX[",
  "H[MTVT RMMM[ RVMV[",
  19,
  "H[M[MMVMV[",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ",
  17,
  "KYMMWM RRMR[",
  "JZMMR[ RWMR[P`OaMb",
  38,
  "IZL[WM RLMW[",
  "I\\WMW[ RNMN[Y[Y`",
  "J\\VMV[ RNMNROTQUVU",
  "F^RMR[ RKMK[Y[YM",
  "F^RMR[ RKMK[Y[YM RY[[[[`",
  "HZJMNMN[S[UZVXVUUSSRNR",
  "F^YMY[ RKMK[P[RZSXSURSPRKR",
  "IZNMN[S[UZVXVUUSSRNR",
  "J\\XTQT RNNPMTMVNWOXQXWWYVZT[P[NZ",
  "E_JTPT RJMJ[ RT[RZQYPWPQQORNTMWMYNZO[Q[WZYYZW[T[",
  "I[RUM[ RV[VMPMNNMPMRNTPUVU",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RPESH",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "M^OKXK RRFR[ RRSSRUQWQYRZTZ[Y^WaVb",
  "JYO[OMWM RTEQH",
  "HZLTST RVZT[P[NZMYLWLQMONNPMTMVN",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN",
  "MWR[RM RRFQGRHSGRFRH",
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RR[RM",
  18,
  "E^H[JZKXLPMNOMRMR[W[YZZXZUYSWRRR",
  "D^IMI[ RRMR[W[YZZXZVYTWSIS",
  "M^OKXK RRFR[ RRSSRUQWQYRZTZ[",
  "IZNMN[ RPSV[ RVMNU RTEQH",
  "H\\MMM[WMW[ RPESH",
  "JZMMR[ RWMR[P`OaMb RNEOGQHSHUGVE",
  "H]R[R` RMMM[W[WM",
  "CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF",
  43,
  "F]IIVI RMFM[S[VZXXYVYSXQVOSNMN",
  "HZJMTM RNFN[S[UZVXVUUSSRNR",
  "D`IFI[ RYPIP R\\Y[ZX[V[SZQXPVOROOPKQISGVFXF[G\\H",
  "F^KMK[ RWTKT RZZX[T[RZQYPWPQQORNTMXMZN",
  "F^LSXS RRSR[ RH[RF\\[",
  "I[NUVU RRUR[ RK[RMY[",
  "AbF[FF RFS\\S RVSV[ RL[VF`[",
  "E_J[JM RVUV[ RZUJU RO[VM][",
  "E_R[RPJFZFRP RI[IVJSLQOPUPXQZS[V[[",
  "G]R[RTLMXMRT RK[KXLVMUOTUTWUXVYXY[",
  "AcF[FF RFPSP RV[VPNF^FVP RM[MVNSPQSPYP\\Q^S_V_[",
  "DaI[IM RITST RV[VTPM\\MVT RO[OXPVQUSTYT[U\\V]X][",
  "H\\OPSP RNAQFSBTAUA RLGNFSFUGVHWJWLVNUOSPVQWRXTXWWYVZT[O[M\\L^L_MaObWb",
  "J[RTTT ROHRMTIUHVH RNNPMTMVNWPWQVSTTVUWWWXVZT[Q[O\\N^N_OaQbVb",
  "G]R[RF RHFJGKIKNLQMROSUSWRXQYNYIZG\\F",
  "G]RMRb RKMKVLXNZP[T[VZXXYVYM",
  32,
  37,
  "I[KFR[YF",
  20,
  "I[KFR[YF ROAL> RVAS>",
  "JZMMR[WM ROHLE RVHSE",
  "GmPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF R`Me[ RjMe[c`ba`b",
  "HkP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ R^Mc[ RhMc[a``a^b",
  "CaRXR^ RRCRI RMFJGHIGLGUHXJZM[W[ZZ\\X]U]L\\IZGWFMF",
  "G]RYR] RRKRO ROMMNLOKQKWLYMZO[U[WZXYYWYQXOWNUMOM",
  "CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF RLBM@O?R?U@X@",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RLIMGOFRFUGXG",
  "CaRWRR RLFJGHIGLGUHXJZL[N[PZQYRWSYTZV[X[ZZ\\X]U]L\\IZGXF RM<W< RR<R?",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMEWE RRERH",
  "FZWGTFPFMGKIJKJNKPMRPSTST[",
  "FZVNTMPMNNMOLQLSMUNVPWTWT[",
  "H[N]UO ROQWU RT[LW",
  "JZMHMFWGWE",
  "JZMHUEVH",
  16,
  25,
  "KZLIMGOFRFUGXG",
  ":j>R?PAOCPDR RC^D\\F[H\\I^ RCFDDFCHDIF ROcPaR`TaUc ROAP?R>T?UA R[^\\\\^[`\\a^ R[F\\D^C`DaF R`RaPcOePfR",
  ":jDQ>Q RH[D_ RHGDC RR_Re RRCR= R\\[`_ R\\G`C R`QfQ",
  "G]LFL[XFX[ RX[[[Ub RN>O@QASAU@V>",
  "H\\MMM[WMW[ RW[Z[Tb RNEOGQHSHUGVE",
  "H]MFM[S[VZXXYVYSXQVOSNMN RJIPI",
  "IZKMQM RNFN[S[UZVXVUUSSRNR",
  "G\\L[LFTFVGWHXJXMWOVPTQLQ RTMXS",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RSWW]",
  "HZM[MFXFXA",
  "JYO[OMWMWH",
  "HZM[MFXF RJQRQ",
  "JYO[OMWM RLTTT",
  "H]M[MFXF RMMSMVNXPYSY\\X_VaSbQb",
  "J\\O[OMWM ROTTTVUWVXXX[W^UaTb",
  "BbOOF[ RR[RF RRRFF R^[UO R^FRR R^[`[``",
  "F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RZ[\\[\\`",
  "I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ RR\\T]U_TaRbOb",
  "K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ RR\\T]U_TaRbOb",
  "G\\L[LF RX[OO RXFLR RX[Z[Z`",
  "IZNMN[ RPSV[ RVMNU RV[X[X`",
  "G\\L[LF RX[OO RXFLR RPKPS",
  "IZNMN[ RPSV[ RVMNU RRORW",
  "G\\L[LF RX[OO RXFLR RIJOJ",
  "IZN[NF RPSV[ RVMNU RKJQJ",
  "E\\X[OO RXFLR RGFLFL[",
  "HZPSV[ RVMNU RJMNMN[",
  "G]L[LF RLPXP RX[XF RX[Z[Z`",
  "H[MTVT RMMM[ RVMV[ RV[X[X`",
  "GeL[LF RLPXP RX[XFcF",
  "H`MTVT RMMM[ RV[VM^M",
  "GhL[LFXFX[ RXM^MaNcPdSd\\c_aa^b\\b",
  "HcM[MMVMV[ RVT[T]U^V_X_[^^\\a[b",
  "F^QFNGLIKKJOJRKVLXNZQ[S[VZXXYVZRZMYJWIVITJSMSRTVUXWZY[[[",
  "H\\QMPMNNMOLQLWMYNZP[T[VZWYXWXRWPUOSPRRRWSYTZV[Y[",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb",
  "JZLFXF RR[RF RR[T[T`",
  "KYMMWM RRMR[ RR[T[T`",
  15,
  "JZR[Rb RMMR[WM",
  "I[RQR[ RKFRQYF RNUVU",
  "JZR[Rb RMMR[WM RN]V]",
  "H\\KFY[ RYFK[ RX[Z[Z`",
  "IZL[WM RLMW[ RV[X[X`",
  "D]FFRF RXFX[ RLFL[Z[Z`",
  "G\\RMIM RWMW[ RNMN[Y[Y`",
  "H\\WFW[ RLFLNMPNQPRWR RW[Y[Y`",
  "J\\VMV[ RNMNROTQUVU RV[X[X`",
  "H\\WFW[ RLFLNMPNQPRWR RRNRV",
  "J\\VMV[ RNMNROTQUVU RRQRY",
  "G]L[LF RL[ RLPRPUQWSXVX[",
  "H[M[MF RV[VPUNSMPMNNMO",
  "@^WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGXIYKZOJQGQEPDOCMCK",
  "E[VZT[P[NZMXMPNNPMTMVNWPWRMTKTISHQHO",
  "@^WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGXIYKZOJQGQEPDOCMCK RR[P]O_PaRbTb",
  "E[VZT[P[NZMXMPNNPMTMVNWPWRMTKTISHQHO RR[P]O_PaRbTb",
  8,
  "BbOOF[ RR[RF RRRFF R^[UO R^FRR RN>O@QASAU@V>",
  "F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RNEOGQHSHUGVE",
  "G\\L[LF RX[OO RXFLR RX[X_WaUbSb",
  "IZNMN[ RPSV[ RVMNU RV[V_UaSbQb",
  "F\\W[WFTFQGOINLLXKZI[H[ RW[Z[Tb",
  "I[V[VMSMQNPPOXNZL[ RV[Y[Sb",
  "G]L[LF RLPXP RX[XF RX[X_WaUbSb",
  "H[MTVT RMMM[ RVMV[ RV[V_UaSbQb",
  "G]L[LF RLPXP RX[XF RX[[[Ub",
  "H[MTVT RMMM[ RVMV[ RV[Y[Sb",
  "H\\WFW[ RLFLNMPNQPRWR RW[U[U`",
  "J\\VMV[ RNMNROTQUVU RV[T[T`",
  "F^K[KFRUYFY[ RY[\\[Vb",
  "G]L[LMRXXMX[ RX[[[Ub",
  8,
  30,
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE",
  "I[MUWU RK[RFY[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "F`JURU RRPYP RH[OF\\F RRFR[\\[",
  "D`INKMOMQNRP R[ZY[U[SZRXRPSNUMYM[N\\P\\RRSKSITHVHXIZK[O[QZRX",
  "H[MPTP RW[M[MFWF RN>O@QASAU@V>",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNEOGQHSHUGVE",
  "F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP",
  33,
  "F^MHNGQFSFVGXIYKZOZRYVXXVZS[Q[NZLXKVJRZP RNBOCNDMCNBND RVBWCVDUCVBVD",
  "I[NNPMTMVNWPWXVZT[P[NZMXMVWT RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "BbOOF[ RR[RF RRRFF R^[UO R^FRR RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "F^QTJ[ RRUJM RRMR[ RZ[ST RZMRU RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I]PPTP RMGOFTFVGWHXJXLWNVOTPWQXRYTYWXYWZU[O[MZ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "K[RTTT RNNPMTMVNWPWQVSTTVUWWWXVZT[P[NZ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  2,
  "JZMMVMOVRVTWUXVZV^U`TaRbObMa",
  "G]LFL[XFX[ RM@W@",
  "H\\MMM[WMW[ RMGWG",
  "G]LFL[XFX[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "H\\MMM[WMW[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  32,
  37,
  "G]KPYP RPFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "H[LTWT RP[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I^ZPPP RMYNZQ[S[VZXXYVZRZOYKXIVGSFQFNGMH RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "J\\XTQT RNZP[T[VZWYXWXQWOVNTMPMNN RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "G[KFRT RYFPXNZL[K[ RM@W@",
  "JZMMR[ RWMR[P`OaMb RMGWG",
  "G[KFRT RYFPXNZL[K[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "JZMMR[ RWMR[P`OaMb RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "G[KFRT RYFPXNZL[K[ RQ>NA RX>UA",
  "JZMMR[ RWMR[P`OaMb RQENH RXEUH",
  "H\\WFW[ RLFLNMPNQPRWR RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "J\\VMV[ RNMNROTQUVU RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "HZM[MFXF RM[O[O`",
  "JYO[OMWM RO[Q[Q`",
  "Da\\F\\[ RIFI[O[RZTXUVUSTQROONIN RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "F^YMY[ RKMK[P[RZSXSURSPRKR RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "HZWFMFM[Q[Q_PaNbLb RJQRQ",
  "JYWMOMO[S[S_RaPbNb RLTTT",
  "H\\KFY[ RYFK[ RX[X_WaUbSb",
  "IZL[WM RLMW[ RV[V_UaSbQb",
  "H\\KFY[ RYFK[ RNPVP",
  "IZL[WM RLMW[ RNTVT",
  "G\\WFW[Q[NZLXKVKSLQNOQNWN",
  "J[VMV[Q[OZNXNUOSQRVR",
  "B_RXSZU[X[ZZ[X[M RRFRXQZO[L[IZGXFVFSGQIOLNRN",
  "E]RXSZU[V[XZYXYQ RRMRXQZO[M[KZJXJUKSMRRR",
  "IePPTP RMGOFTFVGWHXJXLWNVOTPVQWRXTXXYZ[[^[`ZaXaM",
  "KbRTTT RNNPMTMVNWPWQVSTTVUWWWXXZZ[[[]Z^X^Q",
  "I\\PPTP RMGOFTFVGWHXJXLWNVOTPVQWRXTX[Z[Z`",
  "K[RTTT RNNPMTMVNWPWQVSTTVUWWW[Y[Y`",
  "FdH[I[KZLXNLOIQGTFWFWXXZZ[][_Z`X`M",
  "IaL[NZOXPPQNSMVMVXWZY[Z[\\Z]X]Q",
  "CaH[HF RHPTP RTFTXUZW[Z[\\Z]X]M",
  "F^KTTT RKMK[ RTMTXUZW[X[ZZ[X[R",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR",
  "HZUNSMPMNNMOLQLWMYNZP[T[VZVUSU",
  "J_LFXF RRFRXSZU[X[ZZ[X[M",
  "K]MMWM RRMRXSZU[V[XZYXYS",
  "G[PPTP RWGUFPFNGMHLJLLMNNOPPMQLRKTKWLYMZO[U[WZ",
  35,
  "F\\W[WFTFQGOINLLXKZI[H[ RW[W_VaTbRb",
  "I[V[VMSMQNPPOXNZL[ RV[V_UaSbQb",
  "BaP[^F RD[E[GZHXJLKIMGPF^[",
  "E^[MO[ RH[JZKXLPMNOM[[",
  "E_\\FUO\\[ RJ[JFRFTGUHVJVMUOTPRQJQ",
  "F^KMKb R[MUT[[ RKNMMQMSNTOUQUWTYSZQ[M[KZ",
  "DaOQH[ RTFT[^[ R[QLQJPIOHMHJIHJGLF^F",
  "D`H[MU RRPRMKMINHPHRITKURU R[ZY[U[SZRXRPSNUMYM[N\\P\\RRT",
  "G]Z]X\\VZSWQVOV RP[NZLXKTKMLINGPFTFVGXIYMYTXXVZT[P[",
  "I\\WMWb RWZU[Q[OZNYMWMQNOONQMUMWN",
  "F^IFN[RLV[[F",
  21,
  "G\\L[LF RX[OO RXFLR RXKRG",
  "IZNMN[ RPSV[ RVMNU RWQQM",
  "FgW[WFTFQGOINLLXKZI[H[ RWM]M`NbPcSc\\b_`a]b[b",
  "IcV[VMSMQNPPOXNZL[ RVT[T]U^V_X_[^^\\a[b",
  "GhL[LF RLPXP RX[XF RXM^MaNcPdSd\\c_aa^b\\b",
  "HcMTVT RMMM[ RVMV[ RVT[T]U^V_X_[^^\\a[b",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "JZNXVX RM[RMW[",
  "H\\LXRX RRTWT RRMR[Y[ RYMPMK[",
  "D`[ZY[U[SZRX RINKMOMQNRPRXQZO[K[IZHXHVRUYU[T\\R\\P[NYMUMSNRP",
  "I[STVUWWWXVZT[N[NMSMUNVPVQUSSTNT RKWQW",
  17,
  "J[SMOMO[S[UZVYWVWRVOUNSM",
  "J[SMOMO[S[UZVYWVWRVOUNSM RLTRT",
  "JYOTTT RVMOMO[V[",
  "J[TTVSWQWPVNTMPMNN RRTTTVUWWWXVZT[P[NZ",
  "MWRMR[ RRbSaR`QaRbR`",
  "LYTMTWSYRZP[O[",
  31,
  "JYOMO[V[ RLVRR",
  "G]L[LMRXXMX[",
  "I\\W[WMN[NM",
  19,
  "J\\NNPMTMVNWOXQXWWYVZT[P[NZ",
  "G]YSYVXXWYUZOZMYLXKVKSLQMPOOUOWPXQYS",
  "G]XYYWYSXQWPUOOOMPLQKSKWLY",
  "G]YNK[ RYSYVXXWYUZOZMYLXKVKSLQMPOOUOWPXQYS",
  "DaINKMOMQNRPRXQZO[K[IZHXHVRT RRWSYTZV[Y[[Z\\Y]W]Q\\O[NYMVMTNSORQ",
  "G]OMNNMPNRPS RTSVRWPVNUM RPSTSVTWVWXVZT[P[NZMXMVNTPS",
  "I\\XTXQWOVNTMQMONNOMQMT",
  "H[LTLWMYNZP[S[UZVYWWWT",
  "I[N[NMTMVNWPWRVTTUNU",
  "I[RUM[ RV[VMPMNNMPMRNTPUVU",
  "I[RSMM RVMV[P[NZMXMVNTPSVS",
  "KYMMWM RRMR[",
  "H[MMMXNZP[S[UZVXVM",
  "G]KPYP RKYVYXXYVYSXQWP",
  "@]KPYP RKYVYXXYVYSXQWP REWFXEYDXEWEY REOFPEQDPEOEQ",
  "G]KKYK RWKXLYNYQXSVTKT RVTXUYWYZX\\V]K]",
  20,
  21,
  "IZLMWML[W[",
  "JZNMVMRRSRUSVUVXUZS[P[NZ",
  "H\\XNUMPMNNMOLQLSMUNVPWTXVYWZX\\X^W`VaTbObLa RRTR\\",
  "JZW[PROPPNRMTNUPTRM[",
  "JYO[OMWM",
  "JZM[RMW[",
  "H[M[MMVMV[",
  "I[N[NMTMVNWPWRVTTUNU",
  "I[RMR[ RLMMNMRNTPUTUVTWRWNXM",
  "I[V[VMSMQNPPOXNZL[",
  "JZNKVK RMNR@WN",
  "H\\LKRK RRGWG RR@RNYN RY@P@KN",
  "I[SGVHWJWKVMTNNNN@S@UAVCVDUFSGNG",
  "I[SGVHWJWKVMTNNNN@S@UAVCVDUFSGNG RKGQG",
  "J[S@O@ONSNUMVLWIWEVBUAS@",
  "JYOGTG RV@O@ONVN",
  "KZUGPG RN@U@UNNN",
  "HZUAS@P@NAMBLDLJMLNMPNTNVMVHSH",
  "H[MGVG RM@MN RV@VN",
  "MWRNR@ RUNON RU@O@",
  "LYT@TJSLRMPNON",
  "IZN@NN RPFVN RV@NH",
  "JYO@ONVN",
  "G]LNL@RKX@XN",
  "H[MNM@VNV@",
  "I\\WNW@NNN@",
  "H[PNNMMLLJLDMBNAP@S@UAVBWDWJVLUMSNPN",
  "G]O@NAMCNEPF RTFVEWCVAU@ RPFTFVGWIWKVMTNPNNMMKMINGPF",
  "I[NNN@T@VAWCWEVGTHNH",
  "I[RHWN RNNN@T@VAWCWEVGTHNH",
  "KYM@W@ RR@RN",
  "H[M@MKNMPNSNUMVKV@",
  "G]J@NNRDVNZ@",
  "KZOEQDSDUEVGVN RVMTNQNOMNKOIQHVH",
  "JYNDNKOMQNSNUM RNEPDSDUEVGUISJNJ",
  "H]WDUKTMRNPNNMMKMGNEPDRDTEVMWN",
  "H\\XMVNUNSMRK RLDODQERHRKQMONNNLMKKKJVJXIYGXEVDUDSERH",
  "KYO@ON ROMQNSNUMVKVGUESDQDOE",
  "KYU@UN RUESDQDOENGNKOMQNSNUM",
  "LYVMTNRNPMOKOGPERDSDUEVGVHOI",
  "LYOEQDSDUEVGVKUMSNRNPMOKOJVI",
  "LXPIRI RUETDPDOEOHPIOJOMPNTNUM",
  "LXRITI ROEPDTDUEUHTIUJUMTNPNOM",
  "KYUDUPTRRSOS RUESDQDOENGNKOMQNSNUM",
  "NVRDRN RRUSTRSQTRURS",
  "IZO@ON RUNQH RUDOJ",
  "G]KNKD RKEMDODQERGRN RRGSEUDVDXEYGYN",
  "KZODON ROEQDSDUEVGVPURSSRS",
  "KYQNOMNKNGOEQDSDUEVGVKUMSNQN",
  "LYOEQDSDUEVGVKUMSNQNOM",
  "KYNINGOEQDSDUEVGVI",
  "KYNINKOMQNSNUMVKVI",
  "KYOSOD ROEQDSDUEVGVKUMSNQNOM",
  "NXPDVD RR@RKSMUNVN",
  "KYUDUN RNDNKOMQNSNUM",
  "I[MFWF RMMTMVLWJWHVF",
  "G]YDYN RYMWNUNSMRKRD RRKQMONNNLMKKKD",
  "LXNDRNVD",
  "LXVNPGPEQDSDTETGNN",
  "KYSFRF RNSOQOCPAR@S@UAVCUESFUGVIVKUMSNQNOM",
  "KXRMRS RMDOERMVD",
  "KYSDQDOENGNKOMQNSNUMVKVGUESDPCOBOAP@U@",
  "I[MDLFLJMLNMPNTNVMWLXJXGWEUDSERGRS",
  "LXVDNS RNDPETRVS",
  "NVRWRa RRPQQRRSQRPRR",
  "LWPWPa RPZQXSWUW",
  "KYUWUa RNWN^O`QaSaU`",
  "LXNWRaVW",
  "KYSYRY RNfOdOVPTRSSSUTVVUXSYUZV\\V^U`SaQaO`",
  "KXR`Rf RMWOXR`VW",
  "KYOfOZPXRWSWUXVZV^U`SaQaO`",
  "I[MWLYL]M_N`PaTaV`W_X]XZWXUWSXRZRf",
  "LXVWNf RNWPXTeVf",
  "D`IMIXJZL[O[QZRX R[ZY[U[SZRXRPSNUMYM[N\\P\\RRT",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RIHJGLFPHRGSF",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RQHRGTFXHZG[F",
  "MYOMWM RR[RISGUFWF RMTNSPRTTVSWR",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RMTNSPRTTVSWR",
  "I\\NMN[ RNOONQMTMVNWPW[ RMTNSPRTTVSWR",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RI`J_L^P`R_S^",
  "KXP[PM RPQQORNTMVM RLTMSORSTUSVR",
  "KXM[S[ RVMTMRNQOPRP[ RLTMSORSTUSVR",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNTOSQRUTWSXR",
  "MYOMWM RRFRXSZU[W[ RMSNRPQTSVRWQ",
  "IZLMWML[W[ RMTNSPRTTVSWR",
  "H[M[MJNHOGQFTFVG RMNOMSMUNVOWQWWVYUZS[O[MZ",
  "H[MGVG RM@MN RV@VN",
  "JZMMVMOURUTVUWVYV^U`TaRbPbNaM_M^N\\P[V[",
  "MlOMWM RRFRXSZU[W[ R^[^F Rg[gPfNdMaM_N^O RiC]`",
  "MWR[RM RU[O[ RUMOM ROTUT",
  "MXRMRXSZU[ ROTUT",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RHT\\T",
  "H[MMMXNZP[S[UZVXVM RHT\\T",
  "I\\XMUMUPWRXTXWWYVZT[Q[OZNYMWMTNRPPPMMM RHU\\U",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "I[MUWU RK[RFY[ RR`TaUcTeRfPeOcPaR`",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RR`TaUcTeRfPeOcPaR`",
  "G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RR?Q@RAS@R?RA",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RN?M@NAO@N?NA",
  "G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RRbSaR`QaRbR`",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RRbSaR`QaRbR`",
  "G\\SPVQWRXTXWWYVZT[L[LFSFUGVHWJWLVNUOSPLP RWaMa",
  "H[M[MF RMNOMSMUNVOWQWWVYUZS[O[MZ RWaMa",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR\\T]U_TaRbOb RT>QA",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RR\\T]U_TaRbOb RTEQH",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RR?Q@RAS@R?RA",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RV?U@VAW@V?VA",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RRbSaR`QaRbR`",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RSbTaS`RaSbS`",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RWaMa",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RXaNa",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RQ\\S]T_SaQbNb",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RS\\U]V_UaSbPb",
  "G\\L[LFQFTGVIWKXOXRWVVXTZQ[L[ RVcR`Nc",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RWcS`Oc",
  "H[MPTP RW[M[MFWF RM@W@ RP9S<",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG RP>SA",
  "H[MPTP RW[M[MFWF RM@W@ RT9Q<",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMGWG RT>QA",
  "H[MPTP RW[M[MFWF RVcR`Nc",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RVcR`Nc",
  "H[MPTP RW[M[MFWF RW`VaTbP`NaMb",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RW`VaTbP`NaMb",
  "H[MPTP RW[M[MFWF RR\\T]U_TaRbOb RN>O@QASAU@V>",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RR\\T]U_TaRbOb RNEOGQHSHUGVE",
  "HZTPMP RM[MFWF RR?Q@RAS@R?RA",
  "MYOMWM RR[RISGUFWF RT?S@TAU@T?TA",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RM@W@",
  "I\\WMW^V`UaSbPbNa RWZU[Q[OZNYMWMQNOONQMUMWN RMGWG",
  "G]L[LF RLPXP RX[XF RR?Q@RAS@R?RA",
  "H[M[MF RV[VPUNSMPMNNMO RM?L@MAN@M?MA",
  "G]L[LF RLPXP RX[XF RRbSaR`QaRbR`",
  "H[M[MF RV[VPUNSMPMNNMO RRbSaR`QaRbR`",
  "G]L[LF RLPXP RX[XF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "H[M[MF RV[VPUNSMPMNNMO RI?J@IAH@I?IA RQ?R@QAP@Q?QA",
  "G]L[LF RLPXP RX[XF RL\\N]O_NaLbIb",
  "H[M[MF RV[VPUNSMPMNNMO RM\\O]P_OaMbJb",
  "G]L[LF RLPXP RX[XF RV`UbScQcObN`",
  "H[M[MF RV[VPUNSMPMNNMO RV`UbScQcObN`",
  "MWR[RF RW`VaTbP`NaMb",
  "MWR[RM RRFQGRHSGRFRH RW`VaTbP`NaMb",
  "MWR[RF RN?O@NAM@N?NA RV?W@VAU@V?VA RT9Q<",
  "MWR[RM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  "G\\L[LF RX[OO RXFLR RT>QA",
  "IZN[NF RPSV[ RVMNU RPAMD",
  "G\\L[LF RX[OO RXFLR RRbSaR`QaRbR`",
  "IZN[NF RPSV[ RVMNU RRbSaR`QaRbR`",
  "G\\L[LF RX[OO RXFLR RWaMa",
  "IZN[NF RPSV[ RVMNU RWaMa",
  "HYW[M[MF RRbSaR`QaRbR`",
  "MXU[SZRXRF RSbTaS`RaSbS`",
  "HYW[M[MF RH@R@ RRbSaR`QaRbR`",
  "MXU[SZRXRF RM@W@ RSbTaS`RaSbS`",
  "HYW[M[MF RWaMa",
  "MXU[SZRXRF RXaNa",
  "HYW[M[MF RVcR`Nc",
  "MXU[SZRXRF RWcS`Oc",
  "F^K[KFRUYFY[ RT>QA",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RTEQH",
  "F^K[KFRUYFY[ RR?Q@RAS@R?RA",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RRFQGRHSGRFRH",
  "F^K[KFRUYFY[ RRbSaR`QaRbR`",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RRbSaR`QaRbR`",
  "G]L[LFX[XF RR?Q@RAS@R?RA",
  "I\\NMN[ RNOONQMTMVNWPW[ RRFQGRHSGRFRH",
  "G]L[LFX[XF RRbSaR`QaRbR`",
  "I\\NMN[ RNOONQMTMVNWPW[ RRbSaR`QaRbR`",
  "G]L[LFX[XF RWaMa",
  "I\\NMN[ RNOONQMTMVNWPW[ RWaMa",
  "G]L[LFX[XF RVcR`Nc",
  "I\\NMN[ RNOONQMTMVNWPW[ RVcR`Nc",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RT9Q<",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RT>QA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RMAN@P?TAV@W? RN:O;N<M;N:N< RV:W;V<U;V:V<",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMHNGPFTHVGWF RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@ RP9S<",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG RP>SA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RM@W@ RT9Q<",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RMGWG RT>QA",
  "G\\L[LFTFVGWHXJXMWOVPTQLQ RT>QA",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RTEQH",
  "G\\L[LFTFVGWHXJXMWOVPTQLQ RR?Q@RAS@R?RA",
  "H[MMMb RMNOMSMUNVOWQWWVYUZS[O[MZ RRFQGRHSGRFRH",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RR?Q@RAS@R?RA",
  "KXP[PM RPQQORNTMVM RSFRGSHTGSFSH",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RRbSaR`QaRbR`",
  "KXP[PM RPQQORNTMVM RPbQaP`OaPbP`",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RM@W@ RRbSaR`QaRbR`",
  "KXP[PM RPQQORNTMVM RNGXG RPbQaP`OaPbP`",
  "G\\X[QQ RL[LFTFVGWHXJXMWOVPTQLQ RWaMa",
  "KXP[PM RPQQORNTMVM RUaKa",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR?Q@RAS@R?RA",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRFQGRHSGRFRH",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RRbSaR`QaRbR`",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRbSaR`QaRbR`",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RU>RA RM>N?M@L?M>M@",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RUERH RMENFMGLFMEMG",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RN>RAV> RR:Q;R<S;R:R<",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RNERHVE RR?Q@RAS@R?RA",
  "H\\LZO[T[VZWYXWXUWSVRTQPPNOMNLLLJMHNGPFUFXG RR?Q@RAS@R?RA RRbSaR`QaRbR`",
  "J[NZP[T[VZWXWWVUTTQTOSNQNPONQMTMVN RRFQGRHSGRFRH RRbSaR`QaRbR`",
  "JZLFXF RR[RF RR?Q@RAS@R?RA",
  "MYOMWM RRFRXSZU[W[ RR?Q@RAS@R?RA",
  "JZLFXF RR[RF RRbSaR`QaRbR`",
  "MYOMWM RRFRXSZU[W[ RTbUaT`SaTbT`",
  "JZLFXF RR[RF RWaMa",
  "MYOMWM RRFRXSZU[W[ RYaOa",
  "JZLFXF RR[RF RVcR`Nc",
  "MYOMWM RRFRXSZU[W[ RXcT`Pc",
  "G]LFLWMYNZP[T[VZWYXWXF RVbUaV`WaVbV` RNbMaN`OaNbN`",
  "H[VMV[ RMMMXNZP[S[UZVY RVbUaV`WaVbV` RNbMaN`OaNbN`",
  "G]LFLWMYNZP[T[VZWYXWXF RW`VaTbP`NaMb",
  "H[VMV[ RMMMXNZP[S[UZVY RW`VaTbP`NaMb",
  "G]LFLWMYNZP[T[VZWYXWXF RVcR`Nc",
  "H[VMV[ RMMMXNZP[S[UZVY RVcR`Nc",
  "G]LFLWMYNZP[T[VZWYXWXF RMAN@P?TAV@W? RT9Q<",
  "H[VMV[ RMMMXNZP[S[UZVY RMHNGPFTHVGWF RT>QA",
  "G]LFLWMYNZP[T[VZWYXWXF RM@W@ RN:O;N<M;N:N< RV:W;V<U;V:V<",
  "H[VMV[ RMMMXNZP[S[UZVY RMGWG RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "I[KFR[YF RMAN@P?TAV@W?",
  "JZMMR[WM RMHNGPFTHVGWF",
  "I[KFR[YF RRbSaR`QaRbR`",
  "JZMMR[WM RRbSaR`QaRbR`",
  "F^IFN[RLV[[F RP>SA",
  "G]JMN[RQV[ZM RPESH",
  "F^IFN[RLV[[F RT>QA",
  "G]JMN[RQV[ZM RTEQH",
  "F^IFN[RLV[[F RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "G]JMN[RQV[ZM RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "F^IFN[RLV[[F RR?Q@RAS@R?RA",
  "G]JMN[RQV[ZM RRFQGRHSGRFRH",
  "F^IFN[RLV[[F RRbSaR`QaRbR`",
  "G]JMN[RQV[ZM RRbSaR`QaRbR`",
  "H\\KFY[ RYFK[ RR?Q@RAS@R?RA",
  "IZL[WM RLMW[ RRFQGRHSGRFRH",
  "H\\KFY[ RYFK[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "IZL[WM RLMW[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I[RQR[ RKFRQYF RR?Q@RAS@R?RA",
  "JZMMR[ RWMR[P`OaMb RRFQGRHSGRFRH",
  "H\\KFYFK[Y[ RNAR>VA",
  "IZLMWML[W[ RNHREVH",
  "H\\KFYFK[Y[ RRbSaR`QaRbR`",
  "IZLMWML[W[ RRbSaR`QaRbR`",
  "H\\KFYFK[Y[ RWaMa",
  "IZLMWML[W[ RWaMa",
  "H[M[MF RV[VPUNSMPMNNMO RWaMa",
  "MYOMWM RRFRXSZU[W[ RN?O@NAM@N?NA RV?W@VAU@V?VA",
  "G]JMN[RQV[ZM RRHPGOEPCRBTCUETGRH",
  "JZMMR[ RWMR[P`OaMb RRHPGOEPCRBTCUETGRH",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RWJYIZGYEWD",
  "MYR[RISGUFWF RT?S@TAU@T?TA",
  "MYR[RISGUFWF ROSUO",
  "MYR[RISGUFWF ROLUL",
  "E^J[JLKIMGPFZFSNVNXOYPZRZWYYXZV[R[PZOY",
  "H[SMPMNNMOLQLWMYNZP[S[UZVYWWWQVOUNSMPLNKMINGPFTFVG",
  "I[MUWU RK[RFY[ RRbSaR`QaRbR`",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRbSaR`QaRbR`",
  "I[MUWU RK[RFY[ RRAT?U=T;R:P:",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RRHTFUDTBRAPA",
  "I[MUWU RK[RFY[ RU>X; RNAR>VA",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RUEXB RNHREVH",
  "I[MUWU RK[RFY[ RO>L; RNAR>VA",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR ROELB RNHREVH",
  "I[MUWU RK[RFY[ RNAR>VA RXAZ?[=Z;X:V:",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RXHZF[DZBXAVA",
  "I[MUWU RK[RFY[ RNAR>VA RM<N;P:T<V;W:",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RMAN@P?TAV@W?",
  "I[MUWU RK[RFY[ RNAR>VA RRbSaR`QaRbR`",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNHREVH RRbSaR`QaRbR`",
  "I[MUWU RK[RFY[ RN>O@QASAU@V> RT9Q<",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RT>QA",
  "I[MUWU RK[RFY[ RN>O@QASAU@V> RP9S<",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RP>SA",
  "I[MUWU RK[RFY[ RN>O@QASAU@V> RP>R<S:R8P7N7",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RPERCSAR?P>N>",
  "I[MUWU RK[RFY[ RN>O@QASAU@V> RM<N;P:T<V;W:",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RMAN@P?TAV@W?",
  "I[MUWU RK[RFY[ RN>O@QASAU@V> RRbSaR`QaRbR`",
  "I\\W[WPVNTMPMNN RWZU[P[NZMXMVNTPSUSWR RNEOGQHSHUGVE RRbSaR`QaRbR`",
  "H[MPTP RW[M[MFWF RRbSaR`QaRbR`",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRbSaR`QaRbR`",
  "H[MPTP RW[M[MFWF RRAT?U=T;R:P:",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RRHTFUDTBRAPA",
  "H[MPTP RW[M[MFWF RMAN@P?TAV@W?",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RMHNGPFTHVGWF",
  "H[MPTP RW[M[MFWF RU>X; RNAR>VA",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RUEXB RNHREVH",
  "H[MPTP RW[M[MFWF RO>L; RNAR>VA",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT ROELB RNHREVH",
  "H[MPTP RW[M[MFWF RNAR>VA RXAZ?[=Z;X:V:",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RXHZF[DZBXAVA",
  "H[MPTP RW[M[MFWF RNAR>VA RM<N;P:T<V;W:",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RMAN@P?TAV@W?",
  "H[MPTP RW[M[MFWF RNAR>VA RRbSaR`QaRbR`",
  "I[VZT[P[NZMXMPNNPMTMVNWPWRMT RNHREVH RRbSaR`QaRbR`",
  "MWR[RF RRAT?U=T;R:P:",
  "MWR[RM RRHTFUDTBRAPA",
  "MWR[RF RRbSaR`QaRbR`",
  "MWR[RM RRFQGRHSGRFRH RRbSaR`QaRbR`",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RRbSaR`QaRbR`",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRbSaR`QaRbR`",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RRAT?U=T;R:P:",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RRHTFUDTBRAPA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RU>X; RNAR>VA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUEXB RNHREVH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RO>L; RNAR>VA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ ROELB RNHREVH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RXAZ?[=Z;X:V:",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RXHZF[DZBXAVA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RM<N;P:T<V;W:",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RMAN@P?TAV@W?",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RNAR>VA RRbSaR`QaRbR`",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RNHREVH RRbSaR`QaRbR`",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RT>QA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RTEQH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RP>SA",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RPESH",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RRAT?U=T;R:P:",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RRHTFUDTBRAPA",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RWAVBTCPANBMC",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RWHVITJPHNIMJ",
  "G]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RVGXFYDXBWA RRbSaR`QaRbR`",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RUNWMXKWIVH RRbSaR`QaRbR`",
  "G]LFLWMYNZP[T[VZWYXWXF RRbSaR`QaRbR`",
  "H[VMV[ RMMMXNZP[S[UZVY RRbSaR`QaRbR`",
  "G]LFLWMYNZP[T[VZWYXWXF RRAT?U=T;R:P:",
  "H[VMV[ RMMMXNZP[S[UZVY RRHTFUDTBRAPA",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RT>QA",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RTEQH",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RP>SA",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RPESH",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RRAT?U=T;R:P:",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RRHTFUDTBRAPA",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RWAVBTCPANBMC",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RWHVITJPHNIMJ",
  "G]LFLWMYNZP[T[VZWYXWXF RXFZE[CZAY@ RRbSaR`QaRbR`",
  "H[VMV[ RMMMXNZP[S[UZVY RVMXLYJXHWG RRbSaR`QaRbR`",
  "I[RQR[ RKFRQYF RP>SA",
  "JZMMR[ RWMR[P`OaMb RPESH",
  "I[RQR[ RKFRQYF RRbSaR`QaRbR`",
  "JZMMR[ RWMR[P`OaMb RVbWaV`UaVbV`",
  "I[RQR[ RKFRQYF RRAT?U=T;R:P:",
  "JZMMR[ RWMR[P`OaMb RRHTFUDTBRAPA",
  "I[RQR[ RKFRQYF RMAN@P?TAV@W?",
  "JZMMR[ RWMR[P`OaMb RMHNGPFTHVGWF",
  "E\\PFP[ RJFJ[Z[",
  "J[MMWM ROFOXPZR[ RX[VZUXUF",
  "G]QFOGMJLMLWMYNZP[T[VZXXYVYTXPVMUL",
  "H[QMONNOMQMWNYOZQ[S[UZVYWWWUVSURSQ",
  "G[KFRT RYFRTPXOZM[KZJXKVMUOVPX",
  "JZMMR[ RWMR[Q_PaNbLaK_L]N\\P]Q_",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMHNHOGOE",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMEMGNHOH",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMHNHOGOE",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMEMGNHOH",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RMAN@P?TAV@W?",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RMAN@P?TAV@W?",
  "G[MUWU RK[RFY[ RJHKHLGLE",
  "G[MUWU RK[RFY[ RJEJGKHLH",
  "?[MUWU RK[RFY[ RIELH RBHCHDGDE",
  "?[MUWU RK[RFY[ RIELH RBEBGCHDH",
  "?[MUWU RK[RFY[ RMEJH RBHCHDGDE",
  "?[MUWU RK[RFY[ RMEJH RBEBGCHDH",
  "D[MUWU RK[RFY[ RFAG@I?MAO@P? RJHKHLGLE",
  "D[MUWU RK[RFY[ RFAG@I?MAO@P? RJEJGKHLH",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RQHRHSGSE",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RQEQGRHSH",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEWH RMHNHOGOE",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RTEWH RMEMGNHOH",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RXEUH RMHNHOGOE",
  "IZPTNUMWMXNZP[T[VZ RRTPTNSMQMPNNPMTMVN RXEUH RMEMGNHOH",
  23,
  23,
  "B[MPTP RW[M[MFWF REHFHGGGE",
  "B[MPTP RW[M[MFWF REEEGFHGH",
  ":[MPTP RW[M[MFWF RDEGH R=H>H?G?E",
  ":[MPTP RW[M[MFWF RDEGH R=E=G>H?H",
  ":[MPTP RW[M[MFWF RHEEH R=H>H?G?E",
  ":[MPTP RW[M[MFWF RHEEH R=E=G>H?H",
  23,
  23,
  "I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE",
  "I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH",
  "I\\NMN[ RNOONQMTMVNWPWb RTEWH RMHNHOGOE",
  "I\\NMN[ RNOONQMTMVNWPWb RTEWH RMEMGNHOH",
  "I\\NMN[ RNOONQMTMVNWPWb RXEUH RMHNHOGOE",
  "I\\NMN[ RNOONQMTMVNWPWb RXEUH RMEMGNHOH",
  "I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RMAN@P?TAV@W?",
  "I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RMAN@P?TAV@W?",
  "A]L[LF RLPXP RX[XF RDHEHFGFE",
  "A]L[LF RLPXP RX[XF RDEDGEHFH",
  "9]L[LF RLPXP RX[XF RCEFH R<H=H>G>E",
  "9]L[LF RLPXP RX[XF RCEFH R<E<G=H>H",
  "9]L[LF RLPXP RX[XF RGEDH R<H=H>G>E",
  "9]L[LF RLPXP RX[XF RGEDH R<E<G=H>H",
  ">]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDHEHFGFE",
  ">]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDEDGEHFH",
  "MXRMRXSZU[ RQHRHSGSE",
  "MXRMRXSZU[ RQEQGRHSH",
  "MXRMRXSZU[ RTEWH RMHNHOGOE",
  "MXRMRXSZU[ RTEWH RMEMGNHOH",
  "MXRMRXSZU[ RXEUH RMHNHOGOE",
  "MXRMRXSZU[ RXEUH RMEMGNHOH",
  "MXRMRXSZU[ RQHRHSGSE RMAN@P?TAV@W?",
  "MXRMRXSZU[ RQEQGRHSH RMAN@P?TAV@W?",
  "GWR[RF RJHKHLGLE",
  "GWR[RF RJEJGKHLH",
  "?WR[RF RIELH RBHCHDGDE",
  "?WR[RF RIELH RBEBGCHDH",
  "?WR[RF RMEJH RBHCHDGDE",
  "?WR[RF RMEJH RBEBGCHDH",
  "DWR[RF RFAG@I?MAO@P? RJHKHLGLE",
  "DWR[RF RFAG@I?MAO@P? RJEJGKHLH",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQHRHSGSE",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RQEQGRHSH",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEWH RMHNHOGOE",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RTEWH RMEMGNHOH",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RXEUH RMHNHOGOE",
  "H[P[NZMYLWLQMONNPMSMUNVOWQWWVYUZS[P[ RXEUH RMEMGNHOH",
  23,
  23,
  "B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF REHFHGGGE",
  "B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF REEEGFHGH",
  ":]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH R=H>H?G?E",
  ":]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH R=E=G>H?H",
  ":]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH R=H>H?G?E",
  ":]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH R=E=G>H?H",
  23,
  23,
  "H[MMMXNZP[S[UZVYWWWPVNUM RQHRHSGSE",
  "H[MMMXNZP[S[UZVYWWWPVNUM RQEQGRHSH",
  "H[MMMXNZP[S[UZVYWWWPVNUM RTEWH RMHNHOGOE",
  "H[MMMXNZP[S[UZVYWWWPVNUM RTEWH RMEMGNHOH",
  "H[MMMXNZP[S[UZVYWWWPVNUM RXEUH RMHNHOGOE",
  "H[MMMXNZP[S[UZVYWWWPVNUM RXEUH RMEMGNHOH",
  "H[MMMXNZP[S[UZVYWWWPVNUM RQHRHSGSE RMAN@P?TAV@W?",
  "H[MMMXNZP[S[UZVYWWWPVNUM RQEQGRHSH RMAN@P?TAV@W?",
  23,
  "@[RQR[ RKFRQYF RCECGDHEH",
  23,
  "8[RQR[ RKFRQYF RBEEH R;E;G<H=H",
  23,
  "8[RQR[ RKFRQYF RFECH R;E;G<H=H",
  23,
  "=[RQR[ RKFRQYF R?A@@B?FAH@I? RCECGDHEH",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMHNHOGOE",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMEMGNHOH",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMHNHOGOE",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMEMGNHOH",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RMAN@P?TAV@W?",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RMAN@P?TAV@W?",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCHDHEGEE",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCECGDHEH",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;H<H=G=E",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;E;G<H=H",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;H<H=G=E",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;E;G<H=H",
  "=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCHDHEGEE",
  "=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCECGDHEH",
  39,
  39,
  40,
  40,
  41,
  41,
  42,
  42,
  29,
  29,
  44,
  44,
  45,
  45,
  23,
  23,
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMHNHOGOE RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEWH RMEMGNHOH RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMHNHOGOE RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RXEUH RMEMGNHOH RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQHRHSGSE RMAN@P?TAV@W? RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RQEQGRHSH RMAN@P?TAV@W? RR`RcSdTd",
  "G[MUWU RK[RFY[ RJHKHLGLE RR`RcSdTd",
  "G[MUWU RK[RFY[ RJEJGKHLH RR`RcSdTd",
  "?[MUWU RK[RFY[ RIELH RBHCHDGDE RR`RcSdTd",
  "?[MUWU RK[RFY[ RIELH RBEBGCHDH RR`RcSdTd",
  "?[MUWU RK[RFY[ RMEJH RBHCHDGDE RR`RcSdTd",
  "?[MUWU RK[RFY[ RMEJH RBEBGCHDH RR`RcSdTd",
  "D[MUWU RK[RFY[ RFAG@I?MAO@P? RJHKHLGLE RR`RcSdTd",
  "D[MUWU RK[RFY[ RFAG@I?MAO@P? RJEJGKHLH RR`RcSdTd",
  "I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RTEWH RMHNHOGOE RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RTEWH RMEMGNHOH RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RXEUH RMHNHOGOE RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RXEUH RMEMGNHOH RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RQHRHSGSE RMAN@P?TAV@W? RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RQEQGRHSH RMAN@P?TAV@W? RN`NcOdPd",
  "N]L[LF RLPXP RX[XF RR`RcSdTd",
  "A]L[LF RLPXP RX[XF RDEDGEHFH RR`RcSdTd",
  "9]L[LF RLPXP RX[XF RCEFH R<H=H>G>E RR`RcSdTd",
  "9]L[LF RLPXP RX[XF RCEFH R<E<G=H>H RR`RcSdTd",
  "9]L[LF RLPXP RX[XF RGEDH R<H=H>G>E RR`RcSdTd",
  "9]L[LF RLPXP RX[XF RGEDH R<E<G=H>H RR`RcSdTd",
  ">]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDHEHFGFE RR`RcSdTd",
  ">]L[LF RLPXP RX[XF R@AA@C?GAI@J? RDEDGEHFH RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMHNHOGOE RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEWH RMEMGNHOH RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMHNHOGOE RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RXEUH RMEMGNHOH RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQHRHSGSE RMAN@P?TAV@W? RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RQEQGRHSH RMAN@P?TAV@W? RR`RcSdTd",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCHDHEGEE RR`RcSdTd",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RCECGDHEH RR`RcSdTd",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;H<H=G=E RR`RcSdTd",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH R;E;G<H=H RR`RcSdTd",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;H<H=G=E RR`RcSdTd",
  "8^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH R;E;G<H=H RR`RcSdTd",
  "=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCHDHEGEE RR`RcSdTd",
  "=^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ R?A@@B?FAH@I? RCECGDHEH RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RNEOGQHSHUGVE",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMGWG",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RPESH RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RR`RcSdTd",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RTEQH RR`RcSdTd",
  23,
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMHNGPFTHVGWF",
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RMHNGPFTHVGWF RR`RcSdTd",
  30,
  "I[MUWU RK[RFY[ RM@W@",
  "G[MUWU RK[RFY[ RIELH",
  "G[MUWU RK[RFY[ RMEJH",
  "I[MUWU RK[RFY[ RR`RcSdTd",
  "NVQHRHSGSE",
  "NVR`RcSdTd",
  "NVQHRHSGSE",
  "KZMHNGPFTHVGWF",
  "LXMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I\\NMN[ RNOONQMTMVNWPWb RPESH RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RN`NcOdPd",
  "I\\NMN[ RNOONQMTMVNWPWb RTEQH RN`NcOdPd",
  23,
  "I\\NMN[ RNOONQMTMVNWPWb RMHNGPFTHVGWF",
  "I\\NMN[ RNOONQMTMVNWPWb RMHNGPFTHVGWF RN`NcOdPd",
  "B[MPTP RW[M[MFWF RDEGH",
  "B[MPTP RW[M[MFWF RHEEH",
  "A]L[LF RLPXP RX[XF RCEFH",
  "A]L[LF RLPXP RX[XF RGEDH",
  "G]L[LF RLPXP RX[XF RR`RcSdTd",
  "JZTEWH RMHNHOGOE",
  "JZXEUH RMHNHOGOE",
  "NVQHRHSGSE RMAN@P?TAV@W?",
  "MXRMRXSZU[ RNEOGQHSHUGVE",
  "MXRMRXSZU[ RMGWG",
  "MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA",
  "MXRMRXSZU[ RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  23,
  23,
  "MXRMRXSZU[ RMHNGPFTHVGWF",
  "MXRMRXSZU[ RMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "MWR[RF RN>O@QASAU@V>",
  "MWR[RF RM@W@",
  "GWR[RF RIELH",
  "GWR[RF RMEJH",
  23,
  "JZTEWH RMEMGNHOH",
  "JZXEUH RMEMGNHOH",
  "NVQEQGRHSH RMAN@P?TAV@W?",
  "H[MMMXNZP[S[UZVYWWWPVNUM RNEOGQHSHUGVE",
  "H[MMMXNZP[S[UZVYWWWPVNUM RMGWG",
  "H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA",
  "H[MMMXNZP[S[UZVYWWWPVNUM RNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  "H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX RQHRHSGSE",
  "H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX RQEQGRHSH",
  "H[MMMXNZP[S[UZVYWWWPVNUM RMHNGPFTHVGWF",
  "H[MMMXNZP[S[UZVYWWWPVNUM RMCNBPATCVBWA RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "I[RQR[ RKFRQYF RN>O@QASAU@V>",
  "I[RQR[ RKFRQYF RM@W@",
  "@[RQR[ RKFRQYF RBEEH",
  "@[RQR[ RKFRQYF RFECH",
  "A\\L[LFTFVGWHXJXMWOVPTQLQ RDEDGEHFH",
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RP>SA",
  "LXNFOGNHMGNFNH RVFWGVHUGVFVH RT>QA",
  16,
  23,
  23,
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RPESH RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RR`RcSdTd",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RTEQH RR`RcSdTd",
  23,
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMHNGPFTHVGWF",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RMHNGPFTHVGWF RR`RcSdTd",
  "B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RDEGH",
  "B]PFTFVGXIYMYTXXVZT[P[NZLXKTKMLINGPF RHEEH",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RBEEH",
  "@^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RFECH",
  "F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[ RR`RcSdTd",
  25,
  "NVQEQGRHSH",
  23,
  "F^",
  "LX",
  "F^",
  "LX",
  "NV",
  "OU",
  "PT",
  "H\\",
  "MW",
  "PT",
  "QS",
  24,
  24,
  24,
  24,
  24,
  46,
  46,
  "H\\JRZR",
  "LXVTNT",
  "F^IT[T",
  "F^IT[T",
  "H\\ODOb RUDUb",
  "JZJbZb RJ]Z]",
  "MWQGQFRDSC",
  "MWSFSGRIQJ",
  "MWSZS[R]Q^",
  "MWQFQGRISJ",
  "JZUGUFVDWC RMGMFNDOC",
  "JZOFOGNIMJ RWFWGVIUJ",
  "JZOZO[N]M^ RWZW[V]U^",
  "JZUFUGVIWJ RMFMGNIOJ",
  "I[MMWM RRFRb",
  "I[M[W[ RMMWM RRFRb",
  "E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ",
  "E_PPPV RQQQU RRQRU RSSUS RSRST ROPUSOV RVSOWOOVS",
  "MWRYSZR[QZRYR[",
  "MaRYSZR[QZRYR[ R\\Y]Z\\[[Z\\Y\\[",
  "MkRYSZR[QZRYR[ R\\Y]Z\\[[Z\\Y\\[ RfYgZf[eZfYf[",
  26,
  24,
  24,
  24,
  24,
  24,
  24,
  24,
  24,
  "FjJ[ZF RMFOGPIOKMLKKJIKGMF RcUeVfXeZc[aZ`XaVcU RYZZXYVWUUVTXUZW[YZ",
  "FvJ[ZF RMFOGPIOKMLKKJIKGMF RcUeVfXeZc[aZ`XaVcU RoUqVrXqZo[mZlXmVoU RYZZXYVWUUVTXUZW[YZ",
  "MWTFQL",
  "JZQFNL RWFTL",
  "G]NFKL RTFQL RZFWL",
  "MWPFSL",
  "JZSFVL RMFPL",
  "G]VFYL RPFSL RJFML",
  "LXVcR`Nc",
  "KYUMOSUY",
  "KYOMUSOY",
  "E_LMXY RXMLY RKRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT",
  "MaRYSZR[QZRYR[ RRSQGRFSGRSRF R\\Y]Z\\[[Z\\Y\\[ R\\S[G\\F]G\\S\\F",
  "I[QFQS RQYRZQ[PZQYQ[ RQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS RMGOFTFVGWIWKVMUNSORPQRQS",
  "E_JGZG",
  "OUb`aa^c\\dYeTfPfKeHdFcCaB`",
  "OUBFCEFCHBKAP@T@YA\\B^CaEbF",
  "E_N_VW RV_R[",
  "CaKRKW RRFRK RYRYW RFUKWPU RH[KWN[ RMIRKWI ROORKUO RTUYW^U RV[YW\\[",
  46,
  1,
  "KYQSVS RVbQbQDVD",
  "KYSSNS RNbSbSDND",
  "ImQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS RcYdZc[bZcYc[ R_GaFfFhGiIiKhMgNeOdPcRcS",
  "IeQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS R`YaZ`[_Z`Y`[ R`S_G`FaG`S`F",
  "MiRYSZR[QZRYR[ RRSQGRFSGRSRF R_Y`Z_[^Z_Y_[ R[G]FbFdGeIeKdMcNaO`P_R_S",
  "KYNMVMPb",
  "G^NMN[ RUMUXVZX[ RJMWMYNZP",
  "H\\NQNU RWPWV RPVPPOQOUPV RQPPPNQMSNUPVQVQP",
  "H\\VQVU RMPMV RTVTPUQUUTV RSPTPVQWSVUTVSVSP",
  "JZR[RV RWXRVMX RURRVOR",
  "MWQZQ[R]S^ RRNQORPSORNRP",
  "OUBFCEFCHBKAP@T@YA\\B^CaEbF Rb`aa^c\\dYeTfPfKeHdFcCaB`",
  "JZRFRK RMIRKWI ROORKUO RRFRK RWIRKMI RUORKOO",
  "JZM^WB RNFOGNHMGNFNH RVYWZV[UZVYV[",
  "E_JSKRNQQRSTVUYTZS",
  ">fB^B]C[EZOZQYRWSYUZ_Za[b]b^",
  "E_JSZS RR[RK RLMXY RXMLY",
  "E_LRMSLTKSLRLT RXYYZX[WZXYX[ RXKYLXMWLXKXM",
  "D`KFHL RQFNL RWFTL R]FZL",
  "E_KRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT",
  "E_LXMYLZKYLXLZ RLLMMLNKMLLLN RRRSSRTQSRRRT RXXYYXZWYXXXZ RXLYMXNWMXLXN",
  "MWRYSZR[QZRYR[ RRNSORPQORNRP",
  "E_KRLSKTJSKRKT RRYSZR[QZRYR[ RRKSLRMQLRKRM RYRZSYTXSYRYT",
  "E_JSZS RR[RK RLXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN",
  "CaR\\S]R^Q]R\\R^ RRRSSRTQSRRRT RRHSIRJQIRHRJ",
  "CaR^S_R`Q_R^R` RRVSWRXQWRVRX RRNSORPQORNRP RRFSGRHQGRFRH",
  "OU",
  24,
  24,
  24,
  24,
  24,
  23,
  23,
  23,
  23,
  23,
  24,
  24,
  24,
  24,
  24,
  24,
  "JZQ@S@UAVDVJUMSNQNOMNJNDOAQ@",
  "NVRDRN RR=Q>R?S>R=R?",
  23,
  23,
  "JZUFUN RQ@NJWJ",
  "JZV@O@NFPESEUFVHVKUMSNPNNM",
  "JZNHOFQESEUFVHVKUMSNQNOMNKNFOCPAR@U@",
  "JZM@W@PN",
  "JZQFOENCOAQ@S@UAVCUESFQFOGNINKOMQNSNUMVKVIUGSF",
  "JZVFUHSIQIOHNFNCOAQ@S@UAVCVHUKTMRNON",
  "I[LHXH RRBRN",
  "I[LHXH",
  "I[LJXJ RLFXF",
  "MWT=S>RAQFQJROSRTS",
  "MWP=Q>RASFSJROQRPS",
  "KZODON ROEQDSDUEVGVN",
  "JZQSSSUTVWV]U`SaQaO`N]NWOTQS",
  "JZVaNa RNVPURSRa",
  "JZNTPSSSUTVVVXUZNaVa",
  "JZNSVSRXSXUYV[V^U`SaPaN`",
  "JZUYUa RQSN]W]",
  "JZVSOSNYPXSXUYV[V^U`SaPaN`",
  "JZN[OYQXSXUYV[V^U`SaQaO`N^NYOVPTRSUS",
  "JZMSWSPa",
  "JZQYOXNVOTQSSSUTVVUXSYQYOZN\\N^O`QaSaU`V^V\\UZSY",
  "JZVYU[S\\Q\\O[NYNVOTQSSSUTVVV[U^T`RaOa",
  "I[L[X[ RRURa",
  "I[L[X[",
  "I[L]X] RLYXY",
  "MWTPSQRTQYQ]RbSeTf",
  "MWPPQQRTSYS]RbQePf",
  24,
  "KZOXQWSWUXVZVa RV`TaQaO`N^O\\Q[V[",
  "LYV`TaRaP`O^OZPXRWSWUXVZV[O\\",
  "KYQaO`N^NZOXQWSWUXVZV^U`SaQa",
  "KYNWVa RVWNa",
  "LYOXQWSWUXVZV^U`SaRaP`O^O]V\\",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "F[XMPMP[X[ RTGRFNFLGKHJJJPKRLSNTUT",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RSBG_ RZBN_",
  "F[WYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH RR[RM RRQSOTNVMXM",
  "HZTPMP RM[MFWF RJVRV",
  "H[LMTM RL[W[ RO[OIPGRFUFWG RLSTS",
  "D`I[IM RIOJNLMOMQNRPR[ RRPSNUMXMZN[P[[ RWHM`",
  "G]L[LFX[XF RHV\\V RHP\\P",
  "GyL[LFTFVGWHXJXMWOVPTQLQ R^MfM RaFaXbZd[f[ RlZn[r[tZuXuWtUrToTmSlQlPmNoMrMtN",
  "GmX[QQ RL[LFTFVGWHXJXMWOVPTQLQ R`Zb[f[hZiXiWhUfTcTaS`Q`PaNcMfMhN",
  "F^IFN[RLV[[F RHV\\V RHP\\P",
  "D`I[IFOFRGTIULUR RONOUPXRZU[[[[F",
  "I\\W[WF RWZU[Q[OZNYMWMQNOONQMUMWN RRHZH RXaNa",
  "F[HSQS RHNTN RWYVZS[Q[NZLXKVJRJOKKLINGQFSFVGWH",
  "G\\L[LF RX[OO RXFLR RLOTO",
  "JZLFXF RR[RF ROVUR ROPUL",
  "IoK[RFY[K[ R`b`QaObNdMgMiNjOkQkWjYiZg[d[bZ`X",
  "G]ITJSLRNSOTQUSTXOYLYIXGVFUFSGRIRLSOXTYVYWXYWZT[",
  "G\\L[LFTFVGWHXJXMWOVPTQLQ RHL\\L",
  "F[VGTFQFNGLIKKJOJRKVLXNZQ[S[VZWYWRSR RRCR^",
  "I[K[RFY[ RHV\\V RHP\\P",
  "H\\XZU[P[NZMYLWLUMSNRPQTPVOWNXLXJWHVGTFOFLG RRCR^",
  "HZVZT[P[NZMYLWLQMONNPMTMVN RRJR^",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "F^J[O[OWMVKTJQJLKIMGPFTFWGYIZLZQYTWVUWU[Z[",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "E_ZSJS RNWJSNO",
  "E_R[RK RNORKVO",
  "E_JSZS RVWZSVO",
  "E_RKR[ RVWR[NW",
  "E_JSZS RVWZSVO RNOJSNW",
  "E_R[RK RNORKVO RVWR[NW",
  "E_KLYZ RRLKLKS",
  "E_YLKZ RRLYLYS",
  "E_YZKL RRZYZYS",
  "E_KZYL RRZKZKS",
  "E_ZSJS RRWVO RNOJSNW",
  "E_JSZS RRONW RVWZSVO",
  "E_JWJQPQ RJQMTOUQTSRUQWRZU",
  "E_ZWZQTQ RZQWTUUSTQROQMRJU",
  "E_ZSJS RTOPSTW RNWJSNO",
  "E_R[RK RNURQVU RNORKVO",
  "E_JSZS RPOTSPW RVWZSVO",
  "E_RKR[ RVQRUNQ RVWR[NW",
  "E_JSVS RZOVSZW RNWJSNO",
  "E_ZSNS RJONSJW RVWZSVO",
  "E_ZOZW RJSZS RNWJSNO",
  "E_R[RK RV[N[ RNORKVO",
  "E_JOJW RZSJS RVWZSVO",
  "E_RKR[ RNKVK RVWR[NW",
  "E_N[V[ RR[RK RNWR[VW RNORKVO",
  "E_NWJSNO RJSWSYRZPYNWM",
  "E_VWZSVO RZSMSKRJPKNMM",
  "E_NWJSNO RJSWSYRZPYNWMUNTPTW",
  "E_VWZSVO RZSMSKRJPKNMMONPPPW",
  "E_PUJUJO RZWZQTQ RZQWTUUSTQROQMRJU",
  "E_JSZS RTOPW RNOJSNW RVWZSVO",
  "E_PWR[VY ROKLTVOR[",
  "E_V[VOJO RNSJONK",
  "E_N[NOZO RVSZOVK",
  "E_VKVWJW RNSJWN[",
  "E_NKNWZW RVSZWV[",
  "E_JOVOV[ RZWV[RW",
  "E_VKVWJW RNSJWN[",
  "E_OQKUGQ RYRYQXNVLSKQKNLLNKQKU",
  "E_UQYU]Q RKRKQLNNLQKSKVLXNYQYU",
  "E_KLYZ RKHYH RRLKLKS",
  "E_JWZW RJKJS RZSZ[ RZOJO RNSJONK RV[ZWVS",
  "E_[KUKUQ RMMLNKQKSLVNXQYSYVXXVYSYQXNUK",
  "E_IKOKOQ RWMXNYQYSXVVXSYQYNXLVKSKQLNOK",
  "E_ZSJSNO",
  "E_ZSJSNW",
  "E_R[RKVO",
  "E_R[RKNO",
  "E_JSZSVO",
  "E_JSZSVW",
  "E_RKR[VW",
  "E_RKR[NW",
  "E_ZWJW RJOZO RVSZOVK RN[JWNS",
  "E_N[NK RVKV[ RJONKRO RRWV[ZW",
  "E_JWZW RZOJO RNSJONK RV[ZWVS",
  "E_ZWJW RJOZO RN[JWNSJONK",
  "E_N[NK RVKV[ RJONKROVKZO",
  "E_JWZW RZOJO RV[ZWVSZOVK",
  "E_VKV[ RN[NK RZWV[RWN[JW",
  "E_JVZVVZ RZPJPNL",
  "E_ZVJVNZ RJPZPVL",
  "E_ZPMP RZVMV RRXVN ROXJSON",
  "E_MVWV RMPWP RSNQX ROXJSON RUNZSUX",
  "E_JVWV RJPWP RRNNX RUNZSUX",
  "E_ZPMP RZVMV ROXJSON",
  "E_ONO[ RUNU[ RWPRKMP",
  "E_JVWV RJPWP RUNZSUX",
  "E_UXUK ROXOK RMVR[WV",
  "E_MVWV RMPWP ROXJSON RUNZSUX",
  "E_OXON RUXUN RMVR[WV RWPRKMP",
  "E_[XOL RW\\KP RSLKLKT",
  "E_IXUL RM\\YP RQLYLYT",
  "E_INUZ RMJYV RQZYZYR",
  "E_[NOZ RWJKV RSZKZKR",
  "E_ZXOX RZSJS RZNON RQLJSQZ",
  "E_JXUX RJSZS RJNUN RSLZSSZ",
  "E_NWJSNO RZUWQTUQQNULSJS",
  "E_VWZSVO RJUMQPUSQVUXSZS",
  "E_NXVX RNSVS RR[RK RNORKVO",
  "E_VNNN RVSNS RRKR[ RVWR[NW",
  "E_ZSWS RSSQS RMSJS RNOJSNW",
  "E_R[RX RRTRR RRNRK RNORKVO",
  "E_JSMS RQSSS RWSZS RVWZSVO",
  "E_RKRN RRRRT RRXR[ RVWR[NW",
  "E_ZSJS RJWJO RNOJSNW",
  "E_JSZS RZOZW RVWZSVO",
  "E_ZPZVOVOXJSONOPZP",
  "E_U[O[OPMPRKWPUPU[",
  "E_JVJPUPUNZSUXUVJV",
  "E_OKUKUVWVR[MVOVOK",
  "E_U[O[OWUWU[ RUSOSOPMPRKWPUPUS",
  "E_W[M[MWOWOPMPRKWPUPUWWWW[",
  "E_ONUN RW[M[MWOWOPMPRKWPUPUWWWW[",
  "E_RKR[ RW[M[MWOWOPMPRKWPUPUWWWW[",
  "E_PPMPRKWPTP RU[O[OSMSRNWSUSU[",
  "E_PPMPRKWPTP RW[M[MWOWOSMSRNWSUSUWWWW[",
  "E_JNNNNPUPUNZSUXUVNVNXJXJN",
  "E_Z[NO RZKJKJ[ RUONONV",
  "E_JKVW RJ[Z[ZK ROWVWVP",
  "E_MPRKWPUPUVWVR[MVOVOPMP",
  "E_JSZS RVWZSVO RTRTTSVQWOWMVLTLRMPOOQOSPTR",
  "E_V[VK RNKN[ RZOVKRO RRWN[JW",
  "E_J[Z[ RJKZK RZSJS RVGZKVOZSVWZ[V_",
  "E_ZSJS RTWTO RNOJSNW",
  "E_JSZS RPOPW RVWZSVO",
  "E_JSZS RRORW RNOJSNW RVWZSVO",
  "E_ZSJS RWWWO RRWRO RNOJSNW",
  "E_JSZS RMOMW RRORW RVWZSVO",
  "E_JSZS RPOPW RTOTW RNWJSNO RVWZSVO",
  "E_NSZS RNWNOJSNW",
  "E_VSJS RVWVOZSVW",
  "E_NSVS RNWJSNONW RVWVOZSVW",
  "I[MLWL RKFR[YF",
  "HZVHUGSFPFNGMHLKLVMYNZP[S[UZVY",
  "H[WOVNTMPMNNMOLQLWMYNZP[S[UZVYWWWJVHUGSFOFMG",
  "I\\WPPP RM[W[WFMF",
  "I\\WQPQ RMFWFW[M[ RXCL`",
  "C`G[\\F ROFTFXHZJ\\N\\SZWXYT[O[KYIWGSGNIJKHOF",
  "I[K[RFY[K[",
  "I[YFR[KFYF",
  "C`\\QGQ R\\GOGKIIKGOGSIWKYO[\\[",
  "C`[CH^ R\\QGQ R\\GOGKIIKGOGSIWKYO[\\[",
  "E_JSZS RZZPZMYKWJTJRKOMMPLZL",
  "DaHP]P RHZUZYX[V]R]N[JYHUFHF",
  "DaI^\\C RHP]P RHZUZYX[V]R]N[JYHUFHF",
  "E_ZSJS RJZTZWYYWZTZRYOWMTLJL",
  "E_M[WQ RMZWP RMYWO RMXWN RMWWM RMVWL RMUWK RMTVK RMSUK RMRTK RMQSK RMPRK RMOQK RMNPK RMMOK RMLNK RN[WR RO[WS RP[WT RQ[WU RR[WV RS[WW RT[WX RU[WY RV[WZ RM[MKWKW[M[",
  "E_Z`ZFJFJ`",
  "E_ZFZ`J`JF",
  "E_Z`I`TSIF[F",
  0,
  "E_ZWJW RROR_ RJKZK",
  "E_JSZS RR[RK RRDQERFSERDRF",
  1,
  "KYID[_",
  "E_KOYW RR[RK RYOKW",
  "E_PQRPTQUSTURVPUOSPQ",
  "E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ",
  "IbMTQSS[bB",
  "IbMTQSS[bB RN@V@RESEUFVHVKUMSNPNNM",
  "IbMTQSS[bB RUFUN RQ@NJWJ",
  "E_XPWPUQQUOVMULSMQOPQQUUWVXV",
  "E_TQVPXQYSXUVVTUPQNPLQKSLUNVPUTQ",
  "E_JKJ[Z[",
  "E_ZKJ[Z[",
  "E_ZKJ[Z[ RPSRUTZT]",
  "E_Z[JSZK RSYTWUSTOSM",
  22,
  "H\\NUVQ RRDRb",
  "H\\ODOb RUDUb",
  "H\\LVXP RODOb RUDUb",
  "E_[[RKI[",
  "E_IKR[[K",
  "E_Z[ZQXMTKPKLMJQJ[",
  "E_JKJULYP[T[XYZUZK",
  "H\\L]M_O`Q_R]RISGUFWGXI",
  "D`H]I_K`M_N]NIOGQFSGTI RP]Q_S`U_V]VIWGYF[G\\I",
  "@dD]E_G`I_J]JIKGMFOGPI RL]M_O`Q_R]RISGUFWGXI RT]U_W`Y_Z]ZI[G]F_G`I",
  "H\\L]M_O`Q_R]RISGUFWGXI RRMUNWPXSWVUXRYOXMVLSMPONRM",
  "D`H]I_K`M_N]NIOGQFSGTI RP]Q_S`U_V]VIWGYF[G\\I RVMYN[P\\S[VYXVYNYKXIVHSIPKNNMVM",
  "@dD]E_G`I_J]JIKGMFOGPI RL]M_O`Q_R]RISGUFWGXI RT]U_W`Y_Z]ZI[G]F_G`I RZM]N_P`S_V]XZYJYGXEVDSEPGNJMZM",
  "H\\URXU[R RLSMPONRMUNWPXSXU RL]M_O`Q_R]RISGUFWGXI",
  "H\\UQXT[Q RL]M_O`Q_R]RISGUFWGXI RLSMPONRMUNWPXSWVUXRYOXMVLS",
  "H\\UUXR[U RL]M_O`Q_R]RISGUFWGXI RLSMPONRMUNWPXSWVUXRYOXMVLS",
  "E_KXLYKZJYKXKZ RRLSMRNQMRLRN RYXZYYZXYYXYZ",
  "E_YNXMYLZMYNYL RRZQYRXSYRZRX RKNJMKLLMKNKL",
  "JZRXSYRZQYRXRZ RRLSMRNQMRLRN",
  "E_LXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN",
  "E_JSZS RRFQGRHSGRFRH",
  "E_JSTS RYXZYYZXYYXYZ RYLZMYNXMYLYN",
  "E_JSZS RLXMYLZKYLXLZ RLLMMLNKMLLLN RXXYYXZWYXXXZ RXLYMXNWMXLXN",
  "E_JSKRNQQRSTVUYTZS RRXSYRZQYRXRZ RRLSMRNQMRLRN",
  "E_JSKRNQQRSTVUYTZS",
  "E_ZSYRVQSRQTNUKTJS",
  "E_WPYQZSYUWVTUPQMPKQJSKUMV",
  "E_JSKNLLNKPLQNSXTZV[XZYXZS",
  "E_RKSLTOSRQTPWQZR[",
  "E_JSKRNQQRSTVUYTZS RVKN[",
  "E_ZPJP RZVYWVXSWQUNTKUJV",
  "E_JVZV RJPKONNQOSQVRYQZP",
  "E_JVZV RJPKONNQOSQVRYQZP RVKN[",
  "E_JYZY RJSZS RJMKLNKQLSNVOYNZM",
  "E_JYZY RJSZS RUPO\\ RJMKLNKQLSNVOYNZM",
  "E_JYZY RJSZS RJMKLNKQLSNVOYNZM RXGL_",
  "E_JVKUNTQUSWVXYWZV RJPKONNQOSQVRYQZP",
  "E_JVKUNTQUSWVXYWZV RJPKONNQOSQVRYQZP RVKN[",
  "E_JYZY RJSKRNQQRSTVUYTZS RJMKLNKQLSNVOYNZM",
  "E_JYKXNWQXSZV[YZZY RJSKRNQQRSTVUYTZS RJMKLNKQLSNVOYNZM",
  "E_ZYJY RZSJS RZMYLVKSLQNNOKNJM",
  "E_JXLWPVTVXWZX RJNLOPPTPXOZN",
  "E_JVNVNWOYQZSZUYVWVVZV RJPNPNOOMQLSLUMVOVPZP",
  "E_ZVJV RJPNPNOOMQLSLUMVOVPZP",
  "E_JPZP RZVJV RRHQIRJSIRHRJ",
  "E_JPZP RZVJV RRXSYRZQYRXRZ RRLSMRNQMRLRN",
  "E_JPZP RZVJV RKJLKKLJKKJKL RYZZ[Y\\X[YZY\\",
  "E_ZPJP RJVZV RYJXKYLZKYJYL RKZJ[K\\L[KZK\\",
  "AcNP^P R^VNV RGVHWGXFWGVGX RGNHOGPFOGNGP",
  "AcVPFP RFVVV R]V\\W]X^W]V]X R]N\\O]P^O]N]P",
  "E_JPZP RZVJV RPQRPTQUSTURVPUOSPQ",
  "E_JPZP RZVJV RRJPIOGPERDTEUGTIRJ",
  "E_JPZP RZVJV RNJOHQGSGUHVJ",
  "E_JPZP RZVJV RNJRGVJ",
  "E_JPZP RZVJV RNGRJVG",
  "E_JPZP RZVJV RRATGOCUCPGRA",
  "E_JPZP RZVJV RR?NJVJR?",
  "E_JPZP RYC]C RZVJV R]?[@ZBZJ RM?MJKJIIHGHEICKBMB RQFVFVCUBRBQCQIRJUJ",
  "E_JPZP RZVJV RMBMJ RMCNBQBRCRJ RRCSBVBWCWJ",
  "E_JPZP RZVJV RRHSIRJQIRHRJ RN@P?S?U@VBUDSE",
  "E_JPZP RTMPY RZVJV",
  "E_JYZY RJSZS RJMZM",
  "E_JYZY RJSZS RJMZM RXGL_",
  "E_J\\Z\\ RJPZP RJJZJ RZVJV",
  "E_ZZJZ RZVJPZJ",
  "E_JZZZ RJVZPJJ",
  "E_J]Z] RZWJW RZSJMZG",
  "E_Z]J] RJWZW RJSZMJG",
  "E_J]Z] RTTP` RZWJW RZSJMZG",
  "E_JWZW RTTP` RZ]J] RJSZMJG",
  "=gRMBSRY RbMRSbY",
  "=gRMbSRY RBMRSBY",
  "I[OCPDRGSITLUQUUTZS]R_PbOc RUcTbR_Q]PZOUOQPLQIRGTDUC",
  "E_JXLWPVTVXWZX RJNLOPPTPXOZN RVKN[",
  "E_ZMJSZY RVKN[",
  "E_JMZSJY RVKN[",
  "E_ZZJZ RZVJPZJ RXGL_",
  "E_JZZZ RJVZPJJ RXGL_",
  "E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ",
  "E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ",
  "E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ RXGL_",
  "E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ RXGL_",
  "E_JSZYJ_ RZSJMZG",
  "E_ZSJYZ_ RJSZMJG",
  "E_JSZYJ_ RZSJMZG RXGL_",
  "E_ZSJYZ_ RJSZMJG RXGL_",
  "E_ZKXNVPRRJSRTVVXXZ[",
  "E_JKLNNPRRZSRTNVLXJ[",
  "E_JVRWVYX[Z^ RZHXKVMROJPRQVSXUZX",
  "E_ZVRWNYL[J^ RJHLKNMROZPRQNSLUJX",
  "E_J[KZNYQZS\\V]Y\\Z[ RZHXKVMROJPRQVSXUZX",
  "E_J[KZNYQZS\\V]Y\\Z[ RJXLUNSRQZPRONMLKJH",
  "E_ZKXNVPRRJSRTVVXXZ[ RVKN[",
  "E_JKLNNPRRZSRTNVLXJ[ RVKN[",
  "E_ZMNMLNKOJQJUKWLXNYZY",
  "E_JMVMXNYOZQZUYWXXVYJY",
  "E_ZMNMLNKOJQJUKWLXNYZY RVKN[",
  "E_JMVMXNYOZQZUYWXXVYJY RVKN[",
  "E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV",
  "E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV",
  "E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV RXGL_",
  "E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV RXGL_",
  "E_J\\Z\\ RZJNJLKKLJNJRKTLUNVZV RSYQ_",
  "E_Z\\J\\ RJJVJXKYLZNZRYTXUVVJV RSYQ_",
  "E_JKJULYP[T[XYZUZK ROSUS RSUUSSQ",
  "E_JKJULYP[T[XYZUZK RRRQSRTSSRRRT",
  "E_JKJULYP[T[XYZUZK RLSXS RRMRY",
  "E_ZYJYJMZM",
  "E_JYZYZMJM",
  "E_Z\\J\\ RZVJVJJZJ",
  "E_J\\Z\\ RJVZVZJJJ",
  "E_Z[ZKJKJ[",
  "E_JKJ[Z[ZK",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLSXS RRMRY",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLSXS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RMNWX RWNMX",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RWFM^",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRRQSRTSSRRRT",
  47,
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRNRS RMQRSWQ ROWRSUW",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLUXU RLQXQ",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RNSVS",
  "E_JKZKZ[J[JK RLSXS RRMRY",
  "E_JKZKZ[J[JK RLSXS",
  "E_JKZKZ[J[JK RMNWX RWNMX",
  "E_JKZKZ[J[JK RRRQSRTSSRRRT",
  "E_J[JK RJSZS",
  "E_Z[ZK RZSJS",
  "E_ZKJK RRKR[",
  "E_J[Z[ RR[RK",
  "I[NSVS RNKN[",
  "I[NVVV RNPVP RNKN[",
  "E_JVZV RJPZP RJKJ[",
  "E_JKJ[ RPSZS RPKP[",
  "E_JKJ[ ROKO[ RTKT[ RYSTS",
  "E_JKJ[ RPVYV RPPYP RPKP[",
  "E_J[JK RJSZS RXGL_",
  "E_JVZV RJPZP RJKJ[ RXGL_",
  "E_JKJ[ RPSZS RPKP[ RXGL_",
  "E_JKJ[ RPVYV RPPYP RPKP[ RXGL_",
  "E_VKXLYNXPVQRRJSRTVUXVYXXZV[",
  "E_NKLLKNLPNQRRZSRTNULVKXLZN[",
  "E_JSZYZMJS",
  "E_ZSJYJMZS",
  "E_Z[J[ RJQZWZKJQ",
  "E_J[Z[ RZQJWJKZQ",
  "BbXQXU RYQYU RZPZV R[Q[U R\\Q\\U RMSLQJPHQGSHUJVLUMSWSXUZV\\U]S\\QZPXQWS",
  "BbLQLU RKQKU RJPJV RIQIU RHQHU RWSXQZP\\Q]S\\UZVXUWSMSLUJVHUGSHQJPLQMS",
  "E_JSTSUUWVYUZSYQWPUQTS",
  "E_JSNS RR[RW RRKRO RZSVS",
  "I[NFVF RRFR[",
  "E_J[Z[ RZKRVJK",
  "E_ZKJK RJ[RPZ[",
  "E_JKZK RZPR[JP",
  "E_JKJ[Z[ RJOLOQQTTVYV[",
  "E_Z[ZKJ[Z[",
  "Bb_`REE`",
  "BbEFRa_F",
  "Bb]`]O\\KZHWFSEQEMFJHHKGOG`",
  "BbGFGWH[J^M`QaSaW`Z^\\[]W]F",
  "E_RaJSRFZSRa",
  26,
  "I[RRTXOTUTPXRR",
  "E_ZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN RLMXY RXMLY",
  "E_JKZ[ZKJ[JK",
  "E_ZKJ[JKZ[",
  "E_JKZ[ZKJ[",
  "E_JKZ[ RRSJ[",
  "E_ZKJ[ RRSZ[",
  "E_ZVJV RZPYOVNSOQQNRKQJP",
  "E_JKMMOOQSR[SSUOWMZK",
  "E_Z[WYUWSSRKQSOWMYJ[",
  "E_ZPSPQQPSQUSVZV RZ\\Q\\N[KXJUJQKNNKQJZJ",
  "E_JPQPSQTSSUQVJV RJ\\S\\V[YXZUZQYNVKSJJJ",
  "E_U[UTTRRQPROTO[ R[[[RZOWLTKPKMLJOIRI[",
  "E_OKORPTRUTTURUK RIKITJWMZP[T[WZZW[T[K",
  "E_RKR[ RL[LSMPNOQNSNVOWPXSX[",
  "E_JPZP RZVJV RODOb RUDUb",
  "E_ZMJSZY RYRXSYTZSYRYT",
  "E_JMZSJY RKRJSKTLSKRKT",
  "5oJM:SJY RZMJSZY RjMZSjY",
  "5oZMjSZY RJMZSJY R:MJS:Y",
  "E_ZSJS RJWZ[J_ RZOJKZG",
  "E_JSZS RZWJ[Z_ RJOZKJG",
  "E_ZLJL RZPJVZ\\",
  "E_JLZL RJPZVJ\\",
  "E_JPROVMXKZH RZ^X[VYRWJVRUVSXQZN",
  "E_ZPRONMLKJH RJ^L[NYRWZVRUNSLQJN",
  "E_JPROVMXKZH RZ^X[VYRWJVRUVSXQZN RXGL_",
  "E_ZPRONMLKJH RJ^L[NYRWZVRUNSLQJN RXGL_",
  "E_Z\\J\\ RZVJVJJZJ RXGL_",
  "E_J\\Z\\ RJVZVZJJJ RXGL_",
  "E_Z\\J\\ RZVJVJJZJ RSYQ_",
  "E_J\\Z\\ RJVZVZJJJ RSYQ_",
  "E_ZVJPZJ RJZKYNXQYS[V\\Y[ZZ RSWQ]",
  "E_JVZPJJ RJZKYNXQYS[V\\Y[ZZ RSWQ]",
  "E_J[KZNYQZS\\V]Y\\Z[ RZHXKVMROJPRQVSXUZX RSXQ^",
  "E_J[KZNYQZS\\V]Y\\Z[ RJXLUNSRQZPRONMLKJH RSXQ^",
  "E_JSZYZMJS RXGL_",
  "E_ZSJYJMZS RXGL_",
  "E_Z[J[ RJQZWZKJQ RXGL_",
  "E_J[Z[ RZQJWJKZQ RXGL_",
  "CaR\\S]R^Q]R\\R^ RRRSSRTQSRRRT RRHSIRJQIRHRJ",
  "CaHRISHTGSHRHT RRRSSRTQSRRRT R\\R]S\\T[S\\R\\T",
  "Ca\\H[I\\J]I\\H\\J RRRQSRTSSRRRT RH\\G]H^I]H\\H^",
  "CaHHIIHJGIHHHJ RRRSSRTQSRRRT R\\\\]]\\^[]\\\\\\^",
  ">`BQ\\Q R\\GOGKIIKGOGSIWKYO[\\[",
  ">`GQ\\Q R\\M\\U R\\GOGKIIKGOGSIWKYO[\\[",
  "E_JSZS RZPZV RZZPZMYKWJTJRKOMMPLZL",
  "C`\\QGQ R\\GOGKIIKGOGSIWKYO[\\[ RR@QARBSAR@RB",
  "C`GA\\A R\\QGQ R\\[O[KYIWGSGOIKKIOG\\G",
  "E_JSZS RZGJG RZLPLMMKOJRJTKWMYPZZZ",
  "C`G`\\` R\\PGP R\\FOFKHIJGNGRIVKXOZ\\Z",
  "C`HT\\T RHN\\N R\\GOGKIIKGOGSIWKYO[\\[",
  "DfbQHQ RHGUGYI[K]O]S[WYYU[H[",
  "Df]QHQ RHMHU RHGUGYI[K]O]S[WYYU[H[",
  "E_ZSJS RJPJV RJZTZWYYWZTZRYOWMTLJL",
  "Da]AHA RHQ]Q RH[U[YY[W]S]O[KYIUGHG",
  "E_ZSJS RJGZG RJLTLWMYOZRZTYWWYTZJZ",
  "C`GQ\\Q R\\GGGG[\\[",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RZKJ[",
  "E_JQRWROZU",
  "E_J[JORGZOZ[J[",
  "E_NORKVO",
  "E_VWR[NW",
  "E_ZKJK RJ[RPZ[",
  "E_JNZN RJHZH RJ[RSZ[",
  "H\\RDSETGSIRJQLRNSOTQSSRTQVRXSYT[S]R^Q`Rb",
  "KYQbQDVD",
  "KYSbSDND",
  "KYQDQbVb",
  "KYSDSbNb",
  "E_RWR[ RVSZS",
  "E_RWR[ RNSJS",
  "E_RORK RVSZS",
  "E_RORK RNSJS",
  "E_ZQJQJV",
  "D`[JZLYPYVZZ[\\Y[UZOZK[I\\JZKVKPJLIJKKOLULYK[J",
  "E_JSJQLMPKTKXMZQZS",
  "E_JSJQLMPKTKXMZQZS RJSZS",
  "E_JMLLPKTKXLZMR[JM",
  "E_PUJ[ RTKWLYNZQYTWVTWQVOTNQONQLTK",
  "E_JSZS RR[RK RVRUPSOQOOPNRNTOVQWSWUVVTVR",
  "E_JWZW RJOZO RNKN[ RVKV[",
  "E_LPXPZO[MZKXJVKUMUYV[X\\Z[[YZWXVLVJWIYJ[L\\N[OYOMNKLJJKIMJOLP",
  "E_ZUJUJP",
  "E_RORSUS RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_M[RVW[ RN[RWV[ RP[RYT[ RS[RZQ[ RU[RXO[ RYMRPKMROYM RJFZFZKYMKTJVJ[Z[ZVYTKMJJJF",
  "JZVFNFNM",
  "JZNFVFVM",
  "JZV[N[NT",
  "JZN[V[VT",
  "H\\RbRMSITGVFXGYI",
  "H\\RDRYQ]P_N`L_K]",
  "E_JUKTMSRRWSYTZU",
  "E_ZQYRWSRTMSKRJQ",
  "E_LKHK RXK\\K RNORKVO",
  "@dXK^K RFKLKX[^[",
  "AfJKZ[ RZKJ[ RFKZKbSZ[F[FK",
  "AcJKZ[ RZKJ[ RFK^K^[F[FK",
  "9k>VfV R>LfL RCQCL RD[DV REVEQ RFLFG RHQHL RJVJQ RK[KV RKLKG RMQML ROVOQ RPLPG RRQRL RTVTQ RULUG RWQWL RYVYQ RZ[ZV RZLZG R\\Q\\L R^V^Q R_L_G R`[`V R>QaQaL R>[>GfGf[>[",
  "KYUcOSUC",
  "KYOcUSOC",
  ">cZKJ[ RJKZ[ R^KJKBSJ[^[^K",
  "AcKOKW RR[YW RRKYO RRE^L^ZRaFZFLRE",
  "H\\PNKX RYNTX RVRUPSOQOOPNRNTOVQWSWUVVTVR",
  "E_N[J[JW RZSRSJ[ RVRUPSOQOOPNRNTOVQWSWUVVTVR",
  "E_JSZS RNYVY RVMNM",
  "E_RPRKNN RZPZKVN RRKJ[R[ZK",
  "H\\LS[S RRMRY RXP[SXV RVRUPSOQOOPNRNTOVQWSWUVVTVR",
  "E_ZSJ\\JJZS RJSZS",
  "E_J[JRZ[J[",
  "E_JWJ[Z[ZW",
  "E_VWR[NW",
  "D`JaZa RJFZF RRFRa",
  "D`MFWFWaMaMF",
  "D`IF[F[aIaIF RJPZP RZVJV",
  "D`IF[F[aIaIF RZSJS RRXSYRZQYRXRZ RRLSMRNQMRLRN",
  "D`IF[F[aIaIF RRJ[SR\\ISRJ",
  "D`IF[F[aIaIF RPQRPTQUSTURVPUOSPQ",
  "D`IF[F[aIaIF RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRbRD",
  47,
  "E_JSZS RZKJ[",
  "E_JSZS RJKZ[",
  "D`IaIF[F[aIa[F",
  "D`[a[FIFIa[aIF",
  "D`IF[F[aIaIF RZMJSZY",
  "D`IF[F[aIaIF RJMZSJY",
  "E_ZSJS RNWJSNO RR[RK",
  "E_JSZS RVWZSVO RR[RK",
  "D`IF[F[aIaIF RZSJS RNWJSNO",
  "D`IF[F[aIaIF RJSZS RVWZSVO",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RLGX_",
  "E_J[Z[ RR[RK RZaJa",
  "E_RKX[L[RK RRbRD",
  "D`IF[F[aIaIF RIKR[[K",
  "D`IF[F[aIaIF RRKX[L[RK",
  "E_ZKJK RRKR[ RVRUPSOQOOPNRNTOVQWSWUVVTVR",
  "E_R[RK RNORKVO RJSZS",
  "D`IF[F[aIaIF RR[RK RNORKVO",
  "E_ZKJK RRKR[ RMEWE",
  "E_R[LKXKR[ RRbRD",
  "D`IF[F[aIaIF R[[RKI[",
  "D`IF[F[aIaIF RR[LKXKR[",
  "E_J[Z[ RR[RK RPQRPTQUSTURVPUOSPQ",
  "E_RKR[ RVWR[NW RJSZS",
  "D`IF[F[aIaIF RRKR[ RVWR[NW",
  "JZJ]Z] RSFQJ",
  "E_RKX[L[RK RJ]Z]",
  "E_RJ[SR\\ISRJ RJ]Z]",
  "E_PQRPTQUSTURVPUOSPQ RJ]Z]",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RJ]Z]",
  "E_Z[ZQXMTKPKLMJQJ[ RPQRPTQUSTURVPUOSPQ",
  "D`IF[F[aIaIF RSFQJ",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRPTVORURPVRP",
  "D`IF[F[aIaIF RRYSZR[QZRYR[ RRNSORPQORNRP",
  "E_ZKJK RRKR[ RNDOENFMENDNF RVDWEVFUEVDVF",
  "E_R[LKXKR[ RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "E_RKWZJQZQMZRK RNDOENFMENDNF RVDWEVFUEVDVF",
  "E_PQRPTQUSTURVPUOSPQ RNIOJNKMJNINK RVIWJVKUJVIVK",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RNDOENFMENDNF RVDWEVFUEVDVF",
  "E_JKJULYP[T[XYZUZK RRbRD",
  "E_ZMNMLNKOJQJUKWLXNYZY RRbRD",
  "E_JSKRNQQRSTVUYTZS RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "E_JMZSJY RNFOGNHMGNFNH RVFWGVHUGVFVH",
  "E_JSZS RSZS[R]Q^",
  "E_R[LKXKR[ RJSKRNQQRSTVUYTZS",
  "H\\QFSFUGVHWJXNXSWWVYUZS[Q[OZNYMWLSLNMJNHOGQF RJPKONNQOSQVRYQZP",
  "E_JSKRNQQRSTVUYTZS RRbRD",
  "MWSZS[R]Q^ RRNSORPQORNRP RJ]Z]",
  "D`IF[F[aIaIF RJPZP RTMPY RZVJV",
  "D`IF[F[aIaIF RQYRZQ[PZQYQ[ RMGOFTFVGWIWKVMUNSORPQRQS",
  "E_IKR[[K RJSKRNQQRSTVUYTZS",
  "E_[[RKI[ RJSKRNQQRSTVUYTZS",
  36,
  "H\\MbMQNOONQMTMVNWOXQXWWYVZT[Q[OZMX",
  43,
  "H]YMVWUYTZR[P[NZMYLVLRMONNPMRMTNUOVQWXXZZ[ RJ]Z]",
  "HZLTST RVZT[P[NZMYLWLQMONNPMTMVN RJ]Z]",
  "MXRMRXSZU[ RJ]Z]",
  "G]RTRX RMMLNKPKXLZN[O[QZRXSZU[V[XZYXYPXNWM RJ]Z]",
  34,
  "IbMTQSS[bB RXL`L",
  "A_J_F_F[ RJKJ[Z[ RF_OVEQOG",
  "E_JWNWN[V[VWZW",
  "E_NSN[J[ RVSV[Z[ RJSJQLMPKTKXMZQZSJS",
  "E_PQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ RRbRD",
  "E_VWR[NW ROEQDSDUEVGVN RVMTNQNOMNKOIQHVH",
  "BbF[^[ RGLIKKKMLNNNU RUSVTUUTTUSUU R]S^T]U\\T]S]U RNTLUIUGTFRGPIONO",
  "BbF[N[ RV[^[ RGLIKKKMLNNNU RWLYK[K]L^N^U RNTLUIUGTFRGPIONO R^T\\UYUWTVRWPYO^O",
  "BbHPDP RJUFX RJKFH R^XZU R^HZK R`P\\P RTTRUPUNTMRMQNNPLRKVKTU",
  "=_RKR[B[BKRK RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_JKZKZ[J[JK RRbRD",
  "C_ESUS RQWUSQO RJWJ[Z[ZKJKJO",
  "@dX[^[ RZO^KZG RF[L[XK^K",
  "E_KOYW RR[RK RYOKW RRMONMPLSMVOXRYUXWVXSWPUNRM",
  "E_JSOSR[USZS RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_R[KOYOR[ RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_STJK RJOJKNK RSKTKXMZQZUXYT[P[LYJUJT",
  "D`KNKROR RYRWPTOPOMPKR RNXMVKUIVHXIZK[MZNX RVXWZY[[Z\\X[VYUWVVX",
  "E_I[N[NKVKV[[[",
  "E_I[V[VK RN[NK[K",
  "E_JKZK RJSRKZSR[JS",
  "E_Z[J[ RZSR[JSRKZS",
  "E_JKZK RJSRKZSR[JS RJSZS",
  "E_Z[J[ RZSR[JSRKZS RJSZS",
  "E_JVLV RJPZP RQVSV RXVZV",
  "BbL[FQLGXG^QX[L[",
  "D`IF[F[aIaIF",
  "MWTFQL",
  "AcZSJS RRORK RR[RW RNOJSNW R^[F[FK^K^[",
  "AcJSZS RRWR[ RRKRO RVWZSVO RFK^K^[F[FK",
  "BbLHQHQC RLSLHQCXCXSLS RLKJKHLGNGXHZJ[Z[\\Z]X]N\\LZKXK",
  "BbROJW RZORW RGXGNHLJKZK\\L]N]X\\ZZ[J[HZGX",
  "H\\XDVGUITLSQR[Rb",
  22,
  "H\\XbV_U]TZSURKRD",
  "H\\LDNGOIPLQQR[Rb",
  22,
  "H\\LbN_O]PZQURKRD",
  "H\\XGRGRb",
  22,
  "H\\X_R_RD",
  "H\\LGRGRb",
  22,
  "H\\L_R_RD",
  "H\\XDTHSJRNRb",
  "H\\RDRIQMPOLSPWQYR]Rb",
  "H\\XbT^S\\RXRD",
  22,
  "H\\LDPHQJRNRb",
  "H\\RDRISMTOXSTWSYR]Rb",
  "H\\LbP^Q\\RXRD",
  22,
  "H\\HS\\S",
  "H\\WDSHRKR[Q^Mb",
  "H\\MDQHRKR[S^Wb",
  "E_VbIF\\F",
  "E_VDI`\\`",
  ">fC^CYaYa^",
  ">fCHCMaMaH",
  ">fC^CYaYa^ RaHaMCMCH",
  "IbMTQSS[bB",
  22,
  22,
  "H\\HG\\G",
  "H\\HM\\M",
  "H\\\\YHY",
  "H\\\\_H_",
  "E_UFOFO[",
  "E_U[O[OF",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRbRD",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RZEJE RRERa",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RJaZa RRaRE",
  "E_RK[[I[RK RRbRD",
  "E_RK[[I[RK RZEJE RRERa",
  "E_RK[[I[RK RJaZa RRaRE",
  "E_JSKRNQQRSTVUYTZS RRbRD",
  "E_JSKRNQQRSTVUYTZS RZEJE RRERa",
  "E_JSKRNQQRSTVUYTZS RJaZa RRaRE",
  "E_JaZa RRaRE",
  "E_ZEJE RRERa",
  "E_OFUFU[",
  "E_O[U[UF",
  "D`TFQL RMKJKJ[Z[ZKWK",
  "E_IWN\\NZZZZKTKTTNTNRIW",
  "E_Z[J[ RJVRKZV",
  22,
  "H\\NQNROTQUSUUTVRVQ",
  "H\\NQNROTQUSUUTVRVQ RMKWK",
  "H\\NQNROTQUSUUTVRVQ RW[M[",
  "CaGQGRHTJULUNTOROQ RUQURVTXUZU\\T]R]Q RGK]K",
  "CaGQGRHTJULUNTOROQ RUQURVTXUZU\\T]R]Q R][G[",
  "E_JQJRKTMUOUQTRRRQ RRRSTUUWUYTZRZQ",
  "E_JUZUZP",
  "E_JPJUZUZP",
  "E_RPRU RJPJUZUZP",
  "E_HO\\O RLUXU RRFRO RT[P[",
  "E_HS\\S RJMZMZYJYJM",
  ">fB]C\\FZHYKXPWTWYX\\Y^Za\\b]",
  ">fbIaJ^L\\MYNTOPOKNHMFLCJBI",
  ">fB^B]C[EZOZQYRWSYUZ_Za[b]b^",
  ">fbHbIaK_LULSMROQMOLELCKBIBH",
  ">fB^FY^Yb^",
  ">fbH^MFMBH",
  "E_I[NKVK[[I[",
  "AcRE^L^ZRaFZFLRE RQLSLVMXOYRYTXWVYSZQZNYLWKTKRLONMQL",
  0,
  "E_HXMN\\NWXHX",
  "E_JSZS RJSKNLLNKPLQNSXTZV[XZYXZS",
  "E_LMXY RXMLY RPQRPTQUSTURVPUOSPQ",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "E_KKK[ RL[LK RMKM[ RN[NK ROKO[ RP[PK RQKQ[ RR[RK RSKS[ RT[TK RUKU[ RV[VK RWKW[ RX[XK RYKY[ RJKZKZ[J[JK",
  "E_JKZKZ[J[JK",
  "E_KLMKWKYLZNZXYZW[M[KZJXJNKL",
  "E_JKZKZ[J[JK RPPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV",
  "E_JWZW RJSZS RJOZO RJKZKZ[J[JK",
  "E_NKN[ RRKR[ RVKV[ RJKZKZ[J[JK",
  "E_JWZW RJSZS RJOZO RNKN[ RRKR[ RVKV[ RJKZKZ[J[JK",
  "E_JKZ[ RN[JW RT[JQ RZUPK RZOVK RJKZKZ[J[JK",
  "E_J[ZK RJUTK RJONK RP[ZQ RV[ZW RJKZKZ[J[JK",
  "E_J[ZK RJUTK RJONK RJKZ[ RN[JW RP[ZQ RT[JQ RV[ZW RZUPK RZOVK RJKZKZ[J[JK",
  "E_PPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV",
  "E_OVOPUPUVOV",
  "E_JXTN RJWSN RJVRN RJUQN RJTPN RJSON RJRNN RJQMN RJPLN RJOKN RKXUN RLXVN RMXWN RNXXN ROXYN RPXZN RQXZO RRXZP RSXZQ RTXZR RUXZS RVXZT RWXZU RXXZV RYXZW RJNZNZXJXJN",
  "E_JNZNZXJXJN",
  "E_M[WQ RMZWP RMYWO RMXWN RMWWM RMVWL RMUWK RMTVK RMSUK RMRTK RMQSK RMPRK RMOQK RMNPK RMMOK RMLNK RN[WR RO[WS RP[WT RQ[WU RR[WV RS[WW RT[WX RU[WY RV[WZ RM[MKWKW[M[",
  "E_M[MKWKW[M[",
  "E_NNLP RONKR RPNJT RQNIV RRNHX RSNIX RTNJX RUNKX RVNLX RWNMX RXVVX RXNNX RYTUX RYNOX RZRTX RZNPX R[PSX R[NQX R\\NRX RHXMN\\NWXHX",
  "E_HXMN\\NWXHX",
  "E_JZJ[ RKXK[ RLVL[ RMTM[ RNSN[ ROQO[ RPOP[ RQMQ[ RRKR[ RSMS[ RTOT[ RUQU[ RVSV[ RWTW[ RXVX[ RYXY[ RZ[RLJ[ RZZZ[ RRK[[I[RK",
  "E_RK[[I[RK",
  "E_OUOV RPSPV RQQQV RRORV RSQSV RTSTV RUUUV ROVRPUV RROVVNVRO",
  "E_ROVVNVRO",
  "E_KKK[ RLLLZ RMLMZ RNMNY ROMOY RPNPX RQNQX RRORW RSPSV RTPTV RUQUU RVQVU RWSXS RWRWT RJKYSJ[ RZSJ\\JJZS",
  "E_ZSJ\\JJZS",
  "E_PPPV RQQQU RRQRU RSSUS RSRST ROPUSOV RVSOWOOVS",
  "E_VSOWOOVS",
  "E_KNKX RLNLX RMOMW RNONW ROOOW RPPPV RQPQV RRPRV RSQSU RTQTU RURUT RVRVT RWRWT RXSWS RJNYSJX RZSJYJMZS",
  "E_ZSJYJMZS",
  "E_ZLZK RYNYK RXPXK RWRWK RVSVK RUUUK RTWTK RSYSK RR[RK RQYQK RPWPK ROUOK RNSNK RMRMK RLPLK RKNKK RJKRZZK RJLJK RR[IK[KR[",
  "E_R[IK[KR[",
  "E_UQUP RTSTP RSUSP RRWRP RQUQP RPSPP ROQOP RUPRVOP RRWNPVPRW",
  "E_RWNPVPRW",
  "E_Y[YK RXZXL RWZWL RVYVM RUYUM RTXTN RSXSN RRWRO RQVQP RPVPP ROUOQ RNUNQ RMSLS RMTMR RZ[KSZK RJSZJZ\\JS",
  "E_JSZJZ\\JS",
  "E_TVTP RSUSQ RRURQ RQSOS RQTQR RUVOSUP RNSUOUWNS",
  "E_NSUOUWNS",
  "E_YXYN RXXXN RWWWO RVWVO RUWUO RTVTP RSVSP RRVRP RQUQQ RPUPQ ROTOR RNTNR RMTMR RLSMS RZXKSZN RJSZMZYJS",
  "E_JSZMZYJS",
  "E_JRJT RKUKQ RLPLV RMWMO RNNNX ROYOM RPLPZ RQ[QK RRJR\\ RS[SK RTLTZ RUYUM RVNVX RWWWO RXPXV RYUYQ RZRZT RRJ[SR\\ISRJ",
  "E_RJ[SR\\ISRJ",
  "E_RJ[SR\\ISRJ RPRPT RQUQQ RRPRV RSUSQ RTRTT RRPUSRVOSRP",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RPQPU RQUQQ RRPRV RSUSQ RTQTU RPTRVTT RPRRPTR RPQRPTQUSTURVPUOSPQ",
  "E_RaJSRFZSRa",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_JQKO RKWJU RNLPK RP[NZ RTKVL RVZT[ RYOZQ RZUYW",
  "E_NLNZ RRKR[ RVLVZ RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  47,
  "E_KOKW RLXP[ RLNPK RLMLY RMYMM RNLNZ ROZOL RPKP[ RQ[QK RRKR[ RS[SK RT[XX RTKT[ RTKXN RUZUL RVLVZ RWYWM RXMXY RYWYO RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RKOKW RLYLM RMMMY RNZNL ROLOZ RP[LX RP[PK RLN RQKQ[ RR[P[LYJUJQLMPKRKR[",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RYWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RKOKS RLMLS RMSMM RNLNS ROSOL RPKLN RPKPS RQKQS RRKRS RSKSS RTSTK RXN RULUS RVSVL RWMWS RXMXS RYOYS RJSJQLMPKTKXMZQZSJS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RYWYS RXYXS RWSWY RVZVS RUSUZ RT[XX RT[TS RS[SS RR[RS RQ[QS RPSP[ RLX ROZOS RNSNZ RMYMS RLYLS RKWKS RZSZUXYT[P[LYJUJSZS",
  "E_SSSK RTKTS RTKXN RUSUL RVLVS RWSWM RXMXS RYSYO RZSRSRK RPKTKXMZQZUXYT[P[LYJUJQLMPK",
  "E_QSQ[ RP[PS RP[LX ROSOZ RNZNS RMSMY RLYLS RKSKW RJSRSR[ RT[P[LYJUJQLMPKTKXMZQZUXYT[ RYWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK",
  "E_KOKW RLYLM RMMMY RNZNL ROLOZ RP[LX RP[PK RLN RQKQ[ RR[P[LYJUJQLMPKRKR[",
  "E_YWYO RXMXY RWYWM RVLVZ RUZUL RTKXN RTKT[ RXX RS[SK RRKTKXMZQZUXYT[R[RK",
  "E_FDFb RGbGD RHDHb RIbID RJDJb RKbKD RLbLW RLDLO RMXMb RMNMD RNbNY RNDNM ROZOb ROLOD RPbPZ RPDPL RQZQb RQLQD RRbRZ RRDRL RSZSb RSLSD RTbTZ RTDTL RUZUb RULUD RVbVY RVDVM RWXWb RWNWD RXbXW RXDXO RYbYD RZDZb R[b[D R\\D\\b R]b]D R^D^b R_bEbED_D_b RKTKRLONMQLSLVMXOYRYTXWVYSZQZNYLWKT",
  "E_FRFD RGNIJ RGDGN RHLHD RIDIK RJJJD RJJMG RKDKI RLHLD RMHQF RMDMH RNGND ROPOS RODOG RPSPP RPGPD RQPQS RQDQG RRSRO RRGRD RSPSS RSFWH RSDSG RTSTP RTGTD RUPUS RUDUG RVGVD RWGZJ RWDWH RXHXD RYDYI RZJZD R[J]N R[D[K R\\L\\D R]D]N R^R^D ROQROUQ RNSOPROUPVSNS RFSFRGNIKJJMHQGSGWHZJ[K]N^R^S_S_DEDESFS R^T^b R]X[\\ R]b]X R\\Z\\b R[b[[ RZ\\Zb RZ\\W_ RYbY] RX^Xb RW^S` RWbW^ RV_Vb RUVUS RUbU_ RTSTV RT_Tb RSVSS RSbS_ RRSRW RR_Rb RQVQS RQ`M^ RQbQ_ RPSPV RP_Pb ROVOS RObO_ RN_Nb RM_J\\ RMbM^ RL^Lb RKbK] RJ\\Jb RI\\GX RIbI[ RHZHb RGbGX RFTFb RUURWOU RVSUVRWOVNSVS R^S^T]X[[Z\\W^S_Q_M^J\\I[GXFTFSESEb_b_S^S",
  "E_FRFD RGNIJ RGDGN RHLHD RIDIK RJJJD RJJMG RKDKI RLHLD RMHQF RMDMH RNGND ROPOS RODOG RPSPP RPGPD RQPQS RQDQG RRSRO RRGRD RSPSS RSFWH RSDSG RTSTP RTGTD RUPUS RUDUG RVGVD RWGZJ RWDWH RXHXD RYDYI RZJZD R[J]N R[D[K R\\L\\D R]D]N R^R^D ROQROUQ RNSOPROUPVSNS RFSFRGNIKJJMHQGSGWHZJ[K]N^R^S_S_DEDESFS",
  "E_^T^b R]X[\\ R]b]X R\\Z\\b R[b[[ RZ\\Zb RZ\\W_ RYbY] RX^Xb RW^S` RWbW^ RV_Vb RUVUS RUbU_ RTSTV RT_Tb RSVSS RSbS_ RRSRW RR_Rb RQVQS RQ`M^ RQbQ_ RPSPV RP_Pb ROVOS RObO_ RN_Nb RM_J\\ RMbM^ RL^Lb RKbK] RJ\\Jb RI\\GX RIbI[ RHZHb RGbGX RFTFb RUURWOU RVSUVRWOVNSVS R^S^T]X[[Z\\W^S_Q_M^J\\I[GXFTFSESEb_b_S^S",
  "E_JSJQLMPKRK",
  "E_ZSZQXMTKRK",
  "E_ZSZUXYT[R[",
  "E_JSJULYP[R[",
  "E_JSJQLMPKTKXMZQZS",
  "E_ZSZUXYT[P[LYJUJS",
  "E_KZK[ RLYL[ RMXM[ RNWN[ ROVO[ RPUP[ RQTQ[ RRSR[ RSRS[ RTQT[ RUPU[ RVOV[ RWNW[ RXMX[ RYLY[ RZ[ZKJ[Z[",
  "E_YZY[ RXYX[ RWXW[ RVWV[ RUVU[ RTUT[ RSTS[ RRSR[ RQRQ[ RPQP[ ROPO[ RNON[ RMNM[ RLML[ RKLK[ RJ[JKZ[J[",
  "E_YLYK RXMXK RWNWK RVOVK RUPUK RTQTK RSRSK RRSRK RQTQK RPUPK ROVOK RNWNK RMXMK RLYLK RKZKK RJKJ[ZKJK",
  "E_KLKK RLMLK RMNMK RNONK ROPOK RPQPK RQRQK RRSRK RSTSK RTUTK RUVUK RVWVK RWXWK RXYXK RYZYK RZKZ[JKZK",
  "E_PQRPTQUSTURVPUOSPQ",
  "E_JKZKZ[J[JK RK[KK RLKL[ RM[MK RNKN[ RO[OK RPKP[ RQ[QK RJ[JKRKR[J[",
  "E_JKZKZ[J[JK RYKY[ RX[XK RWKW[ RV[VK RUKU[ RT[TK RSKS[ RZKZ[R[RKZK",
  "E_JKZKZ[J[JK RYLYK RXMXK RWNWK RVOVK RUPUK RTQTK RSRSK RRSRK RQTQK RPUPK ROVOK RNWNK RMXMK RLYLK RKZKK RJKJ[ZKJK",
  "E_JKZKZ[J[JK RKZK[ RLYL[ RMXM[ RNWN[ ROVO[ RPUP[ RQTQ[ RRSR[ RSRS[ RTQT[ RUPU[ RVOV[ RWNW[ RXMX[ RYLY[ RZ[ZKJ[Z[",
  "E_JKZKZ[J[JK RR[RK",
  "E_RK[[I[RK RRUQVRWSVRURW",
  "E_J[RL RJZJ[ RKXK[ RLVL[ RMTM[ RNSN[ ROQO[ RPOP[ RQMQ[ RRKR[ RRK[[I[RK",
  "E_Z[RL RZZZ[ RYXY[ RXVX[ RWTW[ RVSV[ RUQU[ RTOT[ RSMS[ RRKR[ RRKI[[[RK",
  "C`OFTFXHZJ\\N\\SZWXYT[O[KYIWGSGNIJKHOF",
  "E_JKZKZ[J[JK RRKRSJS",
  "E_JKZKZ[J[JK RR[RSJS",
  "E_JKZKZ[J[JK RR[RSZS",
  "E_JKZKZ[J[JK RRKRSZS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRKRSJS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RR[RSJS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RR[RSZS",
  "E_PKTKXMZQZUXYT[P[LYJUJQLMPK RRKRSZS",
  "E_JKJ[ZKJK",
  "E_ZKZ[JKZK",
  "E_J[JKZ[J[",
  "E_JKZKZ[J[JK",
  "E_KKK[ RL[LK RMKM[ RN[NK ROKO[ RP[PK RQKQ[ RR[RK RSKS[ RT[TK RUKU[ RV[VK RWKW[ RX[XK RYKY[ RJKZKZ[J[JK",
  "E_OVOPUPUVOV",
  "E_PPPV RQVQP RRPRV RSVSP RTPTV ROVOPUPUVOV",
  "E_Z[ZKJ[Z[",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  48,
  "PfUUYZ",
  "PfWTYT[V[XYZWZUXUVWT",
  "PfZKXS R^K\\S",
  "PfYFUISMSQUUZXZUXTXRZQ[R[L]N^L^FaIcMcQaU\\X",
  "PfZJYMVQ RYM`M\\T RZR]V",
  "PfbHTWWK^R",
  "PfWG_GcMcS_XWXSSSMWG",
  "PfaD[OaZ",
  "PfUD[OUZ",
  "PfaD[OaZ R^DXO^Z",
  "PfUD[OUZ RXD^OXZ",
  "PfbD^D^R",
  "PfT[X[XO",
  "PfbDbH^H^PZPZDbD",
  "PfT[TWYWYO]O][T[",
  "Pf^DbDaIaOaUbZ^Z^D",
  "PfTDXDX[T[UVUITD",
  "PfUIaI RUNaN R[N[Y",
  "PfUJaJaNUNUJ RURaRaVUVUR",
  "PfbD_H_VbZ",
  "PfTDWHWVTZ",
  "Pf\\DbDaIaOaUbZ\\Z\\D",
  "PfTDZDZ[T[UVUITD",
  "PfbD]F]XbZ R`E`Y",
  "PfTDYFYXTZ RVEVY",
  "PfbD]D][b[ R`D`[",
  "PfTDYDY[T[ RVDV[",
  "PfTOXL^RbO",
  "Pf^EbK RYE]K",
  "PfWDTJ R[DXJ",
  "PfXTTY R]TYY",
  "PfWI_I RWL_L R[L[S RWSXU^U_S RVNXNYPXRVRUPVN R^N`NaP`R^R]P^N RTNRNRSTSVX`XbSdSdNbN",
  "Pf[F[Y",
  "PfXJXU R]F]X",
  "PfVHVX R[J[V R`G`X",
  "PfaK^SUZ RWOaV",
  "PfZHVN]O_R_U]XYXWTWR_M",
  "Pf[M[P RTPbP",
  "Pf[J[M RTMbM RTQbQ",
  "Pf[I[L RTLbL RTPbP RTTbT",
  "PfXLWOTR RWObO R`O_VV[ RVQ[S_Y",
  "PfT\\W\\Y^YaWcTcRaR^T\\",
  "PfTAWAYCYFWHTHRFRCTA",
  "Pf_AbAdCdFbH_H]F]C_A",
  "Pf_\\b\\d^dabc_c]a]^_\\",
  "PfgOjOlQlTjVgVeTeQgO",
  "PfgKjKlMlPjRgRePeMgK RgTjTlVlYj[g[eYeVgT",
  "PfSQVMYQ\\M_QbM",
  "Pf]DWP]Z",
  "Pf]I`L R`HcK R]DWP]Z",
  "Pf_GWY",
  "Pf_MaP RbMdP R_GWY",
  "PfVH_X",
  "PfWG_GcMcS_XWXSSSMWG RWK_K RWO_O R[O[U",
  "PfUFZY R[FUY R\\FaY RaF\\Y",
  "PfULaL R[E[Y",
  "PfTLbL RXEXY R^E^Y",
  "PfTNbN RWGWVUY R[I[V R_H_Y",
  "PfXI^N\\O RXP^U",
  "PfUJaJaWUWUJ RaJUW",
  "PfTLWHZM]JbW",
  "PfTIVI RXIZI R\\I^I R`IbI RbK RbMbO RbQbS RbUbW R`W R^W\\W RZWXW RVWTWTU RTSTQ RTOTM RTKTI RWM[K]N`L RWQ_Q RWT_T R\\PYV",
  "PfUHaHaYUYUH R_JWW RWJ_W",
  48,
  "PfVO]O RYLYTZY R\\QXYWYVXVUZR^R`U`W]Z",
  "PfTI^H RYEXPZY R]LZUVZTUXP^NaRaX][",
  "PfVPVWX[ZX R]Q`W",
  "Pf^J`NaS RTHTOUTWZZT",
  "PfZJ]L RWO]N_Q^VZ[",
  "PfXD]F RUM\\J_M_S]XXZ",
  "PfZN]P RXR^RX[ R[W]W][`[",
  "PfYE]H RWL^KV[ RYU]R]Z`Z",
  "PfUQ[Q RXNX[UYUWZT^T`W`Y[[ R]O`R",
  "PfTJ[I RWEWYTWTSZP^QaS`X[Y R^HaL",
  "PfSLZK\\OZZWY RXDTZ R]IaQ",
  "PfSLZK\\OZZWX RXDTY R]H`Q R`JbM RcIeL",
  "PfVI^G RUNaK RYD]SZS RVTVWXY\\Z",
  "PfVI^G RUNaK RYD]SZS RVTVWXY\\Z R_DaG RbCdF",
  "Pf]EXO]Z",
  "Pf]EXO]Z R_IaL RbHdK",
  "PfZLaL RVDUKURUVVYXS R^E_M_S^W\\Z",
  "PfZLaL RVDUKURUVVYXS R^E_M_S^W\\Z RaEcH RdDfG",
  "PfWG^G[J RWPUUWZ`Z",
  "PfWG^G[J RWPUUWZ`Z R`DbG RcCeF",
  "PfTK`I RYE_R[Q RVRVVXY]Z",
  "PfTK`I RYE_R[Q RVRVVXY]Z R_DaG RbCdF",
  "PfWEWVXYZ[][`YaU",
  "PfWEWVXYZ[][`YaU R\\L^O R_KaN",
  "PfSJaJ R]E]S\\WX[ R\\OZMYMWPWRYSZS\\Q",
  "PfSJaJ R]E]S\\WX[ R\\OZMYMWPWRYSZS\\Q R`DbG RcCeF",
  "PfTMbL R^E^S\\R RWGWZ`Z",
  "PfTMbL R^E^S\\R RWGWZ`Z R`EbH RcDeG",
  "PfWF_EXM RTNaL R_M[PYRYU[X^Z",
  "PfWF_EXM RTNaL R_M[PYRYU[X^Z RaDcG RdCfF",
  "PfTI[I RYDTY RZN`N RYSZW\\YaY",
  "PfTI[I RYDTY RZN`N RYT[YaY R_GaJ RbFdI",
  "PfTI^I RXDUSYO]O_R_V\\YX[",
  "PfTI^I RXDUSYO]O_R_V\\YX[ R^E`H RaDcG",
  "PfTO]M`NaR_UYX",
  "PfSL]I`JaMaP`S]VWX",
  "PfSL]I`JaMaP`S]VWX R`EbH RcDeG",
  "PfTIaG R_H[KYPYV[Y^Z",
  "PfTIaG R_H[KYPYV[Y^Z R`CbF RcBeE",
  "Pf_KWQUSUWWZ_Z RWDXIZN",
  "Pf_KWQUSUWWZ_Z RWDXIZN R_GaJ RbFdI",
  "PfTIZI RXDTU R_HbL R]L]X[YXXXT[SaX",
  "PfZHaH RUDTLTRUYWR RZSZW[XaX",
  "PfUGXW R[EXTUXSUTQWK]JaNaV^Z\\ZZW\\TbY",
  "PfWEWZ RTJWJWK RSVZK^IaJbNaU^Y\\YZXZU]TbX",
  "Pf[GWWTTTLVH[F_GbLbRaV\\Y",
  "PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR",
  "PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR R`EbH RcDeG",
  "PfYIaI R^E^YYXYT\\SaW RUETKTQUYVR RbDcDdEdFcGbGaFaEbD",
  "PfSKYGUNUTVXXZ[Y\\W]S^M]GbO",
  "PfSKYGUNUTVXXZ[Y\\W]S^M]GbO R`EbH RcDeG",
  "PfSKYGUNUTVXXZ[Y\\W]S^M]GbO RbEcEdFdGcHbHaGaFbE",
  "PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW",
  "PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW R_DaG RbCdF",
  "PfYE]H RZK[Q]U\\YYYWW RVPTX R_QaW R`DaDbEbFaG`G_F_E`D",
  "PfTRYKbS",
  "Pf^J`M RaIcL RTRYKbS",
  "Pf_I`IaJaK`L_L^K^J_I RTRYKbS",
  "PfYF`F RYL`L R^F^ZZYZW\\UbX RUETKTQUZWS",
  "PfYF`F RYL`L R^F^[ZYZW\\UbX RUETKTQUZWS RaCcF RdBfE",
  "PfYF`F RYL`L R^F^[ZYZW\\UbX RUETKTQUZWS RcCdCeDeEdFcFbEbDcC",
  "PfTH`H RVM^M R[D[YXYUWVUZT`W",
  "PfVG\\GZNVXTUTRWP[PbT R_K_Q^U[Y",
  "PfSHYH RWEVVXZ^Z_V_Q RVRUTTTSRSPTNUNVP R]IaN",
  "PfUHYX R[FYVVZSVSRWM[K_MbRaW]Z",
  "PfYDXVYZ[[^[`ZaV`P RTI\\I RUO\\O",
  "PfUR]N`O`Q_S\\T RVL[[ RYK[M",
  "PfSO_KaLbP_S\\S RUG[[ RYE\\H",
  "PfTLTVWP\\MaQaV]YYV R]J]R[[",
  "PfULUXXP[M_MbPbU_W\\WZU R]J]Y[[",
  "Pf[N[ZVYVVYU`X R[Q_Q",
  "Pf[E[[WZUXUVWTaY R[K`J",
  "PfYE]H RXIVUYQ]P`S_XY[",
  "Pf^E^R]VYZ RWEVJVNWQYN",
  "PfWF_EVS[O`OaRaW][Y[XWZU^Y",
  "PfWEWZ RTJXIWJ RSV\\I_I`L_S_YbU",
  "PfXG^FWT[O`OaRaW^YZZ",
  "PfWIWZ RULXLWN RUU[M^MaNaT_W[Y",
  "PfWEWZ RTKXJWL RSVYN[K_KaMbQ`U[Y",
  "PfWG]FWZUUVQZM^NaQaX][ZY[V_X",
  "PfXE^EVN R\\K`M`QZTWRXP[QTY RVWXW[Z R]W_WaY",
  "PfUH^H RZDUSYM[O\\U R`NWUWXZ[_[",
  "Pf[EU[ZQ\\Q^[_[bV",
  "PfXD]F RUM\\J_M_S]XXZ R`FbI RcEeH",
  "PfUO\\N]P\\YYW RYJUY R^LaQ",
  "PfYP`O RUKTQTUVZWW R]L]V\\X[[",
  48,
  48,
  "Pf^E`H RaDcG",
  "PfaDbDcEcFbGaG`F`EaD",
  "PfSEUH RVDXG",
  "PfTDUDVEVFUGTGSFSETD",
  "PfYI`P\\R",
  "PfYI`P\\R R^G`J RaFcI",
  "PfZJ`J R[EUW RXP^P`S_X\\[YZ",
  "PfTLbL RTTbT",
  "PfVK`K_N]Q R[N[RZUXX",
  "PfTGbGaI_L\\N RZJZQZSYVW[",
  "Pf[P[Z R^J\\NYQVS",
  "Pf[L[[ R`E^H[LWOTQ",
  "PfZHZL RVOVL_L_O^S]U[WXY",
  "Pf[D[H RUOUHaH`N_Q]U[XWZ",
  "PfWL_L R[L[W RVW`W",
  "PfUIaI RTWbW R[I[W",
  "PfWO`O R]K]Z[Y R\\O[RYUVX",
  "PfUKbK R^D^Z[Y R]K[PXSTW",
  "PfUJaJ`Y]W RZCZJZOYSWVUY",
  "PfUJaJ`Y]W RZCZJZOYSWVUY R_EaH RaCcF",
  "PfVL^J RUSaP RYD]Z",
  "Pf]E_G R`DbF RVL^J RUSaP RYD]Z",
  "PfZDYIWLUP RZH`H`L_P]T[WWZ",
  "PfZDYIWLUO RZGaG`L_P]T[WWZ R`DbF RcCeE",
  "PfWKbK RXDWHUMTP R]K]P\\SZVWZ",
  "PfWKbK RXDWHUMTQ R]K]P\\SZVWZ R^G`I RaFcH",
  "PfUIaIaWUW",
  "Pf`FbH RcEeG RUIaIaWUW",
  "PfTKbK RWEWR R_D_K_O^S]U[XYZ",
  "PfTKbK RWEWR R_D_K_O^S]U[XYZ RaDbF RdCeE",
  "PfWFZI RULXO RUYZW]U_SbK",
  "PfWFZI RULXO RUYZW]U_SbK R_GaI RbFdH",
  "PfUF^F]L[PYSWVTY R[Q]T`Y",
  "PfUF^F]L[OYSWVTY R[Q]T`Y R`EbG RcDeF",
  "PfULbJ^R RYEYXaX",
  "Pf_EaG RbDdF RULbJ^R RYDYXaX",
  "PfUFWL R`F`L_P^S\\VWY",
  "PfaG`L_P^T\\WXZ RaDcF RdCfE RUGWM",
  "PfXL]R RYDXHWLUP RYH`H_L^P]T[WXZ",
  "PfXL]R RYDXHWLUP RYH`H_L^P]T[WXZ R`EbG RcDeF",
  "PfTNbN R_E]FZGVH R\\G\\M[QZUYWVZ",
  "PfTNbN R_E]FZGVH R\\G\\M[QZUYWWZ R`DbF RcCeE",
  "PfULWQ RZK[P R`L`Q_T\\WYY",
  "PfUGWN RYF[L R`G`M_Q]U[WXY",
  "PfUGWN RYF[L R`G`M_Q]U[WXY RaEcG RdDfF",
  "PfWG_G RTMbM R[M[RYVVZ",
  "Pf`EbG RcDeF RWG_G RTMbM R[M[RYVVZ",
  "Pf[D[Z R[MaR",
  "Pf_KaM RbJdL R[D[Z R[MaR",
  "PfTLbL R[D[K[QZTXWVZ",
  "PfUKaK RSWcW",
  "PfXM_W RWF`F_L^P\\UZWVZ",
  "PfYD]G R[P[[ R]QaU RVH`H^L\\OYRTU",
  "Pf_F^L]QZUVY",
  "Pf^JbV RYJXOVSTV",
  "Pf^JbV RYJXOVSTV R_HaJ RbGdI",
  "Pf^JbV RYJXOVSTV R`GaGbHbIaJ`J_I_H`G",
  "PfUFUYaY R`J\\MYNVO",
  "PfUFUYaY R`J\\MYNVO R`HbJ RcGeI",
  "PfUFUYaY R`J\\MYNVO RaFbFcGcHbIaI`H`GaF",
  "PfUH`H`M_R]UZWVY",
  "PfUH`H`M_R]UZWVY RaFcH RdEfG",
  "PfUH`H`M_R]UZWVY RbEcEdFdGcHbHaGaFbE",
  "PfTRYJbV",
  "Pf]K_M R`JbL RTRYJbV",
  "Pf_K`KaLaM`N_N^M^L_K RTRYJbV",
  "PfUKaK R[E[ZXY R^OaW RWOVRUTTW",
  "PfUKaK R[E[ZXY R^OaW RWOVRUTTW R`GbI RcFeH",
  "PfUKaK R[E[ZXY R^OaW RWOVRUTTW RaFbFcGcHbIaI`H`GaF",
  "PfTJaJ_N]Q[S RWPZS[U]X",
  "PfWFaJ RWM_P RUT`Y",
  "Pf[FUY_W R]PaZ",
  "Pf`E_J]OZSXUTX RXKZM]Q`U",
  "PfVG`G RSOcO RZGZY`Y",
  "PfUOaL^R RXI[Z",
  "PfXE[Z RTMaI`L_O^Q",
  "PfXL^L^V RVVaV",
  "PfVI`I_W RSWcW",
  "PfWL_L_XWX RWR_R",
  "PfUHaHaXUX RUPaP",
  "PfVG`G RTLaLaQ_T\\WXZ",
  "PfXEXP R_E_M_Q]U\\WYZ",
  "PfWGWOVSUVTY R[E[Y]W_TaP",
  "PfWEWX[W^U`SbO",
  "PfUHUV RUHaHaVUV",
  "PfVPVJ`J_P]UYZ",
  "PfUGUN RaG`M_Q^U\\XYZ RUGaG",
  "PfWJbJ RWJWS RSScS R]D]Z",
  "PfVIaI]P R[L[W RSWcW",
  "PfVM`M RUF`F`L`O_S]VZXVZ",
  "PfUHYL RUXZW]T_QaJ",
  "Pf[D[H RUOUHaH`N_Q]U[XWZ RaEcG RdDfF",
  "PfWM_M^Y\\X R[IZNYSWX",
  "PfYMaM RYIXMWPUS R_M^Q]T\\WZZ",
  "PfaEcG RdDfF RUGUN RaG`N`Q^U\\WYZ RUGaG",
  "Pf`GbI RcFeH RWJbJ RWJWS RSScS R]D]Z",
  "Pf`FbH RcEeG RVIaI]P R[L[W RSWcW",
  "PfVM`M RUF`F`L`O_S]VZXVZ RaEcG RdDfF",
  "PfZP\\P]Q]S\\TZTYSYQZP",
  "PfSPcP",
  "PfWK^U",
  "Pf\\M^O R_KaM RWK^U",
  "PfVF`F`Y",
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  23,
  "PoROlO",
  "PoRFlF RX[`[ R`F`[",
  "PoRFlF R^[e[ RZFVQ RWNiNfZ",
  "Po\\D\\[j[jW RSOkK",
  "PoR[l[ R_D_[",
  "PoRFlF R_F_[",
  "PoRGlG R[UU[ R^LYW R_G\\T",
  "PoRFlF R\\F[PXVT[ R\\NiMiTg[`[",
  "PoRIlI RWLZS^WcYj[ RbDbLaT\\XYZS[",
  "PoTFjF RVPhP RR[l[",
  "Po^MjM RR[l[ R^D^[",
  "PoRElE R^E^[ R^KjQ",
  "PoSGlG RfFf[ RXVR[ RYFYPXV",
  "PoRElE R`H`[ RaGXPRS RaLiOlS",
  "PoYHiH RRTlT R\\[d[ RYCWNgNeZ",
  "PoRElE RURjR Rb[h[ RUJUU R_E_R R_KkKjRi[",
  "PoRElE R_KjK Rb[i[ R_E_P RUQlQi[ RVITR",
  "PoROlO RR[l[ R[FZNX[ RUFgFf[",
  "PoaXhX RR[l[ R`PcT RXUSW R^NVV RVK`P RaH^O RTFkFkNiX",
  "PoTGjG RRLlL ReS`X RYQhQbW R^C\\JXQ RYWeZ",
  "PoWLgL RWTgT RR[l[ RWEW[ RWEgEg[",
  "PoSFkF RR[l[ R`I`Y RcMfOkS RaF`IXQRS",
  "PoRJlJ R_RgR RWYkY RWDW[ R_C_T RgDgT",
  "PoRKlK RWYgY RWCW[ R_C_Y RgCg[",
  "PoWNkN RR[l[ RWGW[ RdNd[ RhEWG",
  "PoRElE Re[j[ RSKS[ RSKkKk[ R_F^PZUVV R^NgV",
  "PoR[l[ R[D[[ RcDc[ RTKXS RjKfS",
  "PoR[l[ RhTlX RaT\\X RYL\\O^T ReMiV RXOTW RcN_W RdHgS RYEWS RdDbR",
  "PoRGlG RUPjP R[[`[ R`K`[ ReSlY RYKUO RXTRZ R\\CYL",
  "Po`VkV RTV]V RR[l[ RkJgN RbJ`NhN`V R]J\\N RVKTO[OTV RZDVM RfDbL",
  "PoYX_X RS[k[ R_J_X RVEgEdG_J RRL[LXQSV RjJgMbN R`JbOgTlV",
  "PoSEkE RUJiJ RRPlP RZZjZ RXZhZ RRZeZ R_E_P ReTl[ R[PWZ"
];

// src/kicad_stroke_font.ts
var SPACE_CHAR_CODE = " ".charCodeAt(0);
var QMARK_GLYPH_INDEX = "?".charCodeAt(0) - SPACE_CHAR_CODE;
var PRELOAD_GLYPH_COUNT = 256;
var REF_CHAR_CODE = "R".charCodeAt(0);
var FONT_SCALE = 1 / 21;
var FONT_OFFSET = -10;
var INTERLINE_PITCH = 1.62;
var glyphCache = /* @__PURE__ */ new Map();
var layoutCache = /* @__PURE__ */ new Map();
var hasPreloadedGlyphs = false;
function decodeCoord(c) {
  return c.charCodeAt(0) - REF_CHAR_CODE;
}
function decodeGlyph(encoded) {
  const left = decodeCoord(encoded[0] ?? "R") * FONT_SCALE;
  const right = decodeCoord(encoded[1] ?? "R") * FONT_SCALE;
  const strokes = [];
  let currentStroke = null;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  for (let i = 2; i + 1 < encoded.length; i += 2) {
    const xChar = encoded[i];
    const yChar = encoded[i + 1];
    if (xChar === " " && yChar === "R") {
      currentStroke = null;
      continue;
    }
    const x = decodeCoord(xChar) * FONT_SCALE - left;
    const y = (decodeCoord(yChar) + FONT_OFFSET) * FONT_SCALE;
    const point = new Vec2(x, y);
    if (currentStroke == null) {
      currentStroke = [];
      strokes.push(currentStroke);
    }
    currentStroke.push(point);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
  }
  if (!Number.isFinite(minY)) {
    minY = 0;
    maxY = 0;
  }
  return {
    advance: right - left,
    strokes,
    minY,
    maxY
  };
}
function loadGlyph(glyphIndex) {
  const data = glyph_data[glyphIndex];
  if (data === void 0) {
    return null;
  }
  let encoded;
  if (typeof data === "string") {
    encoded = data;
  } else if (typeof data === "number") {
    encoded = shared_glyphs[data];
  }
  if (encoded === void 0) {
    return null;
  }
  const glyph = decodeGlyph(encoded);
  glyphCache.set(glyphIndex, glyph);
  glyph_data[glyphIndex] = void 0;
  return glyph;
}
function preloadGlyphs() {
  if (hasPreloadedGlyphs) {
    return;
  }
  const count = Math.min(PRELOAD_GLYPH_COUNT, glyph_data.length);
  for (let i = 0; i < count; i += 1) {
    if (!glyphCache.has(i)) {
      loadGlyph(i);
    }
  }
  hasPreloadedGlyphs = true;
}
function getGlyphByIndex(glyphIndex) {
  preloadGlyphs();
  if (glyphIndex < 0 || glyphIndex >= glyph_data.length) {
    return getGlyphByIndex(QMARK_GLYPH_INDEX);
  }
  const cached = glyphCache.get(glyphIndex);
  if (cached) {
    return cached;
  }
  const loaded = loadGlyph(glyphIndex);
  if (loaded) {
    return loaded;
  }
  if (glyphIndex !== QMARK_GLYPH_INDEX) {
    return getGlyphByIndex(QMARK_GLYPH_INDEX);
  }
  return decodeGlyph("JZ");
}
function getGlyphForChar(ch) {
  const glyphIndex = ch.charCodeAt(0) - SPACE_CHAR_CODE;
  return getGlyphByIndex(glyphIndex);
}
function layoutKicadStrokeText(text, charWidth, charHeight) {
  const cacheKey = `${text}|${charWidth}|${charHeight}`;
  const cached = layoutCache.get(cacheKey);
  if (cached) {
    return cached;
  }
  const strokes = [];
  let cursorX = 0;
  let cursorY = 0;
  let minX = Number.POSITIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let lineMaxX = 0;
  const linePitch = charHeight * INTERLINE_PITCH;
  for (const ch of text) {
    if (ch === "\n") {
      lineMaxX = Math.max(lineMaxX, cursorX);
      cursorX = 0;
      cursorY += linePitch;
      continue;
    }
    if (ch === "	") {
      const tab = charWidth * 3.28;
      const rem = cursorX % tab;
      cursorX += tab - rem;
      lineMaxX = Math.max(lineMaxX, cursorX);
      continue;
    }
    if (ch === " ") {
      cursorX += charWidth * 0.6;
      lineMaxX = Math.max(lineMaxX, cursorX);
      continue;
    }
    const glyph = getGlyphForChar(ch);
    for (const stroke of glyph.strokes) {
      if (stroke.length === 0) {
        continue;
      }
      const transformed = [];
      for (const p of stroke) {
        const tx = cursorX + p.x * charWidth;
        const ty = cursorY + p.y * charHeight;
        transformed.push(new Vec2(tx, ty));
        minX = Math.min(minX, tx);
        minY = Math.min(minY, ty);
        maxX = Math.max(maxX, tx);
        maxY = Math.max(maxY, ty);
      }
      strokes.push(transformed);
    }
    minY = Math.min(minY, cursorY + glyph.minY * charHeight);
    maxY = Math.max(maxY, cursorY + glyph.maxY * charHeight);
    cursorX += glyph.advance * charWidth;
    lineMaxX = Math.max(lineMaxX, cursorX);
  }
  if (!Number.isFinite(minX)) {
    minX = 0;
    maxX = lineMaxX;
    minY = 0;
    maxY = charHeight;
  } else {
    maxX = Math.max(maxX, lineMaxX);
  }
  const layout = { strokes, advance: lineMaxX, minX, minY, maxX, maxY };
  layoutCache.set(cacheKey, layout);
  return layout;
}
function layoutKicadStrokeLine(text, charWidth, charHeight) {
  return layoutKicadStrokeText(text, charWidth, charHeight);
}

// src/painter.ts
var DEG_TO_RAD2 = Math.PI / 180;
var HOLE_SEGMENTS = 36;
var SELECTION_STROKE_WIDTH = 0.12;
var GROUP_SELECTION_STROKE_WIDTH = 0.1;
var HOVER_SELECTION_STROKE_WIDTH = 0.08;
var SELECTION_GROW = 0.2;
var GROUP_SELECTION_GROW = 0.16;
var HOVER_SELECTION_GROW = 0.12;
function footprintOwnerId(footprint, fallbackIndex) {
  return footprint.uuid ? `fp:${footprint.uuid}` : `fp_idx:${fallbackIndex}`;
}
function trackOwnerId(track) {
  return track.uuid ? `trk:${track.uuid}` : null;
}
function viaOwnerId(via) {
  return via.uuid ? `via:${via.uuid}` : null;
}
function drawingOwnerId(drawing) {
  return drawing.uuid ? `drw:${drawing.uuid}` : null;
}
function textOwnerId(text) {
  return text.uuid ? `txt:${text.uuid}` : null;
}
function zoneOwnerId(zone) {
  return zone.uuid ? `zon:${zone.uuid}` : null;
}
function buildDragOwnerIds(model, dragged) {
  const owners = /* @__PURE__ */ new Set();
  const footprintIndices = dragged.footprintIndices ?? /* @__PURE__ */ new Set();
  for (const index of footprintIndices) {
    const footprint = model.footprints[index];
    if (!footprint)
      continue;
    owners.add(footprintOwnerId(footprint, index));
  }
  const trackUuids = dragged.trackUuids ?? /* @__PURE__ */ new Set();
  for (const uuid of trackUuids) {
    owners.add(`trk:${uuid}`);
  }
  const viaUuids = dragged.viaUuids ?? /* @__PURE__ */ new Set();
  for (const uuid of viaUuids) {
    owners.add(`via:${uuid}`);
  }
  const drawingUuids = dragged.drawingUuids ?? /* @__PURE__ */ new Set();
  for (const uuid of drawingUuids) {
    owners.add(`drw:${uuid}`);
  }
  const textUuids = dragged.textUuids ?? /* @__PURE__ */ new Set();
  for (const uuid of textUuids) {
    owners.add(`txt:${uuid}`);
  }
  const zoneUuids = dragged.zoneUuids ?? /* @__PURE__ */ new Set();
  for (const uuid of zoneUuids) {
    owners.add(`zon:${uuid}`);
  }
  return owners;
}
function p2v(p) {
  return new Vec2(p.x, p.y);
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
function circleToPoints(cx, cy, radius, segments = HOLE_SEGMENTS) {
  const points = [];
  if (radius <= 0)
    return points;
  for (let i = 0; i <= segments; i++) {
    const angle = i / segments * 2 * Math.PI;
    points.push(new Vec2(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)));
  }
  return points;
}
function drawFootprintSelectionBox(layer, fp, strokeWidth, strokeAlpha, grow, fillAlpha = 0) {
  const bbox = footprintBBox(fp).grow(grow);
  if (bbox.w <= 0 || bbox.h <= 0)
    return;
  const corners = [
    new Vec2(bbox.x, bbox.y),
    new Vec2(bbox.x2, bbox.y),
    new Vec2(bbox.x2, bbox.y2),
    new Vec2(bbox.x, bbox.y2),
    new Vec2(bbox.x, bbox.y)
  ];
  if (fillAlpha > 0) {
    layer.geometry.add_polygon(corners.slice(0, 4), 1, 1, 1, fillAlpha);
  }
  layer.geometry.add_polyline(corners, strokeWidth, 1, 1, 1, strokeAlpha);
}
function buildLayerMap(model) {
  const layerById = /* @__PURE__ */ new Map();
  for (const layer of model.layers) {
    layerById.set(layer.id, layer);
  }
  return layerById;
}
function layerPaintOrder(layerName, layerById) {
  return layerById.get(layerName)?.paint_order ?? Number.MAX_SAFE_INTEGER;
}
function layerKind(layerName, layerById) {
  return (layerById.get(layerName)?.kind ?? "").toLowerCase();
}
function zoneRenderLayerName(layerName) {
  return `zone:${layerName}`;
}
function isTextHidden(hidden) {
  return hidden.has("__type:text") || hidden.has("__type:text_shapes") || hidden.has("__type:other");
}
function isShapesHidden(hidden) {
  return hidden.has("__type:shapes") || hidden.has("__type:text_shapes") || hidden.has("__type:other");
}
function paintObjects(renderer, layerById, modelDrawings, modelTexts, modelTracks, modelVias, footprints, hidden, footprintOwnerByRef, tint) {
  const showText = !isTextHidden(hidden);
  const showShapes = !isShapesHidden(hidden);
  const showTracks = !hidden.has("__type:tracks");
  const showPads = !hidden.has("__type:pads");
  const drawingsByLayer = /* @__PURE__ */ new Map();
  const tracksByLayer = /* @__PURE__ */ new Map();
  const viasByLayer = /* @__PURE__ */ new Map();
  const drillViasByLayer = /* @__PURE__ */ new Map();
  const padsByLayer = /* @__PURE__ */ new Map();
  const padHolesByLayer = /* @__PURE__ */ new Map();
  const textsByLayer = /* @__PURE__ */ new Map();
  const addDrawing = (layer, at, d, ownerId) => {
    let arr = drawingsByLayer.get(layer);
    if (!arr) {
      arr = [];
      drawingsByLayer.set(layer, arr);
    }
    arr.push({ at, d, ownerId });
  };
  const worldAt = { x: 0, y: 0, r: 0 };
  if (showShapes) {
    for (const d of modelDrawings) {
      if (!d.layer || hidden.has(d.layer))
        continue;
      addDrawing(d.layer, worldAt, d, drawingOwnerId(d));
    }
  }
  if (showText) {
    for (const t of modelTexts) {
      if (!t.layer || hidden.has(t.layer))
        continue;
      let arr = textsByLayer.get(t.layer);
      if (!arr) {
        arr = [];
        textsByLayer.set(t.layer, arr);
      }
      arr.push({ at: worldAt, t, ownerId: textOwnerId(t) });
    }
  }
  if (showTracks) {
    for (const track of modelTracks) {
      if (!track.layer || hidden.has(track.layer))
        continue;
      let arr = tracksByLayer.get(track.layer);
      if (!arr) {
        arr = [];
        tracksByLayer.set(track.layer, arr);
      }
      arr.push({ t: track, ownerId: trackOwnerId(track) });
    }
    for (const via of modelVias) {
      const ownerId = viaOwnerId(via);
      for (const l of via.copper_layers) {
        if (hidden.has(l))
          continue;
        let arr = viasByLayer.get(l);
        if (!arr) {
          arr = [];
          viasByLayer.set(l, arr);
        }
        arr.push({ v: via, ownerId });
      }
      for (const l of via.drill_layers) {
        if (hidden.has(l))
          continue;
        let arr = drillViasByLayer.get(l);
        if (!arr) {
          arr = [];
          drillViasByLayer.set(l, arr);
        }
        arr.push({ v: via, ownerId });
      }
    }
  }
  for (const fp of footprints) {
    const ownerId = footprintOwnerByRef.get(fp) ?? null;
    if (showShapes) {
      for (const d of fp.drawings) {
        if (!d.layer || hidden.has(d.layer))
          continue;
        addDrawing(d.layer, fp.at, d, ownerId);
      }
    }
    if (showText) {
      for (const t of fp.texts) {
        if (!t.layer || hidden.has(t.layer))
          continue;
        let arr = textsByLayer.get(t.layer);
        if (!arr) {
          arr = [];
          textsByLayer.set(t.layer, arr);
        }
        arr.push({ at: fp.at, t, ownerId });
      }
    }
    if (showPads) {
      for (const p of fp.pads) {
        const hasHole = !!p.hole && Math.max(0, p.hole.size_x || 0) > 0;
        for (const l of p.layers) {
          if (hidden.has(l))
            continue;
          if (isDrillLayer(l, layerById))
            continue;
          if ((p.type || "").toLowerCase() === "np_thru_hole")
            continue;
          if (hasHole && !isCopperLayer(l, layerById))
            continue;
          let arr = padsByLayer.get(l);
          if (!arr) {
            arr = [];
            padsByLayer.set(l, arr);
          }
          arr.push({ at: fp.at, p, ownerId });
        }
        if (p.hole) {
          for (const dl of padDrillLayerIds(p, layerById)) {
            if (hidden.has(dl))
              continue;
            let arr = padHolesByLayer.get(dl);
            if (!arr) {
              arr = [];
              padHolesByLayer.set(dl, arr);
            }
            arr.push({ at: fp.at, p, h: p.hole, ownerId });
          }
        }
      }
    }
  }
  const allLayerNames = /* @__PURE__ */ new Set([
    ...drawingsByLayer.keys(),
    ...tracksByLayer.keys(),
    ...viasByLayer.keys(),
    ...drillViasByLayer.keys(),
    ...padsByLayer.keys(),
    ...padHolesByLayer.keys(),
    ...textsByLayer.keys()
  ]);
  const sortedNames = [...allLayerNames].sort((a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById));
  for (const ln of sortedNames) {
    let [r, g, b, a] = getLayerColor(ln, layerById);
    if (tint) {
      [r, g, b] = tint;
      a = 1;
    }
    const layer = renderer.get_layer(ln);
    const tracks = tracksByLayer.get(ln);
    if (tracks)
      for (const { t, ownerId } of tracks) {
        const pts = t.mid ? arcToPoints(t.start, t.mid, t.end) : [p2v(t.start), p2v(t.end)];
        layer.geometry.add_polyline(pts, t.width, r, g, b, a, ownerId);
      }
    const vias = viasByLayer.get(ln);
    if (vias)
      for (const { v, ownerId } of vias) {
        const outerD = v.size, drillD = v.drill;
        if (drillD > 0 && outerD > drillD) {
          const ringPoints = circleToPoints(v.at.x, v.at.y, (outerD + drillD) / 4);
          layer.geometry.add_polyline(ringPoints, (outerD - drillD) / 2, r, g, b, Math.max(a, 0.78), ownerId);
        } else if (outerD > 0) {
          layer.geometry.add_circle(v.at.x, v.at.y, outerD / 2, r, g, b, Math.max(a, 0.78), ownerId);
        }
      }
    const pads = padsByLayer.get(ln);
    if (pads)
      for (const { at, p, ownerId } of pads)
        paintPad(layer, at, p, ln, layerById, ownerId);
    const drawings = drawingsByLayer.get(ln);
    if (drawings)
      for (const { at, d, ownerId } of drawings)
        paintDrawing(layer, at, d, r, g, b, a, ownerId);
    const texts = textsByLayer.get(ln);
    if (texts)
      for (const { at, t, ownerId } of texts)
        paintText(layer, at, t, r, g, b, a, ownerId);
    const dvias = drillViasByLayer.get(ln);
    if (dvias)
      for (const { v, ownerId } of dvias)
        layer.geometry.add_circle(v.at.x, v.at.y, v.drill / 2, r, g, b, a, ownerId);
    const pholes = padHolesByLayer.get(ln);
    if (pholes)
      for (const { at, p, h, ownerId } of pholes)
        paintPadHole(layer, at, p, h, r, g, b, a, ownerId);
  }
}
function paintStaticBoard(renderer, model, hiddenLayers, skipped) {
  const hidden = hiddenLayers ?? /* @__PURE__ */ new Set();
  const layerById = buildLayerMap(model);
  renderer.dispose_layers();
  if (!hidden.has("Edge.Cuts"))
    paintBoardEdges(renderer, model, layerById);
  const skipFootprints = skipped?.footprintIndices;
  const skipTracks = skipped?.trackUuids;
  const skipVias = skipped?.viaUuids;
  const skipDrawings = skipped?.drawingUuids;
  const skipTexts = skipped?.textUuids;
  const skipZones = skipped?.zoneUuids;
  const footprints = [];
  for (let i = 0; i < model.footprints.length; i++) {
    if (!skipFootprints?.has(i))
      footprints.push(model.footprints[i]);
  }
  const tracks = skipTracks ? model.tracks.filter((track) => !track.uuid || !skipTracks.has(track.uuid)) : model.tracks;
  const vias = skipVias ? model.vias.filter((via) => !via.uuid || !skipVias.has(via.uuid)) : model.vias;
  const drawings = skipDrawings ? model.drawings.filter((drawing) => !drawing.uuid || !skipDrawings.has(drawing.uuid)) : model.drawings;
  const texts = skipTexts ? model.texts.filter((text) => !text.uuid || !skipTexts.has(text.uuid)) : model.texts;
  const zones = skipZones ? model.zones.filter((zone) => !zone.uuid || !skipZones.has(zone.uuid)) : model.zones;
  const footprintOwnerByRef = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.footprints.length; i++) {
    const footprint = model.footprints[i];
    if (!footprint)
      continue;
    footprintOwnerByRef.set(footprint, footprintOwnerId(footprint, i));
  }
  paintZones(renderer, model, hidden, layerById, zones);
  paintObjects(
    renderer,
    layerById,
    drawings,
    texts,
    tracks,
    vias,
    footprints,
    hidden,
    footprintOwnerByRef
  );
  renderer.commit_all_layers();
}
function paintDraggedSelection(renderer, model, dragged, layerById, hiddenLayers) {
  const hidden = hiddenLayers ?? /* @__PURE__ */ new Set();
  const footprintIndices = dragged.footprintIndices ?? /* @__PURE__ */ new Set();
  const trackUuids = dragged.trackUuids ?? /* @__PURE__ */ new Set();
  const viaUuids = dragged.viaUuids ?? /* @__PURE__ */ new Set();
  const drawingUuids = dragged.drawingUuids ?? /* @__PURE__ */ new Set();
  const textUuids = dragged.textUuids ?? /* @__PURE__ */ new Set();
  const zoneUuids = dragged.zoneUuids ?? /* @__PURE__ */ new Set();
  const footprints = [...footprintIndices].map((i) => model.footprints[i]).filter(Boolean);
  const tracks = trackUuids.size > 0 ? model.tracks.filter((track) => !!track.uuid && trackUuids.has(track.uuid)) : [];
  const vias = viaUuids.size > 0 ? model.vias.filter((via) => !!via.uuid && viaUuids.has(via.uuid)) : [];
  const drawings = drawingUuids.size > 0 ? model.drawings.filter((drawing) => !!drawing.uuid && drawingUuids.has(drawing.uuid)) : [];
  const texts = textUuids.size > 0 ? model.texts.filter((text) => !!text.uuid && textUuids.has(text.uuid)) : [];
  const footprintOwnerByRef = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.footprints.length; i++) {
    const footprint = model.footprints[i];
    if (!footprint)
      continue;
    footprintOwnerByRef.set(footprint, footprintOwnerId(footprint, i));
  }
  if (zoneUuids.size > 0) {
    const draggedZones = model.zones.filter((zone) => !!zone.uuid && zoneUuids.has(zone.uuid));
    if (draggedZones.length > 0) {
      paintZones(renderer, model, hidden, layerById, draggedZones);
    }
  }
  paintObjects(
    renderer,
    layerById,
    drawings,
    texts,
    tracks,
    vias,
    footprints,
    hidden,
    footprintOwnerByRef
  );
}
function paintBoardEdges(renderer, model, layerById) {
  const layer = renderer.get_layer("Edge.Cuts");
  const [r, g, b, a] = getLayerColor("Edge.Cuts", layerById);
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
}
function paintZones(renderer, model, hidden, layerById, zones = model.zones) {
  if (hidden.has("__type:zones"))
    return;
  for (const zone of zones) {
    const ownerId = zoneOwnerId(zone);
    const sortedFilledPolygons = [...zone.filled_polygons].sort(
      (a, b) => layerPaintOrder(a.layer, layerById) - layerPaintOrder(b.layer, layerById)
    );
    for (const filled of sortedFilledPolygons) {
      if (hidden.has(filled.layer))
        continue;
      const [r, g, b] = getLayerColor(filled.layer, layerById);
      const layer = renderer.get_layer(zoneRenderLayerName(filled.layer));
      const pts = filled.points.map(p2v);
      if (pts.length >= 3) {
        layer.geometry.add_polygon(pts, r, g, b, ZONE_COLOR_ALPHA, ownerId);
      }
    }
    const zoneLayersRaw = zone.layers.length > 0 ? zone.layers : [...new Set(zone.filled_polygons.map((fp) => fp.layer))];
    const zoneLayers = [...new Set(zoneLayersRaw)].sort(
      (a, b) => layerPaintOrder(a, layerById) - layerPaintOrder(b, layerById)
    );
    const shouldDrawFillFromOutline = !zone.keepout && zone.fill_enabled !== false && zone.filled_polygons.length === 0 && zone.outline.length >= 3;
    if (shouldDrawFillFromOutline) {
      const outlinePts2 = zone.outline.map(p2v);
      for (const layerName of zoneLayers) {
        if (!layerName || hidden.has(layerName))
          continue;
        const [r, g, b] = getLayerColor(layerName, layerById);
        const layer = renderer.get_layer(zoneRenderLayerName(layerName));
        layer.geometry.add_polygon(outlinePts2, r, g, b, ZONE_COLOR_ALPHA, ownerId);
      }
    }
    const shouldDrawKeepout = zone.keepout || zone.fill_enabled === false;
    if (!shouldDrawKeepout || zone.outline.length < 3)
      continue;
    const outlinePts = zone.outline.map(p2v);
    const closedOutline = [...outlinePts, outlinePts[0].copy()];
    const hatchPitch = zone.hatch_pitch && zone.hatch_pitch > 0 ? zone.hatch_pitch : 0.5;
    const hatchSegments = hatchSegmentsForPolygon(outlinePts, hatchPitch);
    for (const layerName of zoneLayers) {
      if (!layerName || hidden.has(layerName))
        continue;
      const [r, g, b, a] = getLayerColor(layerName, layerById);
      const layer = renderer.get_layer(zoneRenderLayerName(layerName));
      layer.geometry.add_polyline(closedOutline, 0.1, r, g, b, Math.max(a, 0.8), ownerId);
      for (const [start, end] of hatchSegments) {
        layer.geometry.add_polyline([start, end], 0.06, r, g, b, Math.max(a * 0.65, 0.45), ownerId);
      }
    }
  }
}
function hatchSegmentsForPolygon(points, pitch) {
  if (points.length < 3 || pitch <= 0)
    return [];
  const eps = 1e-6;
  const closed = [...points, points[0]];
  let minV = Infinity;
  let maxV = -Infinity;
  for (const p of points) {
    const v = p.y - p.x;
    if (v < minV)
      minV = v;
    if (v > maxV)
      maxV = v;
  }
  const segments = [];
  for (let c = minV - pitch; c <= maxV + pitch; c += pitch) {
    const rawIntersections = [];
    for (let i = 0; i < closed.length - 1; i++) {
      const a = closed[i];
      const b = closed[i + 1];
      const fa = a.y - a.x - c;
      const fb = b.y - b.x - c;
      if (fa > eps && fb > eps || fa < -eps && fb < -eps)
        continue;
      const denom = fa - fb;
      if (Math.abs(denom) < eps)
        continue;
      const t = fa / denom;
      if (t < -eps || t > 1 + eps)
        continue;
      rawIntersections.push(
        new Vec2(
          a.x + (b.x - a.x) * t,
          a.y + (b.y - a.y) * t
        )
      );
    }
    rawIntersections.sort((p, q) => p.x - q.x || p.y - q.y);
    const intersections = [];
    for (const p of rawIntersections) {
      const last = intersections[intersections.length - 1];
      if (!last || Math.abs(last.x - p.x) > eps || Math.abs(last.y - p.y) > eps) {
        intersections.push(p);
      }
    }
    for (let i = 0; i + 1 < intersections.length; i += 2) {
      segments.push([intersections[i], intersections[i + 1]]);
    }
  }
  return segments;
}
function isDrillLayer(layerName, layerById) {
  return layerName !== null && layerName !== void 0 && layerKind(layerName, layerById) === "drill";
}
function isCopperLayer(layerName, layerById) {
  return layerName !== null && layerName !== void 0 && layerKind(layerName, layerById) === "cu";
}
function orderedCopperLayers(layerById) {
  return [...layerById.values()].filter((layer) => layer.kind === "Cu").sort((a, b) => a.panel_order - b.panel_order).map((layer) => layer.id);
}
function orderedDrillLayers(layerById) {
  return [...layerById.values()].filter((layer) => layer.kind === "Drill").sort((a, b) => a.panel_order - b.panel_order).map((layer) => layer.id);
}
function drillLayerByRoot(layerById) {
  const byRoot = /* @__PURE__ */ new Map();
  for (const drillLayerId of orderedDrillLayers(layerById)) {
    const root = layerById.get(drillLayerId)?.root;
    if (!root)
      continue;
    if (!byRoot.has(root)) {
      byRoot.set(root, drillLayerId);
    }
  }
  return byRoot;
}
function expandCopperLayerSpan(layers, layerById, includeBetween = false) {
  const copperOrder = orderedCopperLayers(layerById);
  const selected = new Set(layers.filter((layer) => isCopperLayer(layer, layerById)));
  if (selected.size === 0)
    return [];
  const expanded = new Set(selected);
  if (includeBetween) {
    const selectedIndices = copperOrder.map((layerName, index) => ({ layerName, index })).filter(({ layerName }) => selected.has(layerName)).map(({ index }) => index).sort((a, b) => a - b);
    if (selectedIndices.length >= 2) {
      const first = selectedIndices[0];
      const last = selectedIndices[selectedIndices.length - 1];
      for (let i = first; i <= last; i++) {
        expanded.add(copperOrder[i]);
      }
    }
  }
  return copperOrder.filter((layerName) => expanded.has(layerName));
}
function padDrillLayerIds(pad, layerById) {
  const copperLayers = expandCopperLayerSpan(pad.layers, layerById, true);
  const allDrillLayers = orderedDrillLayers(layerById);
  if (copperLayers.length > 0) {
    const drillByRoot = drillLayerByRoot(layerById);
    const resolved = [];
    const seen = /* @__PURE__ */ new Set();
    for (const copperLayer of copperLayers) {
      const root = layerById.get(copperLayer)?.root;
      let drillLayer = root ? drillByRoot.get(root) : void 0;
      if (!drillLayer && copperLayer.endsWith(".Cu")) {
        drillLayer = `${copperLayer.slice(0, -3)}.Drill`;
      }
      if (!drillLayer || seen.has(drillLayer))
        continue;
      seen.add(drillLayer);
      resolved.push(drillLayer);
    }
    if (resolved.length > 0)
      return resolved;
  }
  return allDrillLayers;
}
function paintPadHole(layer, fpAt, pad, hole, r, g, b, a, ownerId = null) {
  const sx = Math.max(0, hole.size_x || 0);
  const sy = Math.max(0, hole.size_y || 0);
  if (sx <= 0 || sy <= 0)
    return;
  const offset = hole.offset ?? { x: 0, y: 0 };
  const center = padTransform(fpAt, pad.at, offset.x, offset.y);
  const isOval = (hole.shape ?? "").toLowerCase() === "oval" || Math.abs(sx - sy) > 1e-6;
  if (!isOval) {
    layer.geometry.add_circle(center.x, center.y, sx / 2, r, g, b, a, ownerId);
    return;
  }
  const major = Math.max(sx, sy);
  const minor = Math.min(sx, sy);
  const focal = Math.max(0, (major - minor) / 2);
  const p1 = sx >= sy ? padTransform(fpAt, pad.at, offset.x - focal, offset.y) : padTransform(fpAt, pad.at, offset.x, offset.y - focal);
  const p2 = sx >= sy ? padTransform(fpAt, pad.at, offset.x + focal, offset.y) : padTransform(fpAt, pad.at, offset.x, offset.y + focal);
  layer.geometry.add_polyline([p1, p2], minor, r, g, b, a, ownerId);
}
function paintDrawing(layer, fpAt, drawing, r, g, b, a, ownerId = null) {
  const rawWidth = Number.isFinite(drawing.width) ? drawing.width : 0;
  const strokeWidth = rawWidth > 0 ? rawWidth : drawing.filled ? 0 : 0.12;
  switch (drawing.type) {
    case "line": {
      const p1 = fpTransform(fpAt, drawing.start.x, drawing.start.y);
      const p2 = fpTransform(fpAt, drawing.end.x, drawing.end.y);
      layer.geometry.add_polyline([p1, p2], strokeWidth, r, g, b, a, ownerId);
      break;
    }
    case "arc": {
      const localPts = arcToPoints(drawing.start, drawing.mid, drawing.end);
      const worldPts = localPts.map((p) => fpTransform(fpAt, p.x, p.y));
      layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
      break;
    }
    case "circle": {
      const cx = drawing.center.x;
      const cy = drawing.center.y;
      const rad = Math.sqrt((drawing.end.x - cx) ** 2 + (drawing.end.y - cy) ** 2);
      const pts = [];
      for (let i = 0; i <= 48; i++) {
        const angle = i / 48 * 2 * Math.PI;
        pts.push(new Vec2(cx + rad * Math.cos(angle), cy + rad * Math.sin(angle)));
      }
      const worldPts = pts.map((p) => fpTransform(fpAt, p.x, p.y));
      if (drawing.filled && worldPts.length >= 3) {
        layer.geometry.add_polygon(worldPts, r, g, b, a, ownerId);
      }
      if (strokeWidth > 0) {
        layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
      }
      break;
    }
    case "rect": {
      const s = drawing.start;
      const e = drawing.end;
      const corners = [
        fpTransform(fpAt, s.x, s.y),
        fpTransform(fpAt, e.x, s.y),
        fpTransform(fpAt, e.x, e.y),
        fpTransform(fpAt, s.x, e.y)
      ];
      if (drawing.filled) {
        layer.geometry.add_polygon(corners, r, g, b, a, ownerId);
      }
      if (strokeWidth > 0) {
        layer.geometry.add_polyline([...corners, corners[0].copy()], strokeWidth, r, g, b, a, ownerId);
      }
      break;
    }
    case "polygon": {
      const worldPts = drawing.points.map((p) => fpTransform(fpAt, p.x, p.y));
      if (worldPts.length >= 3) {
        if (drawing.filled) {
          layer.geometry.add_polygon(worldPts, r, g, b, a, ownerId);
        }
        if (strokeWidth > 0) {
          layer.geometry.add_polyline([...worldPts, worldPts[0].copy()], strokeWidth, r, g, b, a, ownerId);
        }
      }
      break;
    }
    case "curve": {
      const worldPts = drawing.points.map((p) => fpTransform(fpAt, p.x, p.y));
      if (worldPts.length >= 2) {
        layer.geometry.add_polyline(worldPts, strokeWidth, r, g, b, a, ownerId);
      }
      break;
    }
  }
}
function paintText(layer, fpAt, text, r, g, b, a, ownerId = null) {
  if (!text.text.trim())
    return;
  const lines = text.text.split("\n");
  const justifySet = new Set(text.justify ?? []);
  const textWidth = text.size?.w ?? 1;
  const textHeight = text.size?.h ?? 1;
  const linePitch = textHeight * 1.62;
  const totalHeight = textHeight * 1.17 + Math.max(0, lines.length - 1) * linePitch;
  let baseOffsetY = textHeight;
  if (justifySet.has("center") || !justifySet.has("top") && !justifySet.has("bottom")) {
    baseOffsetY -= totalHeight / 2;
  } else if (justifySet.has("bottom")) {
    baseOffsetY -= totalHeight;
  }
  const textRotation = text.at.r || 0;
  const worldPos = fpTransform(fpAt, text.at.x, text.at.y);
  const rad = -textRotation * DEG_TO_RAD2;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  const thickness = text.thickness ?? textHeight * 0.15;
  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx];
    const layout = layoutKicadStrokeLine(line, textWidth, textHeight);
    if (layout.strokes.length === 0)
      continue;
    let lineOffsetX = 0;
    if (justifySet.has("right")) {
      lineOffsetX = -layout.advance;
    } else if (justifySet.has("center") || !justifySet.has("left") && !justifySet.has("right")) {
      lineOffsetX = -layout.advance / 2;
    }
    const lineOffsetY = baseOffsetY + lineIdx * linePitch;
    for (const stroke of layout.strokes) {
      if (stroke.length < 2)
        continue;
      const worldPoints = [];
      for (const p of stroke) {
        const lx = p.x + lineOffsetX;
        const ly = p.y + lineOffsetY;
        worldPoints.push(new Vec2(
          worldPos.x + lx * cos - ly * sin,
          worldPos.y + lx * sin + ly * cos
        ));
      }
      layer.geometry.add_polyline(worldPoints, thickness, r, g, b, a, ownerId);
    }
  }
}
function paintPad(layer, fpAt, pad, layerName, layerById, ownerId = null) {
  if (pad.layers.length === 0) {
    return;
  }
  const layerIsCopper = isCopperLayer(layerName, layerById);
  const [lr, lg, lb, la] = getLayerColor(layerName, layerById);
  const cr = lr;
  const cg = lg;
  const cb = lb;
  const ca = Math.max(la, 0.78);
  const hw = pad.size.w / 2;
  const hh = pad.size.h / 2;
  const hole = pad.hole;
  const isThroughHole = (pad.type || "").toLowerCase() === "thru_hole";
  const isNpThroughHole = (pad.type || "").toLowerCase() === "np_thru_hole";
  const holeSx = hole ? Math.max(0, hole.size_x || 0) : 0;
  const holeSy = hole ? Math.max(0, hole.size_y || 0) : 0;
  const hasPadHole = holeSx > 0 && holeSy > 0;
  if (hasPadHole && !layerIsCopper) {
    return;
  }
  if (isNpThroughHole) {
    return;
  }
  const renderAsAnnularRing = isThroughHole && hasPadHole && layerIsCopper;
  if (renderAsAnnularRing) {
    if (pad.shape === "circle") {
      const center = fpTransform(fpAt, pad.at.x, pad.at.y);
      const outerDiameter = Math.max(pad.size.w, pad.size.h);
      const holeDiameter = Math.max(holeSx, holeSy);
      const annulus = (outerDiameter - holeDiameter) / 2;
      const centerlineRadius = (outerDiameter + holeDiameter) / 4;
      if (annulus > 0 && centerlineRadius > 0) {
        const ringPoints = circleToPoints(center.x, center.y, centerlineRadius);
        if (ringPoints.length > 1) {
          layer.geometry.add_polyline(ringPoints, annulus, cr, cg, cb, ca, ownerId);
          return;
        }
      }
    } else if (pad.shape === "oval") {
      const outerMajor = Math.max(pad.size.w, pad.size.h);
      const outerMinor = Math.min(pad.size.w, pad.size.h);
      const holeMajor = Math.max(holeSx, holeSy);
      const holeMinor = Math.min(holeSx, holeSy);
      const annulus = Math.min(
        (outerMajor - holeMajor) / 2,
        (outerMinor - holeMinor) / 2
      );
      if (annulus > 0) {
        const centerMajor = outerMajor - annulus;
        const centerMinor = outerMinor - annulus;
        if (centerMajor > 0 && centerMinor > 0) {
          const horizontal = pad.size.w >= pad.size.h;
          const radius = centerMinor / 2;
          const halfSpan = Math.max(0, (centerMajor - centerMinor) / 2);
          const arcSegments = 18;
          const localPoints = [];
          for (let i = 0; i <= arcSegments; i++) {
            const angle = Math.PI / 2 - Math.PI * i / arcSegments;
            localPoints.push(
              horizontal ? new Vec2(
                halfSpan + radius * Math.cos(angle),
                radius * Math.sin(angle)
              ) : new Vec2(
                -radius * Math.sin(angle),
                halfSpan + radius * Math.cos(angle)
              )
            );
          }
          for (let i = 0; i <= arcSegments; i++) {
            const angle = -Math.PI / 2 + Math.PI * i / arcSegments;
            localPoints.push(
              horizontal ? new Vec2(
                -halfSpan - radius * Math.cos(angle),
                radius * Math.sin(angle)
              ) : new Vec2(
                -radius * Math.sin(angle),
                -halfSpan - radius * Math.cos(angle)
              )
            );
          }
          if (localPoints.length > 2) {
            localPoints.push(localPoints[0].copy());
            const ringPoints = localPoints.map((p) => padTransform(fpAt, pad.at, p.x, p.y));
            layer.geometry.add_polyline(ringPoints, annulus, cr, cg, cb, ca, ownerId);
            return;
          }
        }
      }
    }
  }
  if (pad.shape === "circle") {
    const center = fpTransform(fpAt, pad.at.x, pad.at.y);
    layer.geometry.add_circle(center.x, center.y, hw, cr, cg, cb, ca, ownerId);
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
    layer.geometry.add_polyline([p1, p2], shortAxis * 2, cr, cg, cb, ca, ownerId);
  } else {
    const corners = [
      padTransform(fpAt, pad.at, -hw, -hh),
      padTransform(fpAt, pad.at, hw, -hh),
      padTransform(fpAt, pad.at, hw, hh),
      padTransform(fpAt, pad.at, -hw, hh)
    ];
    layer.geometry.add_polygon(corners, cr, cg, cb, ca, ownerId);
  }
}
function paintSelection(renderer, fp) {
  const layer = renderer.start_dynamic_layer("selection");
  drawFootprintSelectionBox(layer, fp, SELECTION_STROKE_WIDTH, 0.85, SELECTION_GROW, 0.12);
  renderer.commit_dynamic_layer(layer);
}
function paintGroupHalos(renderer, footprints, memberIndices, mode) {
  if (memberIndices.length === 0)
    return null;
  const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-selection" : "group-hover");
  const strokeWidth = mode === "selected" ? GROUP_SELECTION_STROKE_WIDTH : HOVER_SELECTION_STROKE_WIDTH;
  const alpha = mode === "selected" ? 0.7 : 0.45;
  const grow = mode === "selected" ? GROUP_SELECTION_GROW : HOVER_SELECTION_GROW;
  const fillAlpha = mode === "selected" ? 0.09 : 0.055;
  for (const index of memberIndices) {
    const fp = footprints[index];
    if (!fp)
      continue;
    drawFootprintSelectionBox(layer, fp, strokeWidth, alpha, grow, fillAlpha);
  }
  renderer.commit_dynamic_layer(layer);
  return null;
}
function paintGroupBBox(renderer, footprints, memberIndices, mode) {
  if (memberIndices.length === 0)
    return;
  const grow = mode === "selected" ? 0.4 : 0.28;
  const strokeWidth = mode === "selected" ? 0.12 : 0.09;
  const alpha = mode === "selected" ? 0.8 : 0.4;
  const fillAlpha = mode === "selected" ? 0.06 : 0.025;
  const boxes = [];
  for (const index of memberIndices) {
    const fp = footprints[index];
    if (!fp)
      continue;
    const b = footprintBBox(fp);
    if (b.w > 0 || b.h > 0)
      boxes.push(b);
  }
  if (boxes.length === 0)
    return;
  const combined = BBox.combine(boxes).grow(grow);
  if (combined.w <= 0 || combined.h <= 0)
    return;
  const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-bbox-selected" : "group-bbox-hover");
  const corners = [
    new Vec2(combined.x, combined.y),
    new Vec2(combined.x2, combined.y),
    new Vec2(combined.x2, combined.y2),
    new Vec2(combined.x, combined.y2),
    new Vec2(combined.x, combined.y)
  ];
  if (fillAlpha > 0) {
    layer.geometry.add_polygon(corners.slice(0, 4), 0.4, 0.75, 1, fillAlpha);
  }
  layer.geometry.add_polyline(corners, strokeWidth, 0.4, 0.75, 1, alpha);
  renderer.commit_dynamic_layer(layer);
}
function paintBBoxOutline(renderer, bbox, mode) {
  const grow = mode === "selected" ? 0.4 : 0.28;
  const strokeWidth = mode === "selected" ? 0.12 : 0.09;
  const alpha = mode === "selected" ? 0.8 : 0.4;
  const fillAlpha = mode === "selected" ? 0.06 : 0.025;
  const grown = bbox.grow(grow);
  if (grown.w <= 0 || grown.h <= 0)
    return;
  const layer = renderer.start_dynamic_layer(mode === "selected" ? "group-bbox-selected" : "group-bbox-hover");
  const corners = [
    new Vec2(grown.x, grown.y),
    new Vec2(grown.x2, grown.y),
    new Vec2(grown.x2, grown.y2),
    new Vec2(grown.x, grown.y2),
    new Vec2(grown.x, grown.y)
  ];
  if (fillAlpha > 0) {
    layer.geometry.add_polygon(corners.slice(0, 4), 0.4, 0.75, 1, fillAlpha);
  }
  layer.geometry.add_polyline(corners, strokeWidth, 0.4, 0.75, 1, alpha);
  renderer.commit_dynamic_layer(layer);
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
  for (const drawing of model.drawings) {
    switch (drawing.type) {
      case "line":
        points.push(p2v(drawing.start));
        points.push(p2v(drawing.end));
        break;
      case "arc":
        points.push(p2v(drawing.start));
        points.push(p2v(drawing.mid));
        points.push(p2v(drawing.end));
        break;
      case "circle":
        points.push(p2v(drawing.center));
        points.push(p2v(drawing.end));
        break;
      case "rect":
        points.push(p2v(drawing.start));
        points.push(p2v(drawing.end));
        break;
      case "polygon":
      case "curve":
        for (const p of drawing.points)
          points.push(p2v(p));
        break;
    }
  }
  for (const text of model.texts) {
    points.push(new Vec2(text.at.x, text.at.y));
  }
  for (const fp of model.footprints) {
    points.push(new Vec2(fp.at.x, fp.at.y));
    for (const pad of fp.pads) {
      points.push(fpTransform(fp.at, pad.at.x, pad.at.y));
    }
    for (const text of fp.texts) {
      points.push(fpTransform(fp.at, text.at.x, text.at.y));
    }
  }
  for (const track of model.tracks) {
    points.push(p2v(track.start));
    points.push(p2v(track.end));
  }
  if (points.length === 0)
    return new BBox(0, 0, 100, 100);
  return BBox.from_points(points).grow(5);
}

// src/layout_client.ts
function extractErrorMessage(payload, status) {
  if (payload && typeof payload === "object") {
    const obj = payload;
    if (typeof obj.message === "string" && obj.message.trim()) {
      return obj.message;
    }
    if (typeof obj.detail === "string" && obj.detail.trim()) {
      return obj.detail;
    }
    if (Array.isArray(obj.detail)) {
      const parts = obj.detail.map((item) => {
        if (item && typeof item === "object") {
          const entry = item;
          if (typeof entry.msg === "string" && entry.msg.trim())
            return entry.msg;
        }
        return "";
      }).filter(Boolean);
      if (parts.length > 0) {
        return parts.join("; ");
      }
    }
  }
  return `Request failed (${status})`;
}
var LayoutClient = class {
  baseUrl;
  apiPrefix;
  wsPath;
  ws = null;
  reconnectTimer = null;
  constructor(baseUrl2, apiPrefix2 = "/api", wsPath2 = "/ws") {
    this.baseUrl = baseUrl2;
    this.apiPrefix = apiPrefix2;
    this.wsPath = wsPath2;
  }
  async fetchRenderModel() {
    const resp = await fetch(`${this.baseUrl}${this.apiPrefix}/render-model`);
    return await resp.json();
  }
  async executeAction(action) {
    const postAction = async (payload2) => fetch(`${this.baseUrl}${this.apiPrefix}/execute-action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload2)
    });
    const resp = await postAction(action);
    let payload = null;
    try {
      payload = await resp.json();
    } catch {
      payload = null;
    }
    if (payload && typeof payload === "object" && "status" in payload && (payload.status === "ok" || payload.status === "error")) {
      return payload;
    }
    if (!resp.ok) {
      return {
        status: "error",
        code: `http_${resp.status}`,
        message: extractErrorMessage(payload, resp.status),
        delta: null,
        action_id: null
      };
    }
    return {
      status: "error",
      code: "invalid_response",
      message: "Layout action response payload is missing status.",
      delta: null,
      action_id: null
    };
  }
  connect(onUpdate) {
    const wsUrl = this.baseUrl.replace(/^http/, "ws") + this.wsPath;
    this.ws = new WebSocket(wsUrl);
    this.ws.onopen = () => console.log("WS connected");
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "layout_updated" && msg.model || msg.type === "layout_delta" && msg.delta) {
        onUpdate(msg);
      }
    };
    this.ws.onerror = (err) => console.error("WS error:", err);
    this.ws.onclose = () => {
      if (this.reconnectTimer !== null) {
        window.clearTimeout(this.reconnectTimer);
      }
      this.reconnectTimer = window.setTimeout(() => {
        this.reconnectTimer = null;
        this.connect(onUpdate);
      }, 2e3);
    };
  }
  disconnect() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }
};

// src/text_overlay.ts
var DEG_TO_RAD3 = Math.PI / 180;
var PAD_ANNOTATION_FONT_STACK = '"IBM Plex Mono", "Roboto Mono", "Menlo", "Consolas", "Liberation Mono", "DejaVu Sans Mono", "Courier New", monospace';
var PAD_ANNOTATION_NAME_WEIGHT = 550;
var PAD_ANNOTATION_NUMBER_WEIGHT = 650;
var PAD_ANNOTATION_NUMBER_COLOR = "rgba(13, 20, 31, 0.98)";
function drawPadAnnotationText(ctx, camera, viewportWidth, viewportHeight, text, worldX, worldY, rotationDeg, charH, color, fontWeight) {
  const lines = text.split("\n").map((line) => line.trim()).filter((line) => line.length > 0);
  if (lines.length === 0)
    return;
  const screenPos = camera.world_to_screen(new Vec2(worldX, worldY));
  if (screenPos.x < -100 || screenPos.x > viewportWidth + 100 || screenPos.y < -100 || screenPos.y > viewportHeight + 100) {
    return;
  }
  const fontPx = Math.max(charH * Math.max(camera.zoom, 1e-6), 0.8);
  ctx.save();
  ctx.translate(screenPos.x, screenPos.y);
  ctx.rotate(-(rotationDeg || 0) * DEG_TO_RAD3);
  ctx.font = `${fontWeight} ${fontPx}px ${PAD_ANNOTATION_FONT_STACK}`;
  ctx.fontKerning = "normal";
  ctx.textAlign = "left";
  ctx.fillStyle = color;
  if (lines.length === 1) {
    ctx.textBaseline = "alphabetic";
    const metrics = ctx.measureText(lines[0]);
    const left = metrics.actualBoundingBoxLeft ?? 0;
    const right = metrics.actualBoundingBoxRight ?? metrics.width;
    const ascent = metrics.actualBoundingBoxAscent ?? fontPx * 0.78;
    const descent = metrics.actualBoundingBoxDescent ?? fontPx * 0.22;
    const x = -((left + right) / 2);
    const y = (ascent - descent) / 2;
    ctx.fillText(lines[0], x, y);
  } else {
    const lineHeight = fontPx * 1.08;
    const centerLine = (lines.length - 1) / 2;
    ctx.textBaseline = "middle";
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const metrics = ctx.measureText(line);
      const left = metrics.actualBoundingBoxLeft ?? 0;
      const right = metrics.actualBoundingBoxRight ?? metrics.width;
      const x = -((left + right) / 2);
      const y = (i - centerLine) * lineHeight;
      ctx.fillText(line, x, y);
    }
  }
  ctx.restore();
}
function renderTextOverlay(ctx, model, camera, hiddenLayers, layerById, vpWidth, vpHeight, visibleFpIndices, options) {
  const dpr = Math.max(window.devicePixelRatio || 1, 1);
  const width = vpWidth ?? window.innerWidth;
  const height = vpHeight ?? window.innerHeight;
  const pixelWidth = Math.round(width * dpr);
  const pixelHeight = Math.round(height * dpr);
  let resized = false;
  if (ctx.canvas.width !== pixelWidth) {
    ctx.canvas.width = pixelWidth;
    resized = true;
  }
  if (ctx.canvas.height !== pixelHeight) {
    ctx.canvas.height = pixelHeight;
    resized = true;
  }
  const styleWidth = `${width}px`;
  const styleHeight = `${height}px`;
  if (ctx.canvas.style.width !== styleWidth) {
    ctx.canvas.style.width = styleWidth;
  }
  if (ctx.canvas.style.height !== styleHeight) {
    ctx.canvas.style.height = styleHeight;
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (resized || options?.clearCanvas !== false) {
    ctx.clearRect(0, 0, width, height);
  }
  if (!model || camera.zoom < 1.5)
    return;
  const offset = options?.worldOffset ?? new Vec2(0, 0);
  const fpIndices = visibleFpIndices ?? [...Array(model.footprints.length).keys()];
  const minScreenSize = 60;
  for (const idx of fpIndices) {
    const fp = model.footprints[idx];
    if (!fp)
      continue;
    if (hiddenLayers.has("__type:pads"))
      continue;
    const bbox = footprintBBox(fp);
    if (Math.max(bbox.w, bbox.h) * camera.zoom < minScreenSize)
      continue;
    const annotationsByLayer = buildPadAnnotationGeometry(fp, hiddenLayers);
    const layerNames = Array.from(annotationsByLayer.keys());
    if (layerNames.length > 1) {
      layerNames.sort((a, b) => {
        const orderA = layerById.get(a)?.paint_order ?? Number.MAX_SAFE_INTEGER;
        const orderB = layerById.get(b)?.paint_order ?? Number.MAX_SAFE_INTEGER;
        if (orderA !== orderB)
          return orderA - orderB;
        return a.localeCompare(b);
      });
    }
    for (const layerName of layerNames) {
      const geometry = annotationsByLayer.get(layerName);
      if (!geometry)
        continue;
      const [r, g, b, a] = getLayerColor(layerName, layerById);
      const color = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${Math.max(a, 0.7)})`;
      for (const name of geometry.names) {
        drawPadAnnotationText(
          ctx,
          camera,
          width,
          height,
          name.text,
          name.x + offset.x,
          name.y + offset.y,
          name.rotation,
          name.charH,
          color,
          PAD_ANNOTATION_NAME_WEIGHT
        );
      }
      for (const number of geometry.numbers) {
        const badgeX = number.badgeCenterX + offset.x;
        const badgeY = number.badgeCenterY + offset.y;
        const screenPos = camera.world_to_screen(new Vec2(badgeX, badgeY));
        const screenRadius = Math.max(number.badgeRadius * camera.zoom, 2);
        ctx.beginPath();
        ctx.arc(screenPos.x, screenPos.y, screenRadius, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = Math.max(screenRadius * 0.18, 0.8);
        ctx.strokeStyle = "rgba(13, 20, 31, 0.85)";
        ctx.stroke();
        if (!number.labelFit)
          continue;
        const [, charH] = number.labelFit;
        drawPadAnnotationText(
          ctx,
          camera,
          width,
          height,
          number.text,
          badgeX,
          badgeY,
          0,
          charH,
          PAD_ANNOTATION_NUMBER_COLOR,
          PAD_ANNOTATION_NUMBER_WEIGHT
        );
      }
    }
  }
}

// src/render_loop.ts
var RenderLoop = class {
  constructor(tick) {
    this.tick = tick;
  }
  rafHandle = null;
  start() {
    if (this.rafHandle !== null)
      return;
    const loop = () => {
      this.tick();
      this.rafHandle = window.requestAnimationFrame(loop);
    };
    this.rafHandle = window.requestAnimationFrame(loop);
  }
  stop() {
    if (this.rafHandle === null)
      return;
    window.cancelAnimationFrame(this.rafHandle);
    this.rafHandle = null;
  }
};

// src/footprint_groups.ts
function drawingPoints(drawing) {
  switch (drawing.type) {
    case "line":
      return [new Vec2(drawing.start.x, drawing.start.y), new Vec2(drawing.end.x, drawing.end.y)];
    case "arc":
      return [
        new Vec2(drawing.start.x, drawing.start.y),
        new Vec2(drawing.mid.x, drawing.mid.y),
        new Vec2(drawing.end.x, drawing.end.y)
      ];
    case "circle": {
      const cx = drawing.center.x, cy = drawing.center.y;
      const r = Math.hypot(drawing.end.x - cx, drawing.end.y - cy);
      return [new Vec2(cx - r, cy - r), new Vec2(cx + r, cy + r)];
    }
    case "rect":
      return [new Vec2(drawing.start.x, drawing.start.y), new Vec2(drawing.end.x, drawing.end.y)];
    case "polygon":
    case "curve":
      return drawing.points.map((p) => new Vec2(p.x, p.y));
    default:
      return [];
  }
}
function buildGroupIndex(model) {
  const groupsById = /* @__PURE__ */ new Map();
  const groupIdByFpIndex = /* @__PURE__ */ new Map();
  const indexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.footprints.length; i++) {
    const uuid = model.footprints[i].uuid;
    if (uuid)
      indexByUuid.set(uuid, i);
  }
  const trackIndexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.tracks.length; i++) {
    const uuid = model.tracks[i].uuid;
    if (uuid)
      trackIndexByUuid.set(uuid, i);
  }
  const viaIndexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.vias.length; i++) {
    const uuid = model.vias[i].uuid;
    if (uuid)
      viaIndexByUuid.set(uuid, i);
  }
  const drawingIndexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.drawings.length; i++) {
    const uuid = model.drawings[i].uuid;
    if (uuid)
      drawingIndexByUuid.set(uuid, i);
  }
  const textIndexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.texts.length; i++) {
    const uuid = model.texts[i].uuid;
    if (uuid)
      textIndexByUuid.set(uuid, i);
  }
  const zoneIndexByUuid = /* @__PURE__ */ new Map();
  for (let i = 0; i < model.zones.length; i++) {
    const uuid = model.zones[i].uuid;
    if (uuid)
      zoneIndexByUuid.set(uuid, i);
  }
  const usedIds = /* @__PURE__ */ new Set();
  for (let i = 0; i < model.footprint_groups.length; i++) {
    const group = model.footprint_groups[i];
    const memberIndices = [];
    const memberUuids = [];
    for (const memberUuid of group.member_uuids) {
      if (!memberUuid)
        continue;
      const fpIndex = indexByUuid.get(memberUuid);
      if (fpIndex === void 0)
        continue;
      memberIndices.push(fpIndex);
      memberUuids.push(memberUuid);
    }
    const trackMemberUuids = [];
    for (const trackUuid of group.track_member_uuids ?? []) {
      if (trackUuid && trackIndexByUuid.has(trackUuid)) {
        trackMemberUuids.push(trackUuid);
      }
    }
    const viaMemberUuids = [];
    for (const viaUuid of group.via_member_uuids ?? []) {
      if (viaUuid && viaIndexByUuid.has(viaUuid)) {
        viaMemberUuids.push(viaUuid);
      }
    }
    const graphicMemberUuids = [];
    for (const uuid of group.graphic_member_uuids ?? []) {
      if (uuid && drawingIndexByUuid.has(uuid))
        graphicMemberUuids.push(uuid);
    }
    const textMemberUuids = [];
    for (const uuid of group.text_member_uuids ?? []) {
      if (uuid && textIndexByUuid.has(uuid))
        textMemberUuids.push(uuid);
    }
    const zoneMemberUuids = [];
    for (const uuid of group.zone_member_uuids ?? []) {
      if (uuid && zoneIndexByUuid.has(uuid))
        zoneMemberUuids.push(uuid);
    }
    const rawGraphicUuids = (group.graphic_member_uuids ?? []).filter(Boolean);
    if (rawGraphicUuids.length > 0 && graphicMemberUuids.length === 0) {
      console.warn("[layout] Group has graphic_member_uuids but none matched drawingIndexByUuid:", {
        groupId: group.uuid || group.name,
        rawGraphicUuids,
        drawingCount: model.drawings.length,
        drawingsWithUuid: [...Array(model.drawings.length).keys()].filter((i2) => model.drawings[i2]?.uuid).length
      });
    }
    if (memberIndices.length < 2 && graphicMemberUuids.length === 0 && textMemberUuids.length === 0 && zoneMemberUuids.length === 0)
      continue;
    let graphicBBox = null;
    if (graphicMemberUuids.length > 0) {
      const pts = [];
      for (const uuid of graphicMemberUuids) {
        const idx = drawingIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const d = model.drawings[idx];
        if (d)
          pts.push(...drawingPoints(d));
      }
      if (pts.length > 0)
        graphicBBox = BBox.from_points(pts).grow(0.5);
    }
    let id = group.uuid || group.name || `group-${i + 1}`;
    if (usedIds.has(id)) {
      let suffix = 2;
      while (usedIds.has(`${id}:${suffix}`))
        suffix++;
      id = `${id}:${suffix}`;
    }
    usedIds.add(id);
    const uiGroup = {
      id,
      uuid: group.uuid,
      name: group.name,
      memberUuids,
      memberIndices,
      trackMemberUuids,
      viaMemberUuids,
      graphicMemberUuids,
      textMemberUuids,
      zoneMemberUuids,
      graphicBBox
    };
    groupsById.set(id, uiGroup);
    for (const fpIndex of memberIndices) {
      if (!groupIdByFpIndex.has(fpIndex)) {
        groupIdByFpIndex.set(fpIndex, id);
      }
    }
  }
  return { groupsById, groupIdByFpIndex, trackIndexByUuid, viaIndexByUuid, drawingIndexByUuid, textIndexByUuid, zoneIndexByUuid };
}

// src/spatial_index.ts
var SpatialIndex = class {
  grid = /* @__PURE__ */ new Map();
  cellSize = 10;
  constructor(cellSize = 10) {
    this.cellSize = cellSize;
  }
  getKeys(bbox) {
    const x1 = Math.floor(bbox.x / this.cellSize);
    const y1 = Math.floor(bbox.y / this.cellSize);
    const x2 = Math.floor(bbox.x2 / this.cellSize);
    const y2 = Math.floor(bbox.y2 / this.cellSize);
    const keys = [];
    for (let x = x1; x <= x2; x++) {
      for (let y = y1; y <= y2; y++) {
        keys.push(`${x},${y}`);
      }
    }
    return keys;
  }
  insert(obj) {
    const keys = this.getKeys(obj.bbox);
    for (const key of keys) {
      let list = this.grid.get(key);
      if (!list) {
        list = [];
        this.grid.set(key, list);
      }
      list.push(obj.index);
    }
  }
  query(bbox) {
    const keys = this.getKeys(bbox);
    const resultSet = /* @__PURE__ */ new Set();
    for (const key of keys) {
      const list = this.grid.get(key);
      if (list) {
        for (const idx of list) {
          resultSet.add(idx);
        }
      }
    }
    return Array.from(resultSet);
  }
  queryPoint(p) {
    const x = Math.floor(p.x / this.cellSize);
    const y = Math.floor(p.y / this.cellSize);
    return this.grid.get(`${x},${y}`) || [];
  }
  clear() {
    this.grid.clear();
  }
};

// src/editor.ts
var DRAG_START_THRESHOLD_PX = 4;
function captureDrawingCoords(drawing) {
  switch (drawing.type) {
    case "line":
      return [drawing.start.x, drawing.start.y, drawing.end.x, drawing.end.y];
    case "arc":
      return [drawing.start.x, drawing.start.y, drawing.mid.x, drawing.mid.y, drawing.end.x, drawing.end.y];
    case "circle":
      return [drawing.center.x, drawing.center.y, drawing.end.x, drawing.end.y];
    case "rect":
      return [drawing.start.x, drawing.start.y, drawing.end.x, drawing.end.y];
    case "polygon":
    case "curve":
      return drawing.points.flatMap((p) => [p.x, p.y]);
    default:
      return [];
  }
}
function applyDeltaToDrawing(drawing, coords, dx, dy) {
  let i = 0;
  switch (drawing.type) {
    case "line":
      drawing.start.x = coords[i++] + dx;
      drawing.start.y = coords[i++] + dy;
      drawing.end.x = coords[i++] + dx;
      drawing.end.y = coords[i++] + dy;
      break;
    case "arc":
      drawing.start.x = coords[i++] + dx;
      drawing.start.y = coords[i++] + dy;
      drawing.mid.x = coords[i++] + dx;
      drawing.mid.y = coords[i++] + dy;
      drawing.end.x = coords[i++] + dx;
      drawing.end.y = coords[i++] + dy;
      break;
    case "circle":
      drawing.center.x = coords[i++] + dx;
      drawing.center.y = coords[i++] + dy;
      drawing.end.x = coords[i++] + dx;
      drawing.end.y = coords[i++] + dy;
      break;
    case "rect":
      drawing.start.x = coords[i++] + dx;
      drawing.start.y = coords[i++] + dy;
      drawing.end.x = coords[i++] + dx;
      drawing.end.y = coords[i++] + dy;
      break;
    case "polygon":
    case "curve":
      for (const pt of drawing.points) {
        pt.x = coords[i++] + dx;
        pt.y = coords[i++] + dy;
      }
      break;
  }
}
function captureZoneCoords(zone) {
  return {
    outline: zone.outline.flatMap((p) => [p.x, p.y]),
    fills: zone.filled_polygons.map((fp) => fp.points.flatMap((p) => [p.x, p.y]))
  };
}
function applyDeltaToZone(zone, coords, dx, dy) {
  for (let i = 0; i < zone.outline.length; i++) {
    zone.outline[i].x = coords.outline[i * 2] + dx;
    zone.outline[i].y = coords.outline[i * 2 + 1] + dy;
  }
  for (let fi = 0; fi < zone.filled_polygons.length; fi++) {
    const fillPts = zone.filled_polygons[fi].points;
    const fillCoords = coords.fills[fi];
    if (!fillCoords)
      continue;
    for (let i = 0; i < fillPts.length; i++) {
      fillPts[i].x = fillCoords[i * 2] + dx;
      fillPts[i].y = fillCoords[i * 2 + 1] + dy;
    }
  }
}
var Editor = class {
  canvas;
  textOverlay;
  textCtx;
  renderer;
  camera;
  panAndZoom;
  client;
  renderLoop;
  model = null;
  footprintIndex = new SpatialIndex(5);
  footprintBBoxes = [];
  textIndex = new SpatialIndex(10);
  // Selection & interaction state
  selectionMode = "none";
  selectedFpIndex = -1;
  selectedGroupId = null;
  selectedMultiIndices = [];
  hoveredGroupId = null;
  hoveredFpIndex = -1;
  singleOverrideMode = false;
  groupsById = /* @__PURE__ */ new Map();
  groupIdByFpIndex = /* @__PURE__ */ new Map();
  trackIndexByUuid = /* @__PURE__ */ new Map();
  viaIndexByUuid = /* @__PURE__ */ new Map();
  drawingIndexByUuid = /* @__PURE__ */ new Map();
  textIndexByUuid = /* @__PURE__ */ new Map();
  zoneIndexByUuid = /* @__PURE__ */ new Map();
  dragTargetDrawingUuids = [];
  dragStartDrawingCoords = null;
  dragTargetTextUuids = [];
  dragStartTextPositions = null;
  dragTargetZoneUuids = [];
  dragStartZoneCoords = null;
  isDragging = false;
  dragStartWorld = null;
  dragTargetIndices = [];
  dragStartPositions = null;
  dragTargetTrackUuids = [];
  dragStartTrackPositions = null;
  dragTargetViaUuids = [];
  dragStartViaPositions = null;
  dragCacheActive = false;
  pendingDrag = null;
  isBoxSelecting = false;
  boxSelectStartWorld = null;
  boxSelectCurrentWorld = null;
  dynamicDirty = false;
  needsRedraw = true;
  // Layer visibility
  hiddenLayers = /* @__PURE__ */ new Set();
  defaultLayerVisibilityApplied = /* @__PURE__ */ new Set();
  onLayersChanged = null;
  // Track current mouse position
  lastMouseScreen = new Vec2(0, 0);
  // Mouse coordinate callback
  onMouseMoveCallback = null;
  onActionBusyChanged = null;
  pendingActionRequests = 0;
  actionNonce = 0;
  constructor(canvas2, baseUrl2, apiPrefix2 = "/api", wsPath2 = "/ws") {
    this.canvas = canvas2;
    this.textOverlay = this.createTextOverlay();
    this.textCtx = this.textOverlay.getContext("2d");
    this.syncTextOverlayViewport();
    this.renderer = new Renderer(canvas2);
    this.camera = new Camera2();
    this.panAndZoom = new PanAndZoom(canvas2, this.camera, () => this.requestRedraw());
    this.client = new LayoutClient(baseUrl2, apiPrefix2, wsPath2);
    this.renderLoop = new RenderLoop(() => this.onRenderFrame());
    this.setupMouseHandlers();
    this.setupKeyboardHandlers();
    this.setupResizeHandler();
    window.addEventListener("beforeunload", () => {
      this.renderLoop.stop();
      this.client.disconnect();
    });
    this.renderer.setup();
    this.renderLoop.start();
  }
  createTextOverlay() {
    const existing = document.getElementById("editor-text-overlay");
    if (existing instanceof HTMLCanvasElement) {
      return existing;
    }
    const overlay = document.createElement("canvas");
    overlay.id = "editor-text-overlay";
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100vw";
    overlay.style.height = "100vh";
    overlay.style.pointerEvents = "none";
    overlay.style.zIndex = "9";
    document.body.appendChild(overlay);
    return overlay;
  }
  getCanvasViewportMetrics() {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width > 0 ? rect.width : this.canvas.clientWidth || window.innerWidth;
    const height = rect.height > 0 ? rect.height : this.canvas.clientHeight || window.innerHeight;
    return {
      left: Number.isFinite(rect.left) ? rect.left : 0,
      top: Number.isFinite(rect.top) ? rect.top : 0,
      width,
      height
    };
  }
  syncTextOverlayViewport(viewport = this.getCanvasViewportMetrics()) {
    const left = `${viewport.left}px`;
    const top = `${viewport.top}px`;
    const width = `${viewport.width}px`;
    const height = `${viewport.height}px`;
    if (this.textOverlay.style.left !== left)
      this.textOverlay.style.left = left;
    if (this.textOverlay.style.top !== top)
      this.textOverlay.style.top = top;
    if (this.textOverlay.style.width !== width)
      this.textOverlay.style.width = width;
    if (this.textOverlay.style.height !== height)
      this.textOverlay.style.height = height;
  }
  async init() {
    await this.fetchAndPaint();
    this.connectWebSocket();
  }
  async fetchAndPaint() {
    const model = await this.client.fetchRenderModel();
    this.applyModel(model, true);
  }
  applyModel(model, fitToView = false) {
    const prevSelectedUuid = this.getSelectedSingleUuid();
    const prevSelectedMultiUuids = this.getSelectedMultiUuids();
    const prevSelectedGroupId = this.selectedGroupId;
    const prevSingleOverride = this.singleOverrideMode;
    this.model = model;
    this.rebuildGroupIndex();
    this.rebuildSpatialIndexes();
    this.restoreSelection(prevSelectedUuid, prevSelectedMultiUuids, prevSelectedGroupId, prevSingleOverride);
    this.applyDefaultLayerVisibility();
    this.paintStatic();
    this.paintDynamic();
    const viewport = this.getCanvasViewportMetrics();
    this.camera.viewport_size = new Vec2(viewport.width, viewport.height);
    if (fitToView) {
      this.camera.bbox = computeBBox(this.model);
    }
    this.requestRedraw();
    if (this.onLayersChanged)
      this.onLayersChanged();
  }
  applyDelta(delta) {
    if (!this.model)
      return;
    let changed = false;
    changed = this.replaceByUuid(this.model.footprints, delta.footprints) || changed;
    changed = this.replaceByUuid(this.model.tracks, delta.tracks) || changed;
    changed = this.replaceByUuid(this.model.vias, delta.vias) || changed;
    changed = this.replaceByUuid(this.model.drawings, delta.drawings) || changed;
    changed = this.replaceByUuid(this.model.texts, delta.texts) || changed;
    changed = this.replaceByUuid(this.model.zones, delta.zones) || changed;
    if (!changed)
      return;
    this.rebuildGroupIndex();
    this.rebuildSpatialIndexes();
    this.paintStatic();
    this.paintDynamic();
    this.requestRedraw();
  }
  replaceByUuid(target, updates) {
    if (updates.length === 0)
      return false;
    const indexByUuid = /* @__PURE__ */ new Map();
    for (let i = 0; i < target.length; i++) {
      const uuid = target[i]?.uuid;
      if (uuid)
        indexByUuid.set(uuid, i);
    }
    let changed = false;
    for (const update of updates) {
      const uuid = update.uuid;
      if (!uuid)
        continue;
      const idx = indexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      target[idx] = update;
      changed = true;
    }
    return changed;
  }
  applyDefaultLayerVisibility() {
    if (!this.model)
      return;
    for (const layer of this.model.layers) {
      if (this.defaultLayerVisibilityApplied.has(layer.id))
        continue;
      this.defaultLayerVisibilityApplied.add(layer.id);
      if (!layer.default_visible) {
        this.hiddenLayers.add(layer.id);
      }
    }
  }
  paintStatic(skipped) {
    if (!this.model)
      return;
    const geometryHidden = new Set(
      [...this.hiddenLayers].filter((layer) => layer.startsWith("__type:"))
    );
    paintStaticBoard(this.renderer, this.model, geometryHidden, skipped);
    for (const layer of this.model.layers) {
      this.renderer.set_layer_visible(layer.id, !this.hiddenLayers.has(layer.id));
    }
    this.renderer.set_layer_visible("Edge.Cuts", !this.hiddenLayers.has("Edge.Cuts"));
  }
  paintDynamic() {
    this.dynamicDirty = false;
    this.renderer.dispose_dynamic_overlays();
    if (!this.model)
      return;
    if (!this.singleOverrideMode && this.selectionMode !== "multi" && this.hoveredGroupId && this.hoveredGroupId !== this.selectedGroupId) {
      const hovered = this.groupsById.get(this.hoveredGroupId);
      if (hovered) {
        if (hovered.memberIndices.length > 0) {
          paintGroupBBox(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
          paintGroupHalos(this.renderer, this.model.footprints, hovered.memberIndices, "hover");
        } else if (hovered.graphicBBox) {
          paintBBoxOutline(this.renderer, hovered.graphicBBox, "hover");
        }
      }
    }
    if (!this.singleOverrideMode && this.hoveredFpIndex >= 0 && this.hoveredFpIndex < this.model.footprints.length && !(this.selectionMode === "single" && this.selectedFpIndex === this.hoveredFpIndex)) {
      paintGroupHalos(this.renderer, this.model.footprints, [this.hoveredFpIndex], "hover");
    }
    if (!this.singleOverrideMode && this.selectedGroupId) {
      const selectedGroup = this.groupsById.get(this.selectedGroupId);
      if (selectedGroup) {
        if (selectedGroup.memberIndices.length > 0) {
          paintGroupBBox(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
          paintGroupHalos(this.renderer, this.model.footprints, selectedGroup.memberIndices, "selected");
        } else if (selectedGroup.graphicBBox) {
          paintBBoxOutline(this.renderer, selectedGroup.graphicBBox, "selected");
        }
      }
    }
    if (this.selectionMode === "multi" && this.selectedMultiIndices.length > 0) {
      paintGroupHalos(this.renderer, this.model.footprints, this.selectedMultiIndices, "selected");
    }
    if (this.selectionMode === "single" && this.selectedFpIndex >= 0 && this.selectedFpIndex < this.model.footprints.length) {
      paintSelection(this.renderer, this.model.footprints[this.selectedFpIndex]);
    }
    this.paintBoxSelectionOverlay();
    if (this.isDragging && this.dragStartWorld) {
      const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
      const delta = worldPos.sub(this.dragStartWorld);
      const trans = Matrix3.translation(delta.x, delta.y);
      for (const layer of this.renderer.dynamicLayers) {
        layer.transform = trans;
      }
    }
  }
  rebuildGroupIndex() {
    if (!this.model)
      return;
    const index = buildGroupIndex(this.model);
    this.groupsById = index.groupsById;
    this.groupIdByFpIndex = index.groupIdByFpIndex;
    this.trackIndexByUuid = index.trackIndexByUuid;
    this.viaIndexByUuid = index.viaIndexByUuid;
    this.drawingIndexByUuid = index.drawingIndexByUuid;
    this.textIndexByUuid = index.textIndexByUuid;
    this.zoneIndexByUuid = index.zoneIndexByUuid;
  }
  rebuildSpatialIndexes() {
    if (!this.model)
      return;
    this.footprintIndex.clear();
    this.footprintBBoxes = new Array(this.model.footprints.length);
    for (let i = 0; i < this.model.footprints.length; i++) {
      const fp = this.model.footprints[i];
      const bbox = footprintBBox(fp);
      this.footprintBBoxes[i] = bbox;
      this.footprintIndex.insert({ bbox, index: i });
    }
    this.textIndex.clear();
    for (let i = 0; i < this.model.texts.length; i++) {
      const txt = this.model.texts[i];
      const bbox = new BBox(txt.at.x - 1, txt.at.y - 1, 2, 2);
      this.textIndex.insert({ bbox, index: i });
    }
  }
  getSelectedSingleUuid() {
    if (!this.model || this.selectedFpIndex < 0)
      return null;
    return this.model.footprints[this.selectedFpIndex]?.uuid ?? null;
  }
  getSelectedMultiUuids() {
    if (!this.model || this.selectionMode !== "multi" || this.selectedMultiIndices.length === 0)
      return [];
    const uuids = [];
    for (const index of this.selectedMultiIndices) {
      const uuid = this.model.footprints[index]?.uuid;
      if (uuid)
        uuids.push(uuid);
    }
    return uuids;
  }
  restoreSelection(prevSelectedUuid, prevSelectedMultiUuids, prevSelectedGroupId, prevSingleOverride) {
    this.selectionMode = "none";
    this.selectedFpIndex = -1;
    this.selectedGroupId = null;
    this.selectedMultiIndices = [];
    this.hoveredGroupId = null;
    this.hoveredFpIndex = -1;
    this.singleOverrideMode = prevSingleOverride;
    if (!this.model) {
      this.singleOverrideMode = false;
      return;
    }
    if (!prevSingleOverride && prevSelectedGroupId && this.groupsById.has(prevSelectedGroupId)) {
      this.selectionMode = "group";
      this.selectedGroupId = prevSelectedGroupId;
      return;
    }
    if (!prevSingleOverride && prevSelectedMultiUuids.length > 0) {
      const selectedIndices = [];
      const selectedSet = new Set(prevSelectedMultiUuids);
      for (let i = 0; i < this.model.footprints.length; i++) {
        const uuid = this.model.footprints[i].uuid;
        if (uuid && selectedSet.has(uuid))
          selectedIndices.push(i);
      }
      if (selectedIndices.length >= 2) {
        this.setMultiSelection(selectedIndices);
        return;
      }
      if (selectedIndices.length === 1) {
        this.setSingleSelection(selectedIndices[0], false);
        return;
      }
    }
    if (prevSelectedUuid) {
      for (let i = 0; i < this.model.footprints.length; i++) {
        if (this.model.footprints[i].uuid === prevSelectedUuid) {
          this.selectionMode = "single";
          this.selectedFpIndex = i;
          return;
        }
      }
    }
    this.singleOverrideMode = false;
  }
  setSingleSelection(index, enterOverride) {
    this.selectionMode = "single";
    this.selectedFpIndex = index;
    this.selectedGroupId = null;
    this.selectedMultiIndices = [];
    if (enterOverride) {
      this.singleOverrideMode = true;
    } else if (!this.groupIdByFpIndex.has(index)) {
      this.singleOverrideMode = false;
    }
  }
  setMultiSelection(indices) {
    const normalized = [...new Set(indices)].filter((i) => i >= 0).sort((a, b) => a - b);
    if (normalized.length === 0) {
      this.clearSelection();
      return;
    }
    if (normalized.length === 1) {
      this.setSingleSelection(normalized[0], false);
      return;
    }
    this.selectionMode = "multi";
    this.selectedMultiIndices = normalized;
    this.selectedGroupId = null;
    this.selectedFpIndex = -1;
    this.singleOverrideMode = false;
  }
  setGroupSelection(groupId) {
    this.selectionMode = "group";
    this.selectedGroupId = groupId;
    this.selectedFpIndex = -1;
    this.selectedMultiIndices = [];
    this.singleOverrideMode = false;
  }
  clearSelection(exitSingleOverride = false) {
    if (this.isDragging) {
      this.restorePostDragRendering();
    }
    this.selectionMode = "none";
    this.selectedFpIndex = -1;
    this.selectedGroupId = null;
    this.selectedMultiIndices = [];
    this.hoveredGroupId = null;
    this.hoveredFpIndex = -1;
    this.clearDragState();
    this.clearBoxSelectionState();
    if (exitSingleOverride) {
      this.singleOverrideMode = false;
    }
  }
  selectedGroup() {
    if (!this.selectedGroupId)
      return null;
    return this.groupsById.get(this.selectedGroupId) ?? null;
  }
  selectedGroupMembers() {
    const group = this.selectedGroup();
    return group ? group.memberIndices : [];
  }
  selectedUuids() {
    if (this.singleOverrideMode && this.selectedFpIndex >= 0) {
      const uuid = this.model?.footprints[this.selectedFpIndex]?.uuid;
      return uuid ? [uuid] : [];
    }
    if (this.selectionMode === "group" && this.selectedGroupId) {
      const group = this.groupsById.get(this.selectedGroupId);
      return group?.uuid ? [group.uuid] : group?.memberUuids ?? [];
    }
    if (this.selectionMode === "multi")
      return this.getSelectedMultiUuids();
    if (this.selectionMode === "single" && this.selectedFpIndex >= 0) {
      const uuid = this.model?.footprints[this.selectedFpIndex]?.uuid;
      return uuid ? [uuid] : [];
    }
    return [];
  }
  /** Restore all model positions from the saved drag start state. */
  revertDragPositions() {
    if (!this.model)
      return;
    if (this.dragStartPositions) {
      for (const index of this.dragTargetIndices) {
        const fp = this.model.footprints[index];
        const start = this.dragStartPositions.get(index);
        if (fp && start) {
          fp.at.x = start.x;
          fp.at.y = start.y;
        }
      }
    }
    if (this.dragStartTrackPositions) {
      for (const uuid of this.dragTargetTrackUuids) {
        const idx = this.trackIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const track = this.model.tracks[idx];
        const start = this.dragStartTrackPositions.get(uuid);
        if (!track || !start)
          continue;
        track.start.x = start.sx;
        track.start.y = start.sy;
        track.end.x = start.ex;
        track.end.y = start.ey;
        if (track.mid && start.mx !== void 0 && start.my !== void 0) {
          track.mid.x = start.mx;
          track.mid.y = start.my;
        }
      }
    }
    if (this.dragStartViaPositions) {
      for (const uuid of this.dragTargetViaUuids) {
        const idx = this.viaIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const via = this.model.vias[idx];
        const start = this.dragStartViaPositions.get(uuid);
        if (via && start) {
          via.at.x = start.x;
          via.at.y = start.y;
        }
      }
    }
    if (this.dragStartDrawingCoords) {
      for (const uuid of this.dragTargetDrawingUuids) {
        const idx = this.drawingIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const drawing = this.model.drawings[idx];
        const coords = this.dragStartDrawingCoords.get(uuid);
        if (drawing && coords)
          applyDeltaToDrawing(drawing, coords, 0, 0);
      }
    }
    if (this.dragStartTextPositions) {
      for (const uuid of this.dragTargetTextUuids) {
        const idx = this.textIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const text = this.model.texts[idx];
        const start = this.dragStartTextPositions.get(uuid);
        if (text && start) {
          text.at.x = start.x;
          text.at.y = start.y;
        }
      }
    }
    if (this.dragStartZoneCoords) {
      for (const uuid of this.dragTargetZoneUuids) {
        const idx = this.zoneIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const zone = this.model.zones[idx];
        const coords = this.dragStartZoneCoords.get(uuid);
        if (zone && coords)
          applyDeltaToZone(zone, coords, 0, 0);
      }
    }
  }
  /** Apply a drag delta to all currently tracked drag targets. */
  applyDragDelta(dx, dy) {
    if (!this.model)
      return;
    if (this.dragStartPositions) {
      for (const index of this.dragTargetIndices) {
        const fp = this.model.footprints[index];
        const start = this.dragStartPositions.get(index);
        if (fp && start) {
          fp.at.x = start.x + dx;
          fp.at.y = start.y + dy;
        }
      }
    }
    if (this.dragStartTrackPositions) {
      for (const uuid of this.dragTargetTrackUuids) {
        const idx = this.trackIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const track = this.model.tracks[idx];
        const start = this.dragStartTrackPositions.get(uuid);
        if (!track || !start)
          continue;
        track.start.x = start.sx + dx;
        track.start.y = start.sy + dy;
        track.end.x = start.ex + dx;
        track.end.y = start.ey + dy;
        if (track.mid && start.mx !== void 0 && start.my !== void 0) {
          track.mid.x = start.mx + dx;
          track.mid.y = start.my + dy;
        }
      }
    }
    if (this.dragStartViaPositions) {
      for (const uuid of this.dragTargetViaUuids) {
        const idx = this.viaIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const via = this.model.vias[idx];
        const start = this.dragStartViaPositions.get(uuid);
        if (via && start) {
          via.at.x = start.x + dx;
          via.at.y = start.y + dy;
        }
      }
    }
    if (this.dragStartDrawingCoords) {
      for (const uuid of this.dragTargetDrawingUuids) {
        const idx = this.drawingIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const drawing = this.model.drawings[idx];
        const coords = this.dragStartDrawingCoords.get(uuid);
        if (drawing && coords)
          applyDeltaToDrawing(drawing, coords, dx, dy);
      }
    }
    if (this.dragStartTextPositions) {
      for (const uuid of this.dragTargetTextUuids) {
        const idx = this.textIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const text = this.model.texts[idx];
        const start = this.dragStartTextPositions.get(uuid);
        if (text && start) {
          text.at.x = start.x + dx;
          text.at.y = start.y + dy;
        }
      }
    }
    if (this.dragStartZoneCoords) {
      for (const uuid of this.dragTargetZoneUuids) {
        const idx = this.zoneIndexByUuid.get(uuid);
        if (idx === void 0)
          continue;
        const zone = this.model.zones[idx];
        const coords = this.dragStartZoneCoords.get(uuid);
        if (zone && coords)
          applyDeltaToZone(zone, coords, dx, dy);
      }
    }
  }
  clearDragState() {
    this.isDragging = false;
    this.dragStartWorld = null;
    this.dragStartPositions = null;
    this.dragTargetIndices = [];
    this.dragTargetTrackUuids = [];
    this.dragStartTrackPositions = null;
    this.dragTargetViaUuids = [];
    this.dragStartViaPositions = null;
    this.dragTargetDrawingUuids = [];
    this.dragStartDrawingCoords = null;
    this.dragTargetTextUuids = [];
    this.dragStartTextPositions = null;
    this.dragTargetZoneUuids = [];
    this.dragStartZoneCoords = null;
    this.dragCacheActive = false;
    this.pendingDrag = null;
  }
  restorePostDragRendering() {
    if (!this.model)
      return;
    this.renderer.end_fast_drag_cache();
    this.dragCacheActive = false;
    this.renderer.dispose_dynamic_layers();
    this.paintStatic();
  }
  isObjectTypeLayer(layer) {
    return layer.startsWith("__type:");
  }
  currentDraggedSelection() {
    return {
      footprintIndices: new Set(this.dragTargetIndices),
      trackUuids: new Set(this.dragTargetTrackUuids),
      viaUuids: new Set(this.dragTargetViaUuids),
      drawingUuids: new Set(this.dragTargetDrawingUuids),
      textUuids: new Set(this.dragTargetTextUuids),
      zoneUuids: new Set(this.dragTargetZoneUuids)
    };
  }
  rebuildAfterObjectTypeVisibilityChange() {
    if (!this.model)
      return;
    if (this.isDragging) {
      const draggedSelection = this.currentDraggedSelection();
      const skipOwners = buildDragOwnerIds(this.model, draggedSelection);
      this.dragCacheActive = this.renderer.begin_fast_drag_cache(this.camera.matrix, skipOwners);
      if (!this.dragCacheActive) {
        this.paintStatic(draggedSelection);
      }
      this.renderer.dispose_dynamic_layers();
      this.renderer.isDynamicContext = true;
      paintDraggedSelection(this.renderer, this.model, draggedSelection, this.getLayerMap(), this.hiddenLayers);
      this.renderer.commit_dynamic_context_layers();
      this.renderer.isDynamicContext = false;
    } else {
      this.paintStatic();
    }
  }
  clearBoxSelectionState() {
    this.isBoxSelecting = false;
    this.boxSelectStartWorld = null;
    this.boxSelectCurrentWorld = null;
  }
  beginDragSelection(worldPos, targetIndices, trackUuids = [], viaUuids = [], drawingUuids = [], textUuids = [], zoneUuids = []) {
    const dragStartPositions = /* @__PURE__ */ new Map();
    for (const index of targetIndices) {
      const fp = this.model?.footprints[index];
      if (!fp)
        continue;
      dragStartPositions.set(index, { x: fp.at.x, y: fp.at.y });
    }
    if (dragStartPositions.size === 0 && drawingUuids.length === 0 && textUuids.length === 0 && zoneUuids.length === 0) {
      return false;
    }
    const dragStartTrackPositions = /* @__PURE__ */ new Map();
    for (const uuid of trackUuids) {
      const idx = this.trackIndexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      const track = this.model?.tracks[idx];
      if (!track)
        continue;
      dragStartTrackPositions.set(uuid, {
        sx: track.start.x,
        sy: track.start.y,
        ex: track.end.x,
        ey: track.end.y,
        ...track.mid ? { mx: track.mid.x, my: track.mid.y } : {}
      });
    }
    const dragStartViaPositions = /* @__PURE__ */ new Map();
    for (const uuid of viaUuids) {
      const idx = this.viaIndexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      const via = this.model?.vias[idx];
      if (!via)
        continue;
      dragStartViaPositions.set(uuid, { x: via.at.x, y: via.at.y });
    }
    const dragStartDrawingCoords = /* @__PURE__ */ new Map();
    for (const uuid of drawingUuids) {
      const idx = this.drawingIndexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      const drawing = this.model?.drawings[idx];
      if (!drawing)
        continue;
      dragStartDrawingCoords.set(uuid, captureDrawingCoords(drawing));
    }
    const dragStartTextPositions = /* @__PURE__ */ new Map();
    for (const uuid of textUuids) {
      const idx = this.textIndexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      const text = this.model?.texts[idx];
      if (!text)
        continue;
      dragStartTextPositions.set(uuid, { x: text.at.x, y: text.at.y, r: text.at.r });
    }
    const dragStartZoneCoords = /* @__PURE__ */ new Map();
    for (const uuid of zoneUuids) {
      const idx = this.zoneIndexByUuid.get(uuid);
      if (idx === void 0)
        continue;
      const zone = this.model?.zones[idx];
      if (!zone)
        continue;
      dragStartZoneCoords.set(uuid, captureZoneCoords(zone));
    }
    this.isDragging = true;
    this.dragStartWorld = worldPos;
    this.dragTargetIndices = [...dragStartPositions.keys()];
    this.dragStartPositions = dragStartPositions;
    this.dragTargetTrackUuids = [...dragStartTrackPositions.keys()];
    this.dragStartTrackPositions = dragStartTrackPositions;
    this.dragTargetViaUuids = [...dragStartViaPositions.keys()];
    this.dragStartViaPositions = dragStartViaPositions;
    this.dragTargetDrawingUuids = [...dragStartDrawingCoords.keys()];
    this.dragStartDrawingCoords = dragStartDrawingCoords;
    this.dragTargetTextUuids = [...dragStartTextPositions.keys()];
    this.dragStartTextPositions = dragStartTextPositions;
    this.dragTargetZoneUuids = [...dragStartZoneCoords.keys()];
    this.dragStartZoneCoords = dragStartZoneCoords;
    const draggedSelection = {
      footprintIndices: new Set(this.dragTargetIndices),
      trackUuids: new Set(this.dragTargetTrackUuids),
      viaUuids: new Set(this.dragTargetViaUuids),
      drawingUuids: new Set(this.dragTargetDrawingUuids),
      textUuids: new Set(this.dragTargetTextUuids),
      zoneUuids: new Set(this.dragTargetZoneUuids)
    };
    const skipOwners = buildDragOwnerIds(this.model, draggedSelection);
    this.dragCacheActive = this.renderer.begin_fast_drag_cache(this.camera.matrix, skipOwners);
    if (!this.dragCacheActive) {
      this.paintStatic(draggedSelection);
    }
    this.renderer.dispose_dynamic_layers();
    this.renderer.isDynamicContext = true;
    paintDraggedSelection(this.renderer, this.model, draggedSelection, this.getLayerMap(), this.hiddenLayers);
    this.renderer.commit_dynamic_context_layers();
    this.renderer.isDynamicContext = false;
    this.paintDynamic();
    this.requestRedraw();
    return true;
  }
  setPendingDrag(startWorld, startScreen, targetIndices, trackUuids = [], viaUuids = [], drawingUuids = [], textUuids = [], zoneUuids = []) {
    this.pendingDrag = {
      startWorld,
      startScreen,
      targetIndices,
      trackUuids,
      viaUuids,
      drawingUuids,
      textUuids,
      zoneUuids
    };
  }
  maybeStartPendingDrag(currentWorld, currentScreen) {
    const pending = this.pendingDrag;
    if (!pending)
      return false;
    const dx = currentScreen.x - pending.startScreen.x;
    const dy = currentScreen.y - pending.startScreen.y;
    if (dx * dx + dy * dy < DRAG_START_THRESHOLD_PX * DRAG_START_THRESHOLD_PX) {
      return false;
    }
    this.pendingDrag = null;
    return this.beginDragSelection(
      pending.startWorld,
      pending.targetIndices,
      pending.trackUuids,
      pending.viaUuids,
      pending.drawingUuids,
      pending.textUuids,
      pending.zoneUuids
    );
  }
  currentBoxSelection() {
    if (!this.boxSelectStartWorld || !this.boxSelectCurrentWorld)
      return null;
    return new BBox(
      this.boxSelectStartWorld.x,
      this.boxSelectStartWorld.y,
      this.boxSelectCurrentWorld.x - this.boxSelectStartWorld.x,
      this.boxSelectCurrentWorld.y - this.boxSelectStartWorld.y
    );
  }
  selectedIndicesForDrag(hitIdx) {
    if (this.selectionMode === "group") {
      return this.selectedGroupMembers();
    }
    if (this.selectionMode === "multi" && this.selectedMultiIndices.includes(hitIdx)) {
      return this.selectedMultiIndices;
    }
    return [hitIdx];
  }
  paintBoxSelectionOverlay() {
    if (!this.isBoxSelecting)
      return;
    const box = this.currentBoxSelection();
    if (!box)
      return;
    const corners = [
      new Vec2(box.x, box.y),
      new Vec2(box.x2, box.y),
      new Vec2(box.x2, box.y2),
      new Vec2(box.x, box.y2)
    ];
    const layer = this.renderer.start_dynamic_layer("selection-box");
    layer.geometry.add_polygon(corners, 0.44, 0.62, 0.95, 0.15);
    layer.geometry.add_polyline([...corners, corners[0].copy()], 0.1, 0.44, 0.62, 0.95, 0.8);
    this.renderer.commit_dynamic_layer(layer);
  }
  updateHoverGroup(worldPos) {
    let nextHoverId = null;
    let nextHoverFp = -1;
    if (this.model && !this.singleOverrideMode) {
      const candidateIndices = this.footprintIndex.queryPoint(worldPos);
      for (let i = candidateIndices.length - 1; i >= 0; i--) {
        const idx = candidateIndices[i];
        const bbox = this.footprintBBoxes[idx] ?? footprintBBox(this.model.footprints[idx]);
        if (bbox.contains_point(worldPos)) {
          nextHoverFp = idx;
          const groupId = this.groupIdByFpIndex.get(idx) ?? null;
          if (groupId) {
            nextHoverId = groupId;
          }
          break;
        }
      }
      if (nextHoverId === null && nextHoverFp === -1) {
        for (const [groupId, group] of this.groupsById) {
          if (group.memberIndices.length === 0 && group.graphicBBox) {
            const hit = group.graphicBBox.contains_point(worldPos);
            if (hit) {
              nextHoverId = groupId;
              break;
            }
          }
        }
      }
    }
    if (nextHoverId === this.hoveredGroupId && nextHoverFp === this.hoveredFpIndex)
      return;
    this.hoveredGroupId = nextHoverId;
    this.hoveredFpIndex = nextHoverFp;
    this.repaintWithSelection();
  }
  connectWebSocket() {
    this.client.connect((msg) => {
      if (msg.type === "layout_updated" && msg.model) {
        this.applyModel(msg.model);
        return;
      }
      if (msg.type === "layout_delta" && msg.delta) {
        this.applyDelta(msg.delta);
      }
    });
  }
  getIndexedHitIdx(worldPos) {
    if (!this.model)
      return -1;
    const candidateIndices = this.footprintIndex.queryPoint(worldPos);
    for (let i = candidateIndices.length - 1; i >= 0; i--) {
      const idx = candidateIndices[i];
      const bbox = this.footprintBBoxes[idx] ?? footprintBBox(this.model.footprints[idx]);
      if (bbox.contains_point(worldPos)) {
        return idx;
      }
    }
    return -1;
  }
  setupMouseHandlers() {
    this.canvas.addEventListener("mousedown", (e) => {
      if (e.button !== 0)
        return;
      const viewport = this.getCanvasViewportMetrics();
      this.lastMouseScreen = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);
      const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
      if (!this.model)
        return;
      if (e.shiftKey) {
        this.clearDragState();
        this.isBoxSelecting = true;
        this.boxSelectStartWorld = worldPos;
        this.boxSelectCurrentWorld = worldPos;
        this.repaintWithSelection();
        return;
      }
      this.pendingDrag = null;
      let hitIdx = -1;
      if (this.hoveredFpIndex >= 0 && this.hoveredFpIndex < this.model.footprints.length) {
        const hoveredBBox = this.footprintBBoxes[this.hoveredFpIndex] ?? footprintBBox(this.model.footprints[this.hoveredFpIndex]);
        if (hoveredBBox.contains_point(worldPos)) {
          hitIdx = this.hoveredFpIndex;
        }
      }
      if (hitIdx < 0) {
        hitIdx = this.getIndexedHitIdx(worldPos);
      }
      if (hitIdx >= 0) {
        const keepMultiSelection = this.selectionMode === "multi" && this.selectedMultiIndices.includes(hitIdx);
        if (!keepMultiSelection) {
          const hitGroupId = this.groupIdByFpIndex.get(hitIdx) ?? null;
          if (!this.singleOverrideMode && hitGroupId) {
            this.setGroupSelection(hitGroupId);
          } else {
            this.setSingleSelection(hitIdx, false);
          }
        }
        const dragTargets = this.selectedIndicesForDrag(hitIdx);
        const isGroupDrag = this.selectionMode === "group";
        const dragTrackUuids = isGroupDrag ? this.selectedGroup()?.trackMemberUuids ?? [] : [];
        const dragViaUuids = isGroupDrag ? this.selectedGroup()?.viaMemberUuids ?? [] : [];
        const dragDrawingUuids = isGroupDrag ? this.selectedGroup()?.graphicMemberUuids ?? [] : [];
        const dragTextUuids = isGroupDrag ? this.selectedGroup()?.textMemberUuids ?? [] : [];
        const dragZoneUuids = isGroupDrag ? this.selectedGroup()?.zoneMemberUuids ?? [] : [];
        this.setPendingDrag(worldPos, this.lastMouseScreen, dragTargets, dragTrackUuids, dragViaUuids, dragDrawingUuids, dragTextUuids, dragZoneUuids);
        this.repaintWithSelection();
      } else {
        let hitGraphicGroupId = null;
        if (!this.singleOverrideMode && this.hoveredGroupId) {
          const hoveredGroup = this.groupsById.get(this.hoveredGroupId);
          if (hoveredGroup && hoveredGroup.memberIndices.length === 0 && hoveredGroup.graphicBBox?.contains_point(worldPos)) {
            hitGraphicGroupId = this.hoveredGroupId;
          }
        }
        if (!this.singleOverrideMode && !hitGraphicGroupId) {
          for (const [groupId, group] of this.groupsById) {
            if (group.memberIndices.length === 0 && group.graphicBBox?.contains_point(worldPos)) {
              hitGraphicGroupId = groupId;
              break;
            }
          }
        }
        if (hitGraphicGroupId) {
          this.setGroupSelection(hitGraphicGroupId);
          const group = this.groupsById.get(hitGraphicGroupId);
          this.setPendingDrag(worldPos, this.lastMouseScreen, [], [], [], group.graphicMemberUuids, group.textMemberUuids, group.zoneMemberUuids);
          this.repaintWithSelection();
        } else {
          this.pendingDrag = null;
          this.clearSelection(true);
          this.repaintWithSelection();
        }
      }
    });
    this.canvas.addEventListener("dblclick", (e) => {
      if (e.button !== 0 || !this.model)
        return;
      const viewport = this.getCanvasViewportMetrics();
      const screenPos = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);
      const worldPos = this.camera.screen_to_world(screenPos);
      const hitIdx = this.getIndexedHitIdx(worldPos);
      if (hitIdx < 0)
        return;
      this.setSingleSelection(hitIdx, true);
      this.repaintWithSelection();
    });
    this.canvas.addEventListener("mousemove", (e) => {
      const viewport = this.getCanvasViewportMetrics();
      this.lastMouseScreen = new Vec2(e.clientX - viewport.left, e.clientY - viewport.top);
      if (this.onMouseMoveCallback) {
        const worldPos2 = this.camera.screen_to_world(this.lastMouseScreen);
        this.onMouseMoveCallback(worldPos2.x, worldPos2.y);
      }
      if (!this.model)
        return;
      const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
      if (this.isBoxSelecting) {
        this.boxSelectCurrentWorld = worldPos;
        this.repaintWithSelection();
        return;
      }
      if (!this.isDragging) {
        if (this.pendingDrag) {
          if (!this.maybeStartPendingDrag(worldPos, this.lastMouseScreen)) {
            return;
          }
        } else {
          this.updateHoverGroup(worldPos);
          return;
        }
      }
      if (!this.dragStartWorld)
        return;
      const delta = worldPos.sub(this.dragStartWorld);
      const trans = Matrix3.translation(delta.x, delta.y);
      for (const layer of this.renderer.dynamicLayers) {
        layer.transform = trans;
      }
      this.requestRedraw();
    });
    window.addEventListener("mouseup", async (e) => {
      if (e.button !== 0)
        return;
      if (this.isBoxSelecting) {
        this.singleOverrideMode = false;
        const selectionBox = this.currentBoxSelection();
        if (this.model && selectionBox) {
          const selected = hitTestFootprintsInBox(selectionBox, this.model.footprints);
          if (selected.length > 0) {
            this.setMultiSelection(selected);
          } else {
            this.clearSelection(false);
          }
        }
        this.clearBoxSelectionState();
        this.repaintWithSelection();
        return;
      }
      if (this.pendingDrag) {
        this.pendingDrag = null;
        setTimeout(() => this.repaintWithSelection(), 0);
        return;
      }
      if (!this.isDragging)
        return;
      const viewport = this.getCanvasViewportMetrics();
      const worldPos = this.camera.screen_to_world(new Vec2(e.clientX - viewport.left, e.clientY - viewport.top));
      const delta = worldPos.sub(this.dragStartWorld);
      const dx = delta.x;
      const dy = delta.y;
      if (!this.model || !this.dragStartWorld) {
        this.isDragging = false;
        this.restorePostDragRendering();
        this.clearDragState();
        this.repaintWithSelection();
        return;
      }
      if (!Number.isFinite(dx) || !Number.isFinite(dy)) {
        console.warn("Ignoring drag move with invalid delta", { dx, dy });
        this.isDragging = false;
        this.restorePostDragRendering();
        this.clearDragState();
        this.repaintWithSelection();
        return;
      }
      const isNoop = Math.abs(dx) < 1e-3 && Math.abs(dy) < 1e-3;
      const uuids = this.selectedUuids();
      if (isNoop) {
        this.isDragging = false;
        this.restorePostDragRendering();
        this.clearDragState();
        this.repaintWithSelection();
        return;
      }
      const movePromise = uuids.length > 0 ? this.executeAction({ command: "move", uuids, dx, dy }) : null;
      this.isDragging = false;
      this.applyDragDelta(dx, dy);
      this.rebuildSpatialIndexes();
      const droppedTransform = Matrix3.translation(dx, dy);
      for (const layer of this.renderer.dynamicLayers) {
        layer.transform = droppedTransform;
      }
      this.clearDragState();
      this.repaintWithSelection();
      if (movePromise) {
        void movePromise.then((ok) => {
          if (!ok) {
            this.restorePostDragRendering();
            this.repaintWithSelection();
          }
        });
      } else {
        this.restorePostDragRendering();
        this.repaintWithSelection();
      }
    });
  }
  setupKeyboardHandlers() {
    window.addEventListener("keydown", async (e) => {
      if (e.key === "Escape") {
        if (this.isDragging) {
          this.revertDragPositions();
          this.restorePostDragRendering();
        }
        this.pendingDrag = null;
        this.clearSelection(true);
        this.repaintWithSelection();
        return;
      }
      if (e.key === "r" || e.key === "R") {
        if (e.ctrlKey || e.metaKey || e.altKey)
          return;
        await this.rotateSelection(90);
        return;
      }
      if (e.key === "f" || e.key === "F") {
        if (e.ctrlKey || e.metaKey || e.altKey)
          return;
        await this.flipSelection();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        await this.executeAction({ command: "undo" });
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && e.shiftKey || (e.ctrlKey || e.metaKey) && e.key === "y") {
        e.preventDefault();
        await this.executeAction({ command: "redo" });
        return;
      }
    });
  }
  setupResizeHandler() {
    window.addEventListener("resize", () => {
      this.requestRedraw();
    });
  }
  async rotateSelection(deltaDegrees) {
    if (!this.model)
      return;
    const uuids = this.selectedUuids();
    if (uuids.length > 0) {
      await this.executeAction({ command: "rotate", uuids, delta_degrees: deltaDegrees });
    }
  }
  async flipSelection() {
    if (!this.model)
      return;
    const uuids = this.selectedUuids();
    if (uuids.length > 0) {
      await this.executeAction({ command: "flip", uuids });
    }
  }
  async executeAction(action) {
    const actionId = `a${Date.now()}_${++this.actionNonce}`;
    const taggedAction = { ...action, client_action_id: actionId };
    this.pendingActionRequests += 1;
    if (this.pendingActionRequests === 1 && this.onActionBusyChanged) {
      this.onActionBusyChanged(true);
    }
    let ok = false;
    try {
      const data = await this.client.executeAction(taggedAction);
      if (data.status === "error") {
        console.warn(`Action ${action.command} failed (${data.code}): ${data.message ?? "unknown error"}`);
      } else {
        ok = true;
      }
    } catch (err) {
      console.error("Failed to execute action:", err);
    } finally {
      if (this.pendingActionRequests > 0) {
        this.pendingActionRequests -= 1;
      } else {
        this.pendingActionRequests = 0;
      }
      if (this.pendingActionRequests === 0 && this.onActionBusyChanged) {
        this.onActionBusyChanged(false);
      }
    }
    return ok;
  }
  // --- Layer visibility ---
  setLayerVisible(layer, visible) {
    if (visible) {
      this.hiddenLayers.delete(layer);
    } else {
      this.hiddenLayers.add(layer);
    }
    if (this.isObjectTypeLayer(layer)) {
      this.rebuildAfterObjectTypeVisibilityChange();
    } else {
      this.renderer.set_layer_visible(layer, visible);
    }
    this.paintDynamic();
    this.requestRedraw();
  }
  setLayersVisible(layers, visible) {
    let objectTypeChanged = false;
    for (const layer of layers) {
      if (visible) {
        this.hiddenLayers.delete(layer);
      } else {
        this.hiddenLayers.add(layer);
      }
      if (this.isObjectTypeLayer(layer)) {
        objectTypeChanged = true;
      } else {
        this.renderer.set_layer_visible(layer, visible);
      }
    }
    if (objectTypeChanged) {
      this.rebuildAfterObjectTypeVisibilityChange();
    }
    this.paintDynamic();
    this.requestRedraw();
  }
  isLayerVisible(layer) {
    return !this.hiddenLayers.has(layer);
  }
  getLayerMap() {
    const layerById = /* @__PURE__ */ new Map();
    if (!this.model)
      return layerById;
    for (const layer of this.model.layers) {
      layerById.set(layer.id, layer);
    }
    return layerById;
  }
  getLayerModels() {
    if (!this.model)
      return [];
    return [...this.model.layers].sort((a, b) => {
      const orderDiff = a.panel_order - b.panel_order;
      if (orderDiff !== 0)
        return orderDiff;
      return a.id.localeCompare(b.id);
    });
  }
  getLayers() {
    return this.getLayerModels().map((layer) => layer.id);
  }
  setOnLayersChanged(cb) {
    this.onLayersChanged = cb;
  }
  setOnMouseMove(cb) {
    this.onMouseMoveCallback = cb;
  }
  setOnActionBusyChanged(cb) {
    this.onActionBusyChanged = cb;
    cb(this.pendingActionRequests > 0);
  }
  repaintWithSelection() {
    this.dynamicDirty = true;
    this.requestRedraw();
  }
  requestRedraw() {
    this.needsRedraw = true;
  }
  drawTextOverlay() {
    if (!this.textCtx || !this.model)
      return;
    const viewport = this.getCanvasViewportMetrics();
    this.syncTextOverlayViewport(viewport);
    const visibleFpIndices = this.footprintIndex.query(this.camera.bbox);
    const layerMap = this.getLayerMap();
    if (!this.isDragging || !this.dragStartWorld || this.dragTargetIndices.length === 0) {
      renderTextOverlay(
        this.textCtx,
        this.model,
        this.camera,
        this.hiddenLayers,
        layerMap,
        viewport.width,
        viewport.height,
        visibleFpIndices,
        { clearCanvas: true }
      );
      return;
    }
    const draggedSet = new Set(this.dragTargetIndices);
    const staticVisible = visibleFpIndices.filter((index) => !draggedSet.has(index));
    renderTextOverlay(
      this.textCtx,
      this.model,
      this.camera,
      this.hiddenLayers,
      layerMap,
      viewport.width,
      viewport.height,
      staticVisible,
      { clearCanvas: true }
    );
    const worldPos = this.camera.screen_to_world(this.lastMouseScreen);
    const delta = worldPos.sub(this.dragStartWorld);
    renderTextOverlay(
      this.textCtx,
      this.model,
      this.camera,
      this.hiddenLayers,
      layerMap,
      viewport.width,
      viewport.height,
      this.dragTargetIndices,
      { clearCanvas: false, worldOffset: delta }
    );
  }
  onRenderFrame() {
    if (!this.needsRedraw)
      return;
    this.needsRedraw = false;
    if (this.dynamicDirty) {
      this.paintDynamic();
    }
    const viewport = this.getCanvasViewportMetrics();
    this.camera.viewport_size = new Vec2(viewport.width, viewport.height);
    this.renderer.updateGrid(this.camera.bbox, 1);
    this.renderer.draw(this.camera.matrix);
    this.drawTextOverlay();
  }
};

// src/main.ts
var canvas = document.getElementById("editor-canvas");
if (!canvas) {
  throw new Error("Canvas element #editor-canvas not found");
}
var w = window;
var baseUrl = w.__LAYOUT_BASE_URL__ || window.location.origin;
var apiPrefix = w.__LAYOUT_API_PREFIX__ || "/api";
var wsPath = w.__LAYOUT_WS_PATH__ || "/ws";
var editor = new Editor(canvas, baseUrl, apiPrefix, wsPath);
w.__layoutEditor = editor;
var initialLoadingEl = document.getElementById("initial-loading");
var initialLoadingMessageEl = initialLoadingEl?.querySelector(".initial-loading-message");
var initialLoadingSubtextEl = initialLoadingEl?.querySelector(".initial-loading-subtext");
function setInitialLoading(message, subtext) {
  if (!initialLoadingEl)
    return;
  initialLoadingEl.classList.remove("hidden", "error");
  initialLoadingEl.setAttribute("aria-busy", "true");
  if (initialLoadingMessageEl)
    initialLoadingMessageEl.textContent = message;
  if (initialLoadingSubtextEl)
    initialLoadingSubtextEl.textContent = subtext;
}
function hideInitialLoading() {
  if (!initialLoadingEl)
    return;
  initialLoadingEl.classList.add("hidden");
  initialLoadingEl.setAttribute("aria-busy", "false");
}
function showInitialLoadingError(message, subtext) {
  if (!initialLoadingEl)
    return;
  initialLoadingEl.classList.remove("hidden");
  initialLoadingEl.classList.add("error");
  initialLoadingEl.setAttribute("aria-busy", "false");
  if (initialLoadingMessageEl)
    initialLoadingMessageEl.textContent = message;
  if (initialLoadingSubtextEl)
    initialLoadingSubtextEl.textContent = subtext;
}
var panelCollapsed = false;
var collapsedGroups = /* @__PURE__ */ new Set();
var objectTypesExpanded = false;
var textShapesExpanded = false;
var OBJECT_ROOT_FILTERS = [
  { id: "__type:zones", label: "Zones", color: "#5a8a3a" },
  { id: "__type:tracks", label: "Tracks & Vias", color: "#c05030" },
  { id: "__type:pads", label: "Pads", color: "#a07020" }
];
var TEXT_SHAPES_FILTERS = [
  { id: "__type:text", label: "Text", color: "#4a8cad" },
  { id: "__type:shapes", label: "Shapes", color: "#356982" }
];
var TEXT_SHAPES_FILTER_IDS = TEXT_SHAPES_FILTERS.map((t) => t.id);
var OBJECT_TYPE_IDS = [
  ...OBJECT_ROOT_FILTERS.map((t) => t.id),
  ...TEXT_SHAPES_FILTER_IDS
];
function groupLayers(layers) {
  const groupMap = /* @__PURE__ */ new Map();
  const topLevel = [];
  for (const layer of layers) {
    const group = layer.group?.trim() ?? "";
    if (!group) {
      topLevel.push(layer);
      continue;
    }
    if (!groupMap.has(group))
      groupMap.set(group, []);
    groupMap.get(group).push(layer);
  }
  const groups = [...groupMap.entries()].map(([group, groupedLayers]) => ({ group, layers: groupedLayers })).sort((a, b) => {
    const aOrder = a.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
    const bOrder = b.layers[0]?.panel_order ?? Number.MAX_SAFE_INTEGER;
    if (aOrder !== bOrder)
      return aOrder - bOrder;
    return a.group.localeCompare(b.group);
  });
  return { groups, topLevel };
}
function colorToCSS(layerName, layerById) {
  const [r, g, b] = getLayerColor(layerName, layerById);
  return `rgb(${Math.round(r * 255)},${Math.round(g * 255)},${Math.round(b * 255)})`;
}
function createSwatch(color) {
  const swatch = document.createElement("span");
  swatch.className = "layer-swatch";
  swatch.style.background = color;
  return swatch;
}
function updateRowVisual(row, visible) {
  row.style.opacity = visible ? "1" : "0.3";
}
function updateGroupVisual(row, childLayers) {
  const allVisible = childLayers.every((l) => editor.isLayerVisible(l));
  const allHidden = childLayers.every((l) => !editor.isLayerVisible(l));
  if (allVisible) {
    row.style.opacity = "1";
  } else if (allHidden) {
    row.style.opacity = "0.3";
  } else {
    row.style.opacity = "0.6";
  }
}
function buildLayerPanel() {
  const panel = document.getElementById("layer-panel");
  if (!panel)
    return;
  panel.innerHTML = "";
  const header = document.createElement("div");
  header.className = "layer-panel-header";
  const headerTitle = document.createElement("span");
  headerTitle.textContent = "Layers";
  let expandTab = document.getElementById("layer-expand-tab");
  if (!expandTab) {
    expandTab = document.createElement("div");
    expandTab.id = "layer-expand-tab";
    expandTab.className = "layer-expand-tab";
    expandTab.textContent = "Layers";
    expandTab.addEventListener("click", () => {
      panelCollapsed = false;
      panel.classList.remove("collapsed");
      expandTab.classList.remove("visible");
    });
    document.body.appendChild(expandTab);
  }
  const collapseBtn = document.createElement("span");
  collapseBtn.className = "layer-collapse-btn";
  collapseBtn.textContent = "\u25C0";
  collapseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    panelCollapsed = true;
    panel.classList.add("collapsed");
    expandTab.classList.add("visible");
  });
  header.appendChild(headerTitle);
  header.appendChild(collapseBtn);
  panel.appendChild(header);
  const content = document.createElement("div");
  content.className = "layer-panel-content";
  const objGroupRow = document.createElement("div");
  objGroupRow.className = "layer-group-header";
  const objChevron = document.createElement("span");
  objChevron.className = "layer-chevron";
  objChevron.textContent = objectTypesExpanded ? "\u25BE" : "\u25B8";
  const objSwatch = document.createElement("span");
  objSwatch.className = "layer-swatch";
  objSwatch.style.background = "linear-gradient(135deg, #5a8a3a 50%, #c05030 50%)";
  const objLabel = document.createElement("span");
  objLabel.className = "layer-group-name";
  objLabel.textContent = "Objects";
  objGroupRow.appendChild(objChevron);
  objGroupRow.appendChild(objSwatch);
  objGroupRow.appendChild(objLabel);
  const objectRows = /* @__PURE__ */ new Map();
  function updateObjGroupVisual() {
    const allVis = OBJECT_TYPE_IDS.every((id) => editor.isLayerVisible(id));
    const allHid = OBJECT_TYPE_IDS.every((id) => !editor.isLayerVisible(id));
    objGroupRow.style.opacity = allVis ? "1" : allHid ? "0.3" : "0.6";
  }
  const objChildContainer = document.createElement("div");
  objChildContainer.className = "layer-group-children";
  if (!objectTypesExpanded) {
    objChildContainer.style.maxHeight = "0";
  }
  objChevron.addEventListener("click", (e) => {
    e.stopPropagation();
    if (objectTypesExpanded) {
      objectTypesExpanded = false;
      objChevron.textContent = "\u25B8";
      objChildContainer.style.maxHeight = objChildContainer.scrollHeight + "px";
      requestAnimationFrame(() => {
        objChildContainer.style.maxHeight = "0";
      });
    } else {
      objectTypesExpanded = true;
      objChevron.textContent = "\u25BE";
      objChildContainer.style.maxHeight = objChildContainer.scrollHeight + "px";
      const onEnd = () => {
        objChildContainer.style.maxHeight = "";
        objChildContainer.removeEventListener("transitionend", onEnd);
      };
      objChildContainer.addEventListener("transitionend", onEnd);
    }
  });
  const updateTextShapesGroupVisual = (row) => {
    const allVis = TEXT_SHAPES_FILTER_IDS.every((id) => editor.isLayerVisible(id));
    const allHid = TEXT_SHAPES_FILTER_IDS.every((id) => !editor.isLayerVisible(id));
    row.style.opacity = allVis ? "1" : allHid ? "0.3" : "0.6";
  };
  const updateObjectRows = (textShapesGroupRow2) => {
    for (const [id, row] of objectRows.entries()) {
      updateRowVisual(row, editor.isLayerVisible(id));
    }
    updateTextShapesGroupVisual(textShapesGroupRow2);
    updateObjGroupVisual();
  };
  objGroupRow.addEventListener("click", () => {
    const allVis = OBJECT_TYPE_IDS.every((id) => editor.isLayerVisible(id));
    editor.setLayersVisible([...OBJECT_TYPE_IDS], !allVis);
    updateObjectRows(textShapesGroupRow);
  });
  for (const objType of OBJECT_ROOT_FILTERS) {
    const row = document.createElement("div");
    row.className = "layer-row";
    const swatch = document.createElement("span");
    swatch.className = "layer-swatch";
    swatch.style.background = objType.color;
    const label = document.createElement("span");
    label.textContent = objType.label;
    row.appendChild(swatch);
    row.appendChild(label);
    updateRowVisual(row, editor.isLayerVisible(objType.id));
    row.addEventListener("click", () => {
      const vis = !editor.isLayerVisible(objType.id);
      editor.setLayerVisible(objType.id, vis);
      updateObjectRows(textShapesGroupRow);
    });
    objectRows.set(objType.id, row);
    objChildContainer.appendChild(row);
  }
  const textShapesGroupRow = document.createElement("div");
  textShapesGroupRow.className = "layer-group-header";
  const textShapesChevron = document.createElement("span");
  textShapesChevron.className = "layer-chevron";
  textShapesChevron.textContent = textShapesExpanded ? "\u25BE" : "\u25B8";
  const textShapesSwatch = document.createElement("span");
  textShapesSwatch.className = "layer-swatch";
  textShapesSwatch.style.background = "linear-gradient(135deg, #4a8cad 50%, #356982 50%)";
  const textShapesLabel = document.createElement("span");
  textShapesLabel.className = "layer-group-name";
  textShapesLabel.textContent = "Text & Shapes";
  textShapesGroupRow.appendChild(textShapesChevron);
  textShapesGroupRow.appendChild(textShapesSwatch);
  textShapesGroupRow.appendChild(textShapesLabel);
  const textShapesChildContainer = document.createElement("div");
  textShapesChildContainer.className = "layer-group-children";
  if (!textShapesExpanded) {
    textShapesChildContainer.style.maxHeight = "0";
  }
  textShapesChevron.addEventListener("click", (e) => {
    e.stopPropagation();
    if (textShapesExpanded) {
      textShapesExpanded = false;
      textShapesChevron.textContent = "\u25B8";
      textShapesChildContainer.style.maxHeight = textShapesChildContainer.scrollHeight + "px";
      requestAnimationFrame(() => {
        textShapesChildContainer.style.maxHeight = "0";
      });
    } else {
      textShapesExpanded = true;
      textShapesChevron.textContent = "\u25BE";
      textShapesChildContainer.style.maxHeight = textShapesChildContainer.scrollHeight + "px";
      const onEnd = () => {
        textShapesChildContainer.style.maxHeight = "";
        textShapesChildContainer.removeEventListener("transitionend", onEnd);
      };
      textShapesChildContainer.addEventListener("transitionend", onEnd);
    }
  });
  textShapesGroupRow.addEventListener("click", () => {
    const allVis = TEXT_SHAPES_FILTER_IDS.every((id) => editor.isLayerVisible(id));
    editor.setLayersVisible([...TEXT_SHAPES_FILTER_IDS], !allVis);
    updateObjectRows(textShapesGroupRow);
  });
  for (const objType of TEXT_SHAPES_FILTERS) {
    const row = document.createElement("div");
    row.className = "layer-row";
    const swatch = document.createElement("span");
    swatch.className = "layer-swatch";
    swatch.style.background = objType.color;
    const label = document.createElement("span");
    label.textContent = objType.label;
    row.appendChild(swatch);
    row.appendChild(label);
    row.addEventListener("click", () => {
      const vis = !editor.isLayerVisible(objType.id);
      editor.setLayerVisible(objType.id, vis);
      updateObjectRows(textShapesGroupRow);
    });
    objectRows.set(objType.id, row);
    textShapesChildContainer.appendChild(row);
  }
  objChildContainer.appendChild(textShapesGroupRow);
  objChildContainer.appendChild(textShapesChildContainer);
  updateObjectRows(textShapesGroupRow);
  content.appendChild(objGroupRow);
  content.appendChild(objChildContainer);
  const layers = editor.getLayerModels();
  const layerById = new Map(layers.map((layer) => [layer.id, layer]));
  const { groups, topLevel } = groupLayers(layers);
  for (const group of groups) {
    const childNames = group.layers.map((l) => l.id);
    const isCollapsed = collapsedGroups.has(group.group);
    const groupRow = document.createElement("div");
    groupRow.className = "layer-group-header";
    const chevron = document.createElement("span");
    chevron.className = "layer-chevron";
    chevron.textContent = isCollapsed ? "\u25B8" : "\u25BE";
    const primaryColor = colorToCSS(childNames[0], layerById);
    const swatch = createSwatch(primaryColor);
    const label = document.createElement("span");
    label.className = "layer-group-name";
    label.textContent = group.group;
    groupRow.appendChild(chevron);
    groupRow.appendChild(swatch);
    groupRow.appendChild(label);
    updateGroupVisual(groupRow, childNames);
    groupRow.addEventListener("click", () => {
      const allVisible = childNames.every((l) => editor.isLayerVisible(l));
      editor.setLayersVisible(childNames, !allVisible);
      updateGroupVisual(groupRow, childNames);
      const childContainer2 = groupRow.nextElementSibling;
      if (childContainer2) {
        const rows = childContainer2.querySelectorAll(".layer-row");
        rows.forEach((row, i) => {
          updateRowVisual(row, editor.isLayerVisible(childNames[i]));
        });
      }
    });
    chevron.addEventListener("click", (e) => {
      e.stopPropagation();
      const childContainer2 = groupRow.nextElementSibling;
      if (!childContainer2)
        return;
      if (collapsedGroups.has(group.group)) {
        collapsedGroups.delete(group.group);
        chevron.textContent = "\u25BE";
        childContainer2.style.maxHeight = childContainer2.scrollHeight + "px";
        const onEnd = () => {
          childContainer2.style.maxHeight = "";
          childContainer2.removeEventListener("transitionend", onEnd);
        };
        childContainer2.addEventListener("transitionend", onEnd);
      } else {
        collapsedGroups.add(group.group);
        chevron.textContent = "\u25B8";
        childContainer2.style.maxHeight = childContainer2.scrollHeight + "px";
        requestAnimationFrame(() => {
          childContainer2.style.maxHeight = "0";
        });
      }
    });
    content.appendChild(groupRow);
    const childContainer = document.createElement("div");
    childContainer.className = "layer-group-children";
    if (isCollapsed) {
      childContainer.style.maxHeight = "0";
    }
    for (const child of group.layers) {
      const row = document.createElement("div");
      row.className = "layer-row";
      const childSwatch = createSwatch(colorToCSS(child.id, layerById));
      const childLabel = document.createElement("span");
      childLabel.textContent = child.label ?? child.id;
      row.appendChild(childSwatch);
      row.appendChild(childLabel);
      updateRowVisual(row, editor.isLayerVisible(child.id));
      row.addEventListener("click", () => {
        const vis = !editor.isLayerVisible(child.id);
        editor.setLayerVisible(child.id, vis);
        updateRowVisual(row, vis);
        updateGroupVisual(groupRow, childNames);
      });
      childContainer.appendChild(row);
    }
    content.appendChild(childContainer);
  }
  for (const layer of topLevel) {
    const row = document.createElement("div");
    row.className = "layer-row layer-top-level";
    const swatch = createSwatch(colorToCSS(layer.id, layerById));
    const label = document.createElement("span");
    label.textContent = layer.label ?? layer.id;
    row.appendChild(swatch);
    row.appendChild(label);
    updateRowVisual(row, editor.isLayerVisible(layer.id));
    row.addEventListener("click", () => {
      const vis = !editor.isLayerVisible(layer.id);
      editor.setLayerVisible(layer.id, vis);
      updateRowVisual(row, vis);
    });
    content.appendChild(row);
  }
  panel.appendChild(content);
  if (panelCollapsed) {
    panel.classList.add("collapsed");
    expandTab.classList.add("visible");
  }
}
var coordsEl = document.getElementById("status-coords");
var busyEl = document.getElementById("status-busy");
var helpEl = document.getElementById("status-help");
var helpText = "Scroll zoom \xB7 Middle-click pan \xB7 Click group/select \xB7 Shift+drag box-select \xB7 Double-click single \xB7 Esc clear \xB7 R rotate \xB7 F flip \xB7 Ctrl+Z undo \xB7 Ctrl+Shift+Z redo";
if (helpEl)
  helpEl.textContent = helpText;
canvas.addEventListener("mouseenter", () => {
  if (coordsEl)
    coordsEl.dataset.hover = "1";
});
canvas.addEventListener("mouseleave", () => {
  if (coordsEl) {
    delete coordsEl.dataset.hover;
    coordsEl.textContent = "";
  }
});
editor.setOnMouseMove((x, y) => {
  if (coordsEl && coordsEl.dataset.hover) {
    coordsEl.textContent = `X: ${x.toFixed(2)}  Y: ${y.toFixed(2)}`;
  }
});
editor.setOnActionBusyChanged((busy) => {
  if (!busyEl)
    return;
  busyEl.classList.toggle("visible", busy);
  busyEl.setAttribute("aria-hidden", busy ? "false" : "true");
});
setInitialLoading("Loading PCB", "Building scene geometry...");
editor.init().then(() => {
  buildLayerPanel();
  editor.setOnLayersChanged(buildLayerPanel);
  hideInitialLoading();
}).catch((err) => {
  showInitialLoadingError("Load failed", "Could not initialize PCB viewer.");
  console.error("Failed to initialize editor:", err);
});
{
  const fpsEl = document.getElementById("status-fps");
  if (fpsEl) {
    let frames = 0;
    let lastTime = performance.now();
    const tick = () => {
      frames++;
      const now = performance.now();
      if (now - lastTime >= 1e3) {
        fpsEl.textContent = `${frames} fps`;
        frames = 0;
        lastTime = now;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
}
//# sourceMappingURL=editor.js.map

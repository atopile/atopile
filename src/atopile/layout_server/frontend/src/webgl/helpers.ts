/** Shader uniform wrapper */
class Uniform {
    constructor(
        public gl: WebGL2RenderingContext,
        public name: string,
        public location: WebGLUniformLocation,
    ) {}

    f1(x: number) { this.gl.uniform1f(this.location, x); }
    f4(x: number, y: number, z: number, w: number) { this.gl.uniform4f(this.location, x, y, z, w); }
    mat3f(transpose: boolean, data: Float32Array) {
        this.gl.uniformMatrix3fv(this.location, transpose, data);
    }
}

/** Compiled shader program */
export class ShaderProgram {
    program: WebGLProgram;
    uniforms: Record<string, Uniform> = {};
    attribs: Record<string, number> = {};

    constructor(
        public gl: WebGL2RenderingContext,
        vert_src: string,
        frag_src: string,
    ) {
        const vert = ShaderProgram.compile(gl, gl.VERTEX_SHADER, vert_src);
        const frag = ShaderProgram.compile(gl, gl.FRAGMENT_SHADER, frag_src);
        this.program = ShaderProgram.link(gl, vert, frag);
        this.#discover_uniforms();
        this.#discover_attribs();
    }

    static compile(gl: WebGL2RenderingContext, type: GLenum, src: string): WebGLShader {
        const shader = gl.createShader(type)!;
        gl.shaderSource(shader, src);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            const info = gl.getShaderInfoLog(shader);
            gl.deleteShader(shader);
            throw new Error(`Shader compile error: ${info}`);
        }
        return shader;
    }

    static link(gl: WebGL2RenderingContext, vert: WebGLShader, frag: WebGLShader): WebGLProgram {
        const prog = gl.createProgram()!;
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
            const info = this.gl.getActiveUniform(this.program, i)!;
            const loc = this.gl.getUniformLocation(this.program, info.name)!;
            this.uniforms[info.name] = new Uniform(this.gl, info.name, loc);
        }
    }

    #discover_attribs() {
        const count = this.gl.getProgramParameter(this.program, this.gl.ACTIVE_ATTRIBUTES);
        for (let i = 0; i < count; i++) {
            const info = this.gl.getActiveAttrib(this.program, i)!;
            this.attribs[info.name] = this.gl.getAttribLocation(this.program, info.name);
        }
    }

    bind() { this.gl.useProgram(this.program); }
}

/** GPU buffer */
export class Buffer {
    #buf: WebGLBuffer;
    target: GLenum;

    constructor(public gl: WebGL2RenderingContext, target?: GLenum) {
        this.target = target ?? gl.ARRAY_BUFFER;
        this.#buf = gl.createBuffer()!;
    }

    dispose() { this.gl.deleteBuffer(this.#buf); }
    bind() { this.gl.bindBuffer(this.target, this.#buf); }

    set(data: Float32Array, usage?: GLenum) {
        this.bind();
        this.gl.bufferData(this.target, data, usage ?? this.gl.STATIC_DRAW);
    }
}

/** Vertex Array Object */
export class VertexArray {
    vao: WebGLVertexArrayObject;
    buffers: Buffer[] = [];

    constructor(public gl: WebGL2RenderingContext) {
        this.vao = gl.createVertexArray()!;
        this.bind();
    }

    dispose() {
        this.gl.deleteVertexArray(this.vao);
        for (const buf of this.buffers) buf.dispose();
    }

    bind() { this.gl.bindVertexArray(this.vao); }

    buffer(attrib: number, size: number): Buffer {
        const b = new Buffer(this.gl);
        b.bind();
        this.gl.vertexAttribPointer(attrib, size, this.gl.FLOAT, false, 0, 0);
        this.gl.enableVertexAttribArray(attrib);
        this.buffers.push(b);
        return b;
    }
}

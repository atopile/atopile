export const polygon_vert = `#version 300 es
uniform mat3 u_matrix;
in vec2 a_position;
in vec4 a_color;
out vec4 v_color;
void main() {
    v_color = a_color;
    gl_Position = vec4((u_matrix * vec3(a_position, 1)).xy, 0, 1);
}`;

export const polygon_frag = `#version 300 es
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

export const polyline_vert = `#version 300 es
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

export const polyline_frag = `#version 300 es
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

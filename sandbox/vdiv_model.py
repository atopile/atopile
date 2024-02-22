from atopile.parse import parser, parse_text_as_file

vdiv_model = """
component Resistor:
    value = "UNKNOWN"
    pin 1
    pin 2

module VDiv:
    v_out = "UNKNOWN"
    v_in = "UNKNOWN"
    q_current = "UNKNOWN"
    r_total = "UNKNOWN"
    ratio = "UNKNOWN"

    equations = "v_out == v_in * (r_top.value / (r_bottom.value + r_top.value)); q_current == v_in / (r_bottom.value + r_bottom.value); r_total == r_bottom.value + r_bottom.value; ratio == r_bottom.value / (r_bottom.value + r_bottom.value)"

    signal top
    signal out
    signal bottom

    r_top = new Resistor
    r_bottom = new Resistor

module Root:
    vdiv = new VDiv

    vdiv.v_in = 10
    vdiv.v_out = 5
    vdiv.q_current = 1
"""

parser.cache["dummy"] = parse_text_as_file(vdiv_model)

ROOT = "dummy::Root"

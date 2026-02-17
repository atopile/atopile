import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core import graph
from faebryk.exporters.simulation.ngspice import pulse

# --- Set up graph ---
g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)

req_type = F.Requirement.bind_typegraph(tg)

req1 = req_type.create_instance(g=g).setup(
    name="REQ-001: Output DC bias",
    net="output",
    min_val=7.3,
    typical=7.5,
    max_val=7.7,
    capture=F.Captures.DCOPCapture,
    measurement=F.Measurements.FinalValue,
    justification="Resistor divider primary function is to divide voltage.",
)

req2 = req_type.create_instance(g=g).setup(
    name="REQ-002: Supply current",
    net="i(v1)",
    min_val=-500e-6,
    typical=-250e-6,
    max_val=0,
    capture=F.Captures.DCOPCapture,
    measurement=F.Measurements.FinalValue,
    justification="Power budget for shared 10V rail (SPICE sign: negative = into circuit)",
)

req3 = req_type.create_instance(g=g).setup(
    name="REQ-003: Transient final value",
    net="output",
    min_val=7.45,
    typical=7.5,
    max_val=7.55,
    capture=F.Captures.TransientCapture,
    measurement=F.Measurements.FinalValue,
    context_nets=["power_hv"],
    tran_step=1e-4,
    tran_stop=1.0,
    source_override=("V1", pulse(0, 10)),
    justification="Output converges to DC steady-state",
)

req4 = req_type.create_instance(g=g).setup(
    name="REQ-004: Settling time",
    net="output",
    min_val=0.2,
    typical=0.3,
    max_val=0.4,
    capture=F.Captures.TransientCapture,
    measurement=F.Measurements.SettlingTime,
    context_nets=["power_hv"],
    tran_step=1e-4,
    tran_stop=0.5,
    source_override=("V1", pulse(0, 10)),
    justification="Output converges to DC steady-state",
)

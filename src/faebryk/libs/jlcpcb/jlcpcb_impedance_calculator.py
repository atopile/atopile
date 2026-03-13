"""JLCPCB impedance calculator API client.

API endpoint: https://jlcpcb.com/api/jlcTools/impedance/calc
"""

import uuid
from dataclasses import dataclass
from enum import Enum

import httpx

IMPEDANCE_CALC_API_URL = "https://jlcpcb.com/api/jlcTools/impedance/calc"


class CalcMode(Enum):
    """dCalculateMode values for the impedance calc API."""

    FORWARD = 1  # given trace width, compute impedance
    BACK_CALC = 3  # given target impedance, compute trace width


class CalcMark(Enum):
    """impedance_calc_mark values — trace structure types.

    Naming convention: W2 = solve for W2 (back-calc trace width).
    """

    # Single-ended
    MICROSTRIP = "W2_CoatedMicrostrip1B"
    STRIPLINE = "W2_Stripline1B"
    # Single-ended coplanar
    COPLANAR_MICROSTRIP = "W2_CoatedCoplanarWaveguide1B"
    COPLANAR_STRIPLINE = "W2_CoplanarWaveguide1B"
    # Differential edge-coupled
    DIFF_MICROSTRIP = "W2_CoatedEdgeCoupledMicrostrip1B"
    DIFF_STRIPLINE = "W2_EdgeCoupledStripline1B2A"
    # Differential coplanar
    DIFF_COPLANAR_MICROSTRIP = "W2_CoatedEdgeCoupledCoplanarWaveguide1B"
    DIFF_COPLANAR_STRIPLINE = "W2_EdgeCoupledCoplanarWaveguide1B"


@dataclass(frozen=True)
class ImpedanceCalcRequest:
    """Request body for the impedance calc API.

    All dimensions are in mils unless noted.

    Parameters
    ----------
    calc_mark : CalcMark
        Trace structure type.
    H1 : float
        Dielectric height (mils) between signal layer and reference plane.
    Er1 : float
        Relative permittivity of the dielectric (H1).
    W1 : float
        Trace base width (mils).
    W2 : float
        Trace top width (mils). Typically W1 - 0.7.
    T1 : float
        Copper thickness (mils).
    C1 : float
        Solder mask thickness between traces (mils). Outer layers only.
    C2 : float
        Solder mask thickness over copper (mils). Outer layers only.
    CEr : float
        Solder mask relative permittivity.
    Zo : float
        Target impedance (ohms). Used with back-calc mode.
    calc_mode : CalcMode
        Forward (compute Z) or back-calc (compute W).
    S1 : float | None
        Trace spacing (mils). Differential pairs only.
    G1 : float | None
        Conductor-to-coplanar-ground gap (mils). Coplanar types only.
    H2 : float | None
        Second dielectric height (mils). Stripline (below signal) only.
    Er2 : float | None
        Relative permittivity of second dielectric. Stripline only.
    """

    calc_mark: CalcMark
    H1: float
    Er1: float
    W1: float
    W2: float
    T1: float
    Zo: float
    calc_mode: CalcMode = CalcMode.BACK_CALC
    C1: float = 0.0
    C2: float = 0.0
    CEr: float = 0.0
    S1: float | None = None
    G1: float | None = None
    H2: float | None = None
    Er2: float | None = None

    def to_api_dict(self) -> dict:
        """Build the impedance_calc_arg dict for the API request body."""
        arg: dict = {
            "H1": self.H1,
            "Er1": self.Er1,
            "W1": self.W1,
            "W2": self.W2,
            "T1": self.T1,
            "Zo": self.Zo,
            "dCalculateMode": self.calc_mode.value,
            "MinW2": 2,
            "MaxW2": 200,
        }
        if self.C1 or self.C2:
            arg["C1"] = self.C1
            arg["C2"] = self.C2
            arg["CEr"] = self.CEr
        if self.S1 is not None:
            arg["S1"] = self.S1
        if self.G1 is not None:
            arg["G1"] = self.G1
        if self.H2 is not None:
            arg["H2"] = self.H2
        if self.Er2 is not None:
            arg["Er2"] = self.Er2
        return arg


@dataclass(frozen=True)
class ImpedanceCalcResult:
    """Parsed response from the impedance calc API."""

    impedance_ohm: float
    effective_er: float
    capacitance_pf_per_m: float
    inductance_nh_per_m: float
    delay_ps_per_m: float
    back_calc_w1: float | None  # trace base width (back-calc result)
    back_calc_w2: float | None  # trace top width (back-calc result)
    valid: bool

    @classmethod
    def from_api_response(cls, body: dict) -> "ImpedanceCalcResult":
        """Parse the API response body into an ImpedanceCalcResult."""
        r = body["impedance_calc_result"]
        back = r.get("jBackCalc") or {}
        return cls(
            impedance_ohm=r["dImpedance"],
            effective_er=r["dErEff"],
            capacitance_pf_per_m=r["dCer"],
            inductance_nh_per_m=r["dInductance"],
            delay_ps_per_m=r["dDelay"],
            back_calc_w1=back.get("W1"),
            back_calc_w2=back.get("W2"),
            valid=r.get("dResultValid", 0) == 1,
        )


def calculate(
    req: ImpedanceCalcRequest,
    *,
    client: httpx.Client | None = None,
) -> ImpedanceCalcResult:
    """Call the JLCPCB impedance calculator API and return parsed results."""
    payload = {
        "accessId": str(uuid.uuid4()),
        "impedance_calc_mark": req.calc_mark.value,
        "paramMd5": "",
        "impedance_calc_arg": req.to_api_dict(),
        "uuid": str(uuid.uuid4()),
    }

    if client is None:
        with httpx.Client(timeout=30) as c:
            resp = c.post(IMPEDANCE_CALC_API_URL, json=payload)
    else:
        resp = client.post(IMPEDANCE_CALC_API_URL, json=payload)

    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        msg = data.get("message") or "Unknown error"
        raise RuntimeError(f"JLCPCB impedance calc failed: {msg}")

    return ImpedanceCalcResult.from_api_response(data["body"])

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

from faebryk.core.module import Module


class has_designator_prefix(Module.TraitT.decless()):
    class Prefix(StrEnum):
        A = "A"
        """Separable assembly or sub-assembly (e.g. printed circuit assembly)"""

        AT = "AT"
        """Attenuator or isolator"""

        BR = "BR"
        """
        Bridge rectifier (four diodes in a package) > often changed to "D" for diode
        """

        B = "B"
        """Often shortened to "B" for Battery or battery holder"""

        BT = "BT"
        """Battery or battery holder > often shortened to "B" """

        BAT = "BAT"
        """Battery or battery holder > often shortened to "B" """

        C = "C"
        """Capacitor"""

        CB = "CB"
        """Circuit breaker"""

        CN = "CN"
        """Capacitor network > may be simplified to "C" for capacitor"""

        D = "D"
        """
        Diode (all types, including LED), thyristor > "D" is preferred for various types
        of diodes
        """

        CR = "CR"
        """
        Diode (all types, including LED), thyristor > "D" is preferred for various types
        of diodes
        """

        DL = "DL"
        """Delay line"""

        DN = "DN"
        """Diode network > may be simplified to "D" for diode"""

        DS = "DS"
        """Display, general light source, lamp, signal light"""

        F = "F"
        """Fuse"""

        FB = "FB"
        """Ferrite bead > sometimes changed to "L" for inductor, though "E" was used in
        the currently inactive standard IEEE 315 (see Clause 22.4)"""

        L = "L"
        """Inductor or coil or ferrite bead > sometimes changed from "FB" for ferrite
        bead"""

        FD = "FD"
        """Fiducial"""

        FL = "FL"
        """Filter"""

        G = "G"
        """Generator or oscillator"""

        GDT = "GDT"
        """Gas discharge tube"""

        OSC = "OSC"
        """Generator or oscillator"""

        GL = "GL"
        """Graphical logo"""

        GN = "GN"
        """General network"""

        H = "H"
        """Hardware, e.g., screws, nuts, washers, also used for drilled holes >
        sometimes hardware is expanded to "HW" """

        HW = "HW"
        """Expanded form of "H" for hardware"""

        HY = "HY"
        """Circulator or directional coupler"""

        IR = "IR"
        """Infrared diode > often changed to "D" for diode"""

        J = "J"
        """Jack (least-movable connector of a connector pair), jack connector (connector
        may have "male" pin contacts and/or "female" socket contacts) > all types of
        connectors, including pin headers."""

        JP = "JP"
        """Jumper (link)"""

        K = "K"
        """Relay or contactor"""

        LD = "LD"
        """LED > often changed to "D" for diode"""

        LED = "LED"
        """LED > often changed to "D" for diode"""

        LS = "LS"
        """Loudspeaker or buzzer"""

        SPK = "SPK"
        """Loudspeaker or buzzer"""

        M = "M"
        """Motor"""

        MK = "MK"
        """Microphone"""

        MIC = "MIC"
        """Microphone"""

        MOD = "MOD"
        """Module"""

        MP = "MP"
        """Mechanical part (including screws and fasteners)"""

        OP = "OP"
        """Opto-isolator > often changed to "U" for IC"""

        U = "U"
        """Shorter form of "U" (unit) preferred for Integrated Circuit instead of "IC"
        """

        IC = "IC"
        """Integrated circuit (IC) > often shortened to "U" """

        P = "P"
        """Plug (most-movable connector of a connector pair), plug connector (connector
        may have "male" pin contacts and/or "female" socket contacts)"""

        PS = "PS"
        """Power supply"""

        Q = "Q"
        """Transistor (all types)"""

        R = "R"
        """Resistor"""

        RN = "RN"
        """Resistor network > sometimes simplified to "R" for resistor, or "N" for
        network"""

        N = "N"
        """Often used for networks, sometimes simplified from resistor network "RN" """

        RT = "RT"
        """Thermistor > sometimes simplified to "R" for resistor"""

        RV = "RV"
        """Varistor, variable resistor"""

        S = "S"
        """Switch (all types, including buttons) > sometimes "SW" is erroneously used"""

        SW = "SW"
        """Sometimes erroneously used for Switch instead of "S" """

        SA = "SA"
        """Spark arrester"""

        T = "T"
        """Transistor > often changed to "Q", but sometimes "T" is used for bipolar
        transistors and "Q" for FETs."""

        TC = "TC"
        """Thermocouple"""

        TP = "TP"
        """Test point"""

        TR = "TR"
        """Transformer > sometimes changed to "L" for inductor"""

        TUN = "TUN"
        """Tuner"""

        V = "V"
        """Vacuum tube"""

        VR = "VR"
        """Voltage regulator (voltage reference), or variable resistor (potentiometer /
        trimmer / rheostat) > voltage regulators are often "U" for IC, pots and trimmers
        often "R" for resistor"""

        X = "X"
        """Socket connector for another item not P or J, paired with the letter symbol
        for that item (XV for vacuum tube socket, XF for fuse holder, XA for printed
        circuit assembly connector, XU for integrated circuit connector, XDS for light
        socket, etc.)"""

        XTAL = "XTAL"
        """Crystal, ceramic resonator, powered oscillator"""

        Y = "Y"
        """Crystal, ceramic resonator, powered oscillator"""

        ZD = "ZD"
        """Zener diode > often changed to "D" for diode"""

    def __init__(self, prefix: str | Prefix) -> None:
        super().__init__()
        self.prefix = prefix

    def get_prefix(self) -> str:
        return self.prefix

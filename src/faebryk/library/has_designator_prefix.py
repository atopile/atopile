# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import StrEnum, auto

from faebryk.core.module import Module


class has_designator_prefix(Module.TraitT):
    class Prefix(StrEnum):
        A = auto()
        """Separable assembly or sub-assembly (e.g. printed circuit assembly)"""
        AT = auto()
        """Attenuator or isolator"""
        BR = auto()
        """
        Bridge rectifier (four diodes in a package) > often changed to "D" for diode
        """
        B = auto()
        """Often shortened to "B" for Battery or battery holder"""
        BT = auto()
        """Battery or battery holder > often shortened to "B" """
        BAT = auto()
        """Battery or battery holder > often shortened to "B" """
        C = auto()
        """Capacitor"""
        CB = auto()
        """Circuit breaker"""
        CN = auto()
        """Capacitor network > may be simplified to "C" for capacitor"""
        D = auto()
        """
        Diode (all types, including LED), thyristor > "D" is preferred for various types
        of diodes
        """
        CR = auto()
        """
        Diode (all types, including LED), thyristor > "D" is preferred for various types
        of diodes
        """
        DL = auto()
        """Delay line"""
        DN = auto()
        """Diode network > may be simplified to "D" for diode"""
        DS = auto()
        """Display, general light source, lamp, signal light"""
        F = auto()
        """Fuse"""
        FB = auto()
        """Ferrite bead > sometimes changed to "L" for inductor, though "E" was used in
        the currently inactive standard IEEE 315 (see Clause 22.4)"""
        L = auto()
        """Inductor or coil or ferrite bead > sometimes changed from "FB" for ferrite
        bead"""
        FD = auto()
        """Fiducial"""
        FL = auto()
        """Filter"""
        G = auto()
        """Generator or oscillator"""
        OSC = auto()
        """Generator or oscillator"""
        GL = auto()
        """Graphical logo"""
        GN = auto()
        """General network"""
        H = auto()
        """Hardware, e.g., screws, nuts, washers, also used for drilled holes >
        sometimes hardware is expanded to "HW" """
        HW = auto()
        """Expanded form of "H" for hardware"""
        HY = auto()
        """Circulator or directional coupler"""
        IR = auto()
        """Infrared diode > often changed to "D" for diode"""
        J = auto()
        """Jack (least-movable connector of a connector pair), jack connector (connector
        may have "male" pin contacts and/or "female" socket contacts) > all types of
        connectors, including pin headers."""
        JP = auto()
        """Jumper (link)"""
        K = auto()
        """Relay or contactor"""
        LD = auto()
        """LED > often changed to "D" for diode"""
        LED = auto()
        """LED > often changed to "D" for diode"""
        LS = auto()
        """Loudspeaker or buzzer"""
        SPK = auto()
        """Loudspeaker or buzzer"""
        M = auto()
        """Motor"""
        MK = auto()
        """Microphone"""
        MIC = auto()
        """Microphone"""
        MP = auto()
        """Mechanical part (including screws and fasteners)"""
        OP = auto()
        """Opto-isolator > often changed to "U" for IC"""
        U = auto()
        """Shorter form of "U" (unit) preferred for Integrated Circuit instead of "IC"
        """
        IC = auto()
        """Integrated circuit (IC) > often shortened to "U" """
        P = auto()
        """Plug (most-movable connector of a connector pair), plug connector (connector
        may have "male" pin contacts and/or "female" socket contacts)"""
        PS = auto()
        """Power supply"""
        Q = auto()
        """Transistor (all types)"""
        R = auto()
        """Resistor"""
        RN = auto()
        """Resistor network > sometimes simplified to "R" for resistor, or "N" for
        network"""
        N = auto()
        """Often used for networks, sometimes simplified from resistor network "RN" """
        RT = auto()
        """Thermistor > sometimes simplified to "R" for resistor"""
        RV = auto()
        """Varistor, variable resistor"""
        S = auto()
        """Switch (all types, including buttons) > sometimes "SW" is erroneously used"""
        SW = auto()
        """Sometimes erroneously used for Switch instead of "S" """
        SA = auto()
        """Spark arrester"""
        T = auto()
        """Transistor > often changed to "Q", but sometimes "T" is used for bipolar
        transistors and "Q" for FETs."""
        TC = auto()
        """Thermocouple"""
        TP = auto()
        """Test point"""
        TR = auto()
        """Transformer > sometimes changed to "L" for inductor"""
        TUN = auto()
        """Tuner"""
        V = auto()
        """Vacuum tube"""
        VR = auto()
        """Voltage regulator (voltage reference), or variable resistor (potentiometer /
        trimmer / rheostat) > voltage regulators are often "U" for IC, pots and trimmers
        often "R" for resistor"""
        X = auto()
        """Socket connector for another item not P or J, paired with the letter symbol
        for that item (XV for vacuum tube socket, XF for fuse holder, XA for printed
        circuit assembly connector, XU for integrated circuit connector, XDS for light
        socket, etc.)"""
        XTAL = auto()
        """Crystal, ceramic resonator, powered oscillator"""
        Y = auto()
        """Crystal, ceramic resonator, powered oscillator"""
        ZD = auto()
        """Zener diode > often changed to "D" for diode"""

    @abstractmethod
    def get_prefix(self) -> str: ...

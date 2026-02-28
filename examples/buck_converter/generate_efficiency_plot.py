#!/usr/bin/env python3
"""
TPS54560 Design Validation — Efficiency vs Load Current Plot

Generates an analytical efficiency estimate for the TPS54560 buck converter
across multiple input voltages and switching frequencies.

Color  = switching frequency (4 values)
Marker = input voltage (4 values)

Estimated component parameters (proof of concept):
- FET Rdson: 92 mOhm (TPS54560 high-side MOSFET, from datasheet)
- Diode Vf: 0.4V (STPS340U Schottky)
- Inductor DCR: 20 mOhm
- Switching time (tr+tf): 20 ns
- Quiescent current: 146 uA
- Gate charge Qg: 15 nC

Usage:
    python generate_efficiency_plot.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pathlib import Path

# --- Circuit Parameters (estimated) ---
VOUT = 5.0          # Output voltage [V]
RDSON = 92e-3       # High-side FET on-resistance [Ohm]
VF_DIODE = 0.4      # Schottky diode forward voltage [V]
R_DCR = 20e-3       # Inductor DC resistance [Ohm]
TR_TF = 20e-9       # Total switching transition time [s]
IQ = 146e-6         # Quiescent current [A]
QG = 15e-9          # Gate charge [C]
VGS = 5.0           # Gate drive voltage [V]
L_IND = 6.8e-6      # Inductance [H]

# --- Sweep Configuration ---
VIN_VALUES = [12, 24, 36, 48]                       # Input voltages [V]
FSW_VALUES = [200e3, 400e3, 600e3, 1000e3]          # Switching frequencies [Hz]
ILOAD = np.array([0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0])
ILOAD_FINE = np.linspace(0.01, 5.0, 200)


def compute_efficiency(vin: float, fsw: float, iload: np.ndarray) -> dict:
    """Compute efficiency and loss breakdown for given VIN, FSW, and load currents."""
    D = VOUT / vin

    p_out = VOUT * iload

    # Conduction losses
    p_fet = iload**2 * RDSON * D
    p_diode = iload * VF_DIODE * (1 - D)
    p_inductor = iload**2 * R_DCR

    # Switching losses (scale with fsw)
    p_sw = vin * iload * TR_TF * fsw / 2
    p_gate = QG * VGS * fsw * np.ones_like(iload)
    p_quiescent = vin * IQ * np.ones_like(iload)

    p_loss = p_fet + p_diode + p_inductor + p_sw + p_gate + p_quiescent
    p_in = p_out + p_loss
    eff = np.where(p_in > 0, (p_out / p_in) * 100, 0)

    return {
        "eff": eff,
        "p_out": p_out,
        "p_in": p_in,
        "p_loss": p_loss,
        "p_fet": p_fet,
        "p_diode": p_diode,
        "p_inductor": p_inductor,
        "p_sw": p_sw + p_gate + p_quiescent,
        "duty": D,
    }


def main():
    # --- Visual encoding ---
    # Color = switching frequency
    fsw_colors = {
        200e3: "#2196F3",   # blue
        400e3: "#4CAF50",   # green
        600e3: "#FF9800",   # orange
        1000e3: "#F44336",  # red
    }
    fsw_labels = {
        200e3: "200 kHz",
        400e3: "400 kHz",
        600e3: "600 kHz",
        1000e3: "1 MHz",
    }

    # Marker = input voltage
    vin_markers = {12: "o", 24: "s", 36: "D", 48: "^"}

    fig = plt.figure(figsize=(20, 14))
    fig.suptitle(
        "TPS54560 Design Validation — Efficiency vs Load Current\n"
        f"(Vout={VOUT}V, Rdson={RDSON*1e3:.0f}m\u03A9, "
        f"Vf={VF_DIODE}V, L={L_IND*1e6:.1f}\u00B5H, DCR={R_DCR*1e3:.0f}m\u03A9)",
        fontsize=14, fontweight="bold", y=0.98,
    )

    # =====================================================================
    # Panel 1: Efficiency vs Load — color=Fsw, marker=VIN
    # =====================================================================
    ax1 = fig.add_subplot(2, 2, 1)

    for fsw in FSW_VALUES:
        color = fsw_colors[fsw]
        for vin in VIN_VALUES:
            mkr = vin_markers[vin]
            # Smooth curve
            res_fine = compute_efficiency(vin, fsw, ILOAD_FINE)
            ax1.plot(
                ILOAD_FINE, res_fine["eff"],
                color=color, linewidth=1.3, alpha=0.6,
            )
            # Discrete markers at sweep points
            res_pts = compute_efficiency(vin, fsw, ILOAD)
            ax1.plot(
                ILOAD, res_pts["eff"],
                marker=mkr, color=color,
                linestyle="none", markersize=7, zorder=5,
                markeredgecolor=color, markerfacecolor=color, alpha=0.85,
            )

    ax1.set_xlabel("Load Current [A]", fontsize=11)
    ax1.set_ylabel("Efficiency [%]", fontsize=11)
    ax1.set_title("Efficiency vs Load Current", fontsize=12, fontweight="bold")
    ax1.set_xlim(0, 5.2)
    ax1.set_ylim(50, 100)
    ax1.grid(True, alpha=0.3)

    # Legend — two groups: color=Fsw, marker=VIN
    fsw_handles = [
        Line2D([0], [0], color=fsw_colors[f], linewidth=2.5,
               label=fsw_labels[f])
        for f in FSW_VALUES
    ]
    vin_handles = [
        Line2D([0], [0], color="#555", marker=vin_markers[v], markersize=7,
               linestyle="none", label=f"VIN={v}V")
        for v in VIN_VALUES
    ]
    # Frequency legend (top-right)
    leg1 = ax1.legend(
        handles=fsw_handles, title="Frequency (color)",
        loc="upper right", fontsize=8, title_fontsize=9,
    )
    ax1.add_artist(leg1)
    # VIN legend (lower-left)
    ax1.legend(
        handles=vin_handles, title="Input Voltage (marker)",
        loc="lower left", fontsize=8, title_fontsize=9,
    )

    # =====================================================================
    # Panel 2: Power Breakdown (VIN=12V, Fsw=400kHz reference)
    # =====================================================================
    ax2 = fig.add_subplot(2, 2, 2)

    res_ref = compute_efficiency(12, 400e3, ILOAD)
    ax2.fill_between(ILOAD, 0, res_ref["p_out"], alpha=0.6, color="#2196F3", label="Output Power")
    ax2.fill_between(ILOAD, res_ref["p_out"], res_ref["p_in"], alpha=0.6, color="#F44336", label="Losses")
    ax2.plot(ILOAD, res_ref["p_in"], "k-", linewidth=2, label="Input Power")

    ax2.set_xlabel("Load Current [A]", fontsize=11)
    ax2.set_ylabel("Power [W]", fontsize=11)
    ax2.set_title("Power Breakdown (VIN=12V, 400kHz)", fontsize=12, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 5.2)

    # =====================================================================
    # Panel 3: Loss Breakdown (stacked bar)
    # =====================================================================
    ax3 = fig.add_subplot(2, 2, 3)

    bar_width = 0.15
    x_pos = np.arange(len(ILOAD))

    bar_vins = [12, 24, 48]
    vin_colors_bar = {12: "#2196F3", 24: "#4CAF50", 48: "#F44336"}
    bar_tops = {}
    for i, vin in enumerate(bar_vins):
        res = compute_efficiency(vin, 400e3, ILOAD)
        offset = (i - 1) * bar_width
        bottom = np.zeros(len(ILOAD))

        ax3.bar(x_pos + offset, res["p_fet"], bar_width,
                bottom=bottom, color=vin_colors_bar[vin], alpha=0.8)
        bottom += res["p_fet"]

        ax3.bar(x_pos + offset, res["p_diode"], bar_width,
                bottom=bottom, color="#9C27B0", alpha=0.4 + 0.2*i)
        bottom += res["p_diode"]

        ax3.bar(x_pos + offset, res["p_sw"], bar_width,
                bottom=bottom, color="#9E9E9E", alpha=0.4 + 0.2*i)
        bar_tops[vin] = bottom + res["p_sw"]

    # VIN labels above bars
    for i, vin in enumerate(bar_vins):
        offset = (i - 1) * bar_width
        for j in range(len(ILOAD)):
            top = bar_tops[vin][j]
            ax3.text(
                x_pos[j] + offset, top + 0.02,
                f"{vin}V",
                ha="center", va="bottom",
                fontsize=6, fontweight="bold", color=vin_colors_bar[vin],
                rotation=90,
            )

    legend_elements = [
        Patch(facecolor="#FF9800", alpha=0.8, label="FET Rdson"),
        Patch(facecolor="#9C27B0", alpha=0.6, label="Diode Vf"),
        Patch(facecolor="#9E9E9E", alpha=0.6, label="Switching + other"),
    ]
    ax3.legend(handles=legend_elements, loc="upper left", fontsize=9)

    ax3.set_xlabel("Load Current [A]", fontsize=11)
    ax3.set_ylabel("Power Loss [W]", fontsize=11)
    ax3.set_title("Loss Breakdown @ 400kHz (Estimated)", fontsize=12, fontweight="bold")
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels([f"{i:.2g}" for i in ILOAD])
    ax3.grid(True, alpha=0.3, axis="y")

    # =====================================================================
    # Panel 4: Efficiency Summary Table (all Fsw x VIN @ 5A)
    # =====================================================================
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis("off")
    ax4.set_title("Efficiency Summary Table", fontsize=12, fontweight="bold", pad=20)

    col_labels = ["Iload\n[A]"] + [
        f"{fsw_labels[f]}\nVIN=" + "/".join(str(v) for v in VIN_VALUES) + "V"
        for f in FSW_VALUES
    ]

    # Rows = load currents, columns = Fsw (show best/worst VIN)
    col_labels2 = ["Iload\n[A]"]
    for f in FSW_VALUES:
        col_labels2.append(f"{fsw_labels[f]}\n12V / 48V")

    table_data = []
    for il in ILOAD:
        row = [f"{il:.2f}"]
        for fsw in FSW_VALUES:
            eff12 = compute_efficiency(12, fsw, np.array([il]))["eff"][0]
            eff48 = compute_efficiency(48, fsw, np.array([il]))["eff"][0]
            row.append(f"{eff12:.1f} / {eff48:.1f}")
        table_data.append(row)

    table = ax4.table(
        cellText=table_data,
        colLabels=col_labels2,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.6)

    # Color-code cells by average of the two efficiencies shown
    for i, row in enumerate(table_data):
        for j in range(1, len(row)):
            vals = row[j].split(" / ")
            avg_eff = (float(vals[0]) + float(vals[1])) / 2
            cell = table[i + 1, j]
            if avg_eff >= 90:
                cell.set_facecolor("#C8E6C9")
            elif avg_eff >= 80:
                cell.set_facecolor("#FFF9C4")
            else:
                cell.set_facecolor("#FFCDD2")

    # Header styling
    for j in range(len(col_labels2)):
        table[0, j].set_facecolor("#E3F2FD")
        table[0, j].set_text_props(fontweight="bold")

    plt.tight_layout(rect=[0, 0, 1, 0.94], w_pad=3)

    # Save
    output_dir = Path(__file__).parent / "plots"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "18_efficiency_vs_load.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Saved: {output_path}")
    plt.close(fig)


if __name__ == "__main__":
    main()

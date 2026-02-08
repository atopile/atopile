#!/usr/bin/env bash
# Batch generate STM32 .ato definitions from open pin data.
# Run from examples/stm_gen/ with the venv active.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
XML_DIR="/Users/narayanpowderly/projects/STM32_open_pin_data/mcu"
GEN="python $SCRIPT_DIR/stm32_gen.py"
PROJECT_DIR="$SCRIPT_DIR"

mkdir -p "$SCRIPT_DIR/generated"

# ── Target MCUs ──────────────────────────────────────────────────────────
# Format: XML_FILE | LCSC_OR_MFR_SEARCH | NOTES
# We pick popular, LCSC-stocked parts across families and packages.

declare -a TARGETS=(
    # --- F0: Tiny, budget, Cortex-M0 ---
    "STM32F030F4Px.xml|STMicroelectronics:STM32F030F4P6|F0 TSSOP20 tiny"

    # --- F1: Classic Cortex-M3 ---
    # Already generated manually (STM32F103C8T6), skip part install
    "STM32F103C(8-B)Tx.xml|SKIP|F1 LQFP48 classic BluePill"

    # --- F4: Popular Cortex-M4F ---
    "STM32F401CCFx.xml|STMicroelectronics:STM32F401CCU6|F4 QFN48 WeAct"
    "STM32F411C(C-E)Ux.xml|STMicroelectronics:STM32F411CEU6|F4 QFN48 BlackPill"
    "STM32F446R(C-E)Tx.xml|STMicroelectronics:STM32F446RET6|F4 LQFP64 high-perf"

    # --- G4: Cortex-M4F, mixed-signal ---
    "STM32G431CBTxZ.xml|STMicroelectronics:STM32G431CBT6|G4 LQFP48"

    # --- L0: Ultra-low-power Cortex-M0+ ---
    "STM32L073RZIx.xml|STMicroelectronics:STM32L073RZT6|L0 LQFP64 low-power"

    # --- L4: Ultra-low-power Cortex-M4 ---
    "STM32L432K(B-C)Ux.xml|STMicroelectronics:STM32L432KCU6|L4 QFN32 small"

    # --- H7: High-performance Cortex-M7 ---
    "STM32H743ZITx.xml|STMicroelectronics:STM32H743ZIT6|H7 LQFP144 big"

    # --- C0: Entry-level Cortex-M0+ ---
    "STM32C031C(4-6)Tx.xml|STMicroelectronics:STM32C031C6T6|C0 LQFP48 entry"
)

SUCCESS=0
FAIL=0
SKIP_PART=0

for target in "${TARGETS[@]}"; do
    IFS='|' read -r xml_file lcsc_search notes <<< "$target"

    echo ""
    echo "=================================================================="
    echo "  $notes"
    echo "  XML: $xml_file"
    echo "=================================================================="

    xml_path="$XML_DIR/$xml_file"
    if [ ! -f "$xml_path" ]; then
        echo "  ERROR: XML not found at $xml_path"
        FAIL=$((FAIL + 1))
        continue
    fi

    extra_args=""
    if [ "$lcsc_search" = "SKIP" ]; then
        extra_args="--skip-part-install"
        SKIP_PART=$((SKIP_PART + 1))
    else
        extra_args="--mfr-search $lcsc_search"
    fi

    output_name=$(echo "$xml_file" | sed 's/\.xml$//' | sed 's/[()]//g' | sed 's/-/_/g' | tr '[:upper:]' '[:lower:]')

    if $GEN "$xml_path" $extra_args -o "$SCRIPT_DIR/generated/${output_name}.ato" -p "$PROJECT_DIR" 2>&1; then
        echo "  SUCCESS"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "  FAILED"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "=================================================================="
echo "  BATCH COMPLETE: $SUCCESS success, $FAIL failed, $SKIP_PART skipped part install"
echo "=================================================================="

from collections.abc import Iterator
from pathlib import Path

import atopile.compiler.types as ct
from faebryk.core.node import Node


def build() -> ct.CompilationUnit:
    # Root compilation unit and file context
    cu = ct.CompilationUnit()
    file = ct.File()
    file.path = Path("examples/esp32_minimal/esp32_minimal.ato")
    cu.add(file)

    top = file.scope

    # Pragmas
    p1 = ct.PragmaStmt("FOR_LOOP")
    p1.add(ct.SourceChunk('#pragma experiment("FOR_LOOP")'))
    top.add(p1)

    # p2 = ct.PragmaStmt()
    # p2.source.text = '#pragma experiment("BRIDGE_CONNECT")'
    # p2.pragma = 'experiment("BRIDGE_CONNECT")'
    # top.add(p2)

    # # Imports (standard library)
    # imp_elec = ct.ImportStmt()
    # imp_elec.source.text = "import ElectricPower"
    # imp_elec.path = Path("")
    # imp_elec.add(ct.TypeRef("ElectricPower"), name="type_ref")
    # top.add(imp_elec)

    # imp_res = ct.ImportStmt()
    # imp_res.source.text = "import Resistor"
    # imp_res.path = Path("")
    # imp_res.add(ct.TypeRef("Resistor"), name="type_ref")
    # top.add(imp_res)

    # # Package imports
    # imp_usb = ct.ImportStmt()
    # imp_usb.source.text = 'from "atopile/usb-connectors/usb-connectors.ato" import USB2_0TypeCHorizontalConnector'
    # imp_usb.path = Path("atopile/usb-connectors/usb-connectors.ato")
    # imp_usb.add(ct.TypeRef("USB2_0TypeCHorizontalConnector"), name="type_ref")
    # top.add(imp_usb)

    # imp_ldo = ct.ImportStmt()
    # imp_ldo.source.text = (
    #     'from "atopile/ti-tlv75901/ti-tlv75901.ato" import TLV75901_driver'
    # )
    # imp_ldo.path = Path("atopile/ti-tlv75901/ti-tlv75901.ato")
    # imp_ldo.add(ct.TypeRef("TLV75901_driver"), name="type_ref")
    # top.add(imp_ldo)

    # imp_esp = ct.ImportStmt()
    # imp_esp.source.text = 'from "atopile/esp32/esp32_s3.ato" import ESP32_S3_WROOM'
    # imp_esp.path = Path("atopile/esp32/esp32_s3.ato")
    # imp_esp.add(ct.TypeRef("ESP32_S3_WROOM"), name="type_ref")
    # top.add(imp_esp)

    # # Module definition
    # mod = ct.BlockDefinition()
    # mod.source.text = "module ESP32_MINIMAL:"
    # top.add(mod)

    # body = mod.scope

    # # new statements
    # s_micro = ct.AssignNewStmt()
    # s_micro.source.text = "micro = new ESP32_S3_WROOM"
    # s_micro.field_ref.add(ct.FieldRefPart("micro"), container=s_micro.field_ref.parts)
    # s_micro.add(ct.TypeRef("ESP32_S3_WROOM"), name="type_ref")
    # s_micro.new_count = None
    # s_micro.template = None
    # body.add(s_micro)

    # s_usb = ct.AssignNewStmt()
    # s_usb.source.text = "usb_c = new USB2_0TypeCHorizontalConnector"
    # s_usb.field_ref.add(ct.FieldRefPart("usb_c"), container=s_usb.field_ref.parts)
    # s_usb.add(ct.TypeRef("USB2_0TypeCHorizontalConnector"), name="type_ref")
    # body.add(s_usb)

    # s_ldo = ct.AssignNewStmt()
    # s_ldo.source.text = "ldo_3V3 = new TLV75901_driver"
    # s_ldo.field_ref.add(ct.FieldRefPart("ldo_3V3"), container=s_ldo.field_ref.parts)
    # s_ldo.add(ct.TypeRef("TLV75901_driver"), name="type_ref")
    # body.add(s_ldo)

    # s_pwr = ct.AssignNewStmt()
    # s_pwr.source.text = "power_3v3 = new ElectricPower"
    # s_pwr.field_ref.add(ct.FieldRefPart("power_3v3"), container=s_pwr.field_ref.parts)
    # s_pwr.add(ct.TypeRef("ElectricPower"), name="type_ref")
    # body.add(s_pwr)

    # # Power connections (placeholders for PoC)
    # dc1 = ct.DirectedConnectStmt()
    # body.add(dc1)

    # c1 = ct.ConnectStmt()
    # body.add(c1)

    # # LDO configuration quantities
    # q_vin = ct.BilateralQuantity()
    # q_vin.add(ct.Quantity(5.0, "V"), name="quantity")
    # q_vin.add(ct.Quantity(5.0, "%"), name="tolerance")

    # a_vin = ct.AssignQuantityStmt()
    # a_vin.source.text = "ldo_3V3.v_in = 5V +/- 5%"
    # a_vin.field_ref.add(ct.FieldRefPart("ldo_3V3"), container=a_vin.field_ref.parts)
    # a_vin.field_ref.add(ct.FieldRefPart("v_in"), container=a_vin.field_ref.parts)
    # a_vin.quantity = q_vin
    # body.add(a_vin)

    # q_vout = ct.BilateralQuantity()
    # q_vout.add(ct.Quantity(3.3, "V"), name="quantity")
    # q_vout.add(ct.Quantity(3.0, "%"), name="tolerance")

    # a_vout = ct.AssignQuantityStmt()
    # a_vout.source.text = "ldo_3V3.v_out = 3.3V +/- 3%"
    # a_vout.field_ref.add(ct.FieldRefPart("ldo_3V3"), container=a_vout.field_ref.parts)
    # a_vout.field_ref.add(ct.FieldRefPart("v_out"), container=a_vout.field_ref.parts)
    # a_vout.quantity = q_vout
    # body.add(a_vout)

    # # USB connection (placeholder)
    # c2 = ct.ConnectStmt()
    # body.add(c2)

    return cu


def _iter_leaf_nodes(node: ct.CompilerNode) -> Iterator[ct.CompilerNode]:
    children = list(node.get_children(direct_only=True, types=ct.CompilerNode))
    if not children:
        yield node
        return

    for child in children:
        yield from _iter_leaf_nodes(child)


def print_leaf_sources(example: ct.CompilationUnit) -> None:
    for leaf in _iter_leaf_nodes(example):
        assert isinstance(source, ct.SourceChunk)
        source = leaf.get_child_by_name("source")
        print(source.text)


def visualize(example: ct.CompilationUnit):
    from atopile.compiler.interactive_compiler_graph import visualize_compiler_graph

    visualize_compiler_graph(example)


if __name__ == "__main__":
    example = build()
    print_leaf_sources(example)
    # visualize(example)

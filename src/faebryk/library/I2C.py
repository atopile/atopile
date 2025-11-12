# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class I2C(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    scl = F.ElectricLogic.MakeChild()
    sda = F.ElectricLogic.MakeChild()

    address = F.Parameters.NumericParameter.MakeChild(F.Units.Natural)
    bus_addresses = F.Parameters.NumericParameter.MakeChild(F.Units.Natural)
    frequency = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Hertz)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()
    _single_electric_reference = F.has_single_electric_reference.MakeChild()

    # ----------------------------------------
    #                 functions
    # ----------------------------------------

    def requires_pulls(self):
        self._requires_pulls = F.requires_pulls.MakeChild(
            self.scl,
            self.sda,
            interface_type=I2C,
            required_resistance=fabll.Range(
                1000 * (1 - 0.1) * F.Units.Ohm, 10000 * (1 + 0.1) * F.Units.Ohm
            ),
        )

    # def bus_crosses_pad_boundary(self):
    #     return (
    #         self.scl.line.net_crosses_pad_boundary()
    #         or self.sda.line.net_crosses_pad_boundary()
    #     )

    # def terminate(self, owner: fabll.Node):
    #     # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

    #     self.pull_up_sda = self.sda.pulled.pull(up=True, owner=owner)
    #     self.pull_up_scl = self.scl.pulled.pull(up=True, owner=owner)

    # class SpeedMode(Enum):
    #     low_speed = 10  # * P.khertz
    #     standard_speed = 100  # * P.khertz
    #     fast_speed = 400  # * P.khertz
    #     high_speed = 3.4  # * P.Mhertz

    # @staticmethod
    # def define_max_frequency_capability(mode: SpeedMode):
    #     return fabll.Range(I2C.SpeedMode.low_speed.value, mode.value)

    # # self.scl.line.add(F.has_net_name("SCL", level=F.has_net_name.Level.SUGGESTED))
    # # self.sda.line.add(F.has_net_name("SDA", level=F.has_net_name.Level.SUGGESTED))

    # def _hack_get_connected(self):
    #     """
    #     Workaround for hierarchical mifs not working currently
    #     """
    #     # Find all I2C interfaces connected to the same bus (via SCL line)
    #     # Assumption: If SCL is connected, SDA is also connected to the same
    #     # set of interfaces
    #     # Ensure the signal is connected to a line

    #     # Get all nodes connected electrically to the line
    #     connected_nodes = self.scl.line.get_connected()
    #     self.scl

    #     # Get all nodes connected logically to the line
    #     connected_nodes |= self.sda.get_connected()

    #     bus_interfaces: set[I2C] = set()
    #     for node in connected_nodes:
    #         interface = node.get_parent_of_type(I2C)
    #         # Filter out nodes not part of an I2C interface
    #         if interface is not None:
    #             bus_interfaces.add(interface)

    #     # include shallow connections
    #     bus_interfaces |= self.get_connected(include_self=False).keys()

    #     return bus_interfaces

    # class requires_unique_addresses(fabll.Node):
    #     class DuplicateAddressException(
    #         F.implements_design_check.UnfulfilledCheckException
    #     ):
    #         def __init__(self, duplicates: dict[P_Set, list["I2C"]], bus: set["I2C"]):
    #             message = "Duplicate I2C addresses found on the bus:\\n"
    #             message += md_list(
    #                 {f"{addr}": nodes for addr, nodes in duplicates.items()}
    #             )
    #             super().__init__(message, nodes=list(bus))

    #     design_check: F.implements_design_check

    #     @F.implements_design_check.register_post_solve_check
    #     def __check_post_solve__(self):
    #         solver = self.design_check.get_solver()
    #         obj = self.get_obj(I2C)
    #         bus_interfaces = obj._hack_get_connected()

    #         # If only self or less found, no conflicts possible
    #         if len(bus_interfaces) <= 1:
    #             return

    #         # Get addresses, handling potential unresolved parameters gracefully
    #         addresses: dict[I2C, P_Set] = {
    #             interface: solver.inspect_get_known_supersets(interface.address)
    #             for interface in bus_interfaces
    #         }
    #         unresolved, resolved = partition_as_list(
    #             lambda s: s[1].is_single_element(), addresses.items()
    #         )

    #         # Check for duplicates
    #         by_id = invert_dict(dict(resolved))
    #         duplicates = {
    #             addr: busses for addr, busses in by_id.items() if len(busses) > 1
    #         }
    #         if duplicates:
    #             raise I2C.requires_unique_addresses.DuplicateAddressException(
    #                 duplicates=duplicates, bus=bus_interfaces
    #             )

    #         # TODO: Consider raising MaybeUnfulfilled if there are unresolved addresses?
    #         # For now, we only raise if we find concrete duplicates.

    # address_check = requires_unique_addresses.MakeChild()

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import I2C, ElectricPower

        i2c_bus = new I2C
        i2c_bus.frequency = 400kHz  # Fast mode
        i2c_bus.address = 0x48  # Device address

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        i2c_bus.scl.reference ~ power_3v3
        i2c_bus.sda.reference ~ power_3v3

        # Connect to microcontroller
        microcontroller.i2c ~ i2c_bus

        # Connect to I2C sensor
        sensor.i2c ~ i2c_bus
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()

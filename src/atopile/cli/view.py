# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""

from enum import Enum
import logging
from typing import Annotated, Literal

from atopile.errors import UserBadParameterError
from atopile.views import Powertree, render_cli, render_dot
from faebryk.core.graph import GraphFunctions
import typer

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

view_app = typer.Typer(
    rich_markup_mode="rich",
    help="View block diagrams, schematics, or other visualizations of your project",
    no_args_is_help=True
)


@view_app.command(name="schematic")
def view_schematic(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
    ] = [],
):
    """
    View a schematic of your project.
    """

    from atopile import errors

    raise errors.UserNotImplementedError("View schematic is not yet implemented.")


class ViewFormat(str, Enum):
    """
    Enum for the output format of the view command.
    """
    CLI = "cli"
    DOT = "dot"


@view_app.command(name="power-tree")
def view_power_tree(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    target: Annotated[
        list[str], typer.Option("--target", "-t", envvar="ATO_TARGET")
    ] = [],
    option: Annotated[
        list[str], typer.Option("--option", "-o", envvar="ATO_OPTION")
    ] = [],
    format: Annotated[
        ViewFormat, typer.Option("--format", "-f", help="Output format"),
    ] = ViewFormat.CLI,
    max_depth: Annotated[
        int, typer.Option(
        # TODO(marko): Better description
            "--max-depth", "-d", help="How deep do you want to go into the modules",
        ),
    ] = 1,
):
    """
    View the power distribution tree of your project.
    """
    from atopile import build as buildlib
    from atopile.config import config

    # Apply configuration options
    config.apply_options(entry=entry, selected_builds=build)

    # Build the app to get the graph
    for build_ctx in config.builds:
        with build_ctx:
            app = buildlib.init_app()
            graph = app.get_graph()
            ptree_view = Powertree(GraphFunctions(graph))
            try:
                renderer = {
                    ViewFormat.CLI: render_cli,
                    ViewFormat.DOT: render_dot,
                }[format]
            except KeyError:
                raise UserBadParameterError("Invalid format specified.")
            ptree_view.render(renderer)

            #graph_fxns = GraphFunctions(graph)
            #electric_power_interfaces = graph_fxns.nodes_of_type(F.ElectricPower)
            #buses_grouped = ModuleInterface.group_into_buses(electric_power_interfaces)

            #bus_info = []
            #for bus_representative, connected_interfaces in buses_grouped.items():
            #    sources = [ep for ep in connected_interfaces if ep.has_trait(F.Power.is_power_source)]
            #    sinks = [ep for ep in connected_interfaces if ep.has_trait(F.Power.is_power_sink)]

            #    # Try to get voltage
            #    voltage_info = "Unknown"
            #    try:
            #        if hasattr(bus_representative, 'voltage'):
            #            voltage_param = bus_representative.voltage
            #            if hasattr(voltage_param, 'get_value'):
            #                voltage_val = voltage_param.get_value()
            #                if voltage_val:
            #                    voltage_info = f"{voltage_val}"
            #            elif hasattr(voltage_param, 'value'):
            #                if voltage_param.value:
            #                    voltage_info = f"{voltage_param.value}"
            #    except:
            #        pass

            #    bus_info.append({
            #        'representative': bus_representative,
            #        'voltage': voltage_info,
            #        'sources': sources,
            #        'sinks': sinks,
            #        'all_interfaces': connected_interfaces,
            #        'size': len(connected_interfaces)
            #    })

            ## Sort buses by voltage (if available) or by number of connections
            #bus_info.sort(key=lambda x: (x['voltage'] != "Unknown", x['voltage'], -x['size']))

            ## Print the power tree
            #log.info("\n=== Power Tree ===")
            #for i, bus in enumerate(bus_info, 1):
            #    log.info(f"\nBus {i}: Voltage = {bus['voltage']}")
            #    log.info(f"  Connected interfaces: {bus['size']}")

            #    if bus['sources']:
            #        log.info(f"  Sources ({len(bus['sources'])}):")
            #        for source in bus['sources']:
            #            name = source.get_full_name()
            #            log.info(f"    • {name}")

            #    if bus['sinks']:
            #        log.info(f"  Sinks ({len(bus['sinks'])}):")
            #        for sink in bus['sinks']:
            #            name = sink.get_full_name()
            #            log.info(f"    • {name}")

            #    # Show a few unspecified interfaces if any
            #    unspecified = [ep for ep in bus['all_interfaces']
            #                  if not ep.has_trait(F.Power.is_power_source)
            #                  and not ep.has_trait(F.Power.is_power_sink)]
            #    if unspecified:
            #        log.info(f"  Other connections ({len(unspecified)}):")
            #        for j, intf in enumerate(unspecified[:5]):  # Show first 5
            #            name = intf.get_full_name()
            #            log.info(f"    • {name}")
            #        if len(unspecified) > 5:
            #            log.info(f"    ... and {len(unspecified) - 5} more")


# Keep the old view function as the default command for backward compatibility
@view_app.callback()
def view(
    ctx: typer.Context,
):
    """
    View a block diagram or schematic of your project.
    """
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        # This will only happen if we remove no_args_is_help
        from atopile import errors
        raise errors.UserNotImplementedError("View is not yet implemented.")

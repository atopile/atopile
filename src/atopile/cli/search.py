"""CLI for searching parts, packages, stdlib, BOM, and variables."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from atopile.errors import UserException, UserNoProjectException
from atopile.logging_utils import console

logger = logging.getLogger(__name__)

search_app = typer.Typer(
    name="search",
    help="Search parts, packages, standard library, BOM, and variables.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LCSC_RE = re.compile(r"^C?\d+$", re.IGNORECASE)


def _format_stock(stock: int | None) -> str:
    if stock is None:
        return "-"
    if stock >= 1_000_000:
        return f"{stock / 1_000_000:.1f}M"
    if stock >= 1_000:
        return f"{stock / 1_000:.0f}K"
    return str(stock)


def _format_price(price: float | None) -> str:
    if price is None:
        return "-"
    if price < 0.01:
        return f"${price:.4f}"
    return f"${price:.3f}"


def _find_project_root() -> Path:
    """Find project root by looking for ato.yaml up from cwd."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "ato.yaml").exists():
            return parent
    raise UserNoProjectException(
        "No ato.yaml found. Run this command from within an atopile project."
    )


def _list_available_targets(project_root: Path) -> list[str]:
    """List available build targets from build/builds directory."""
    builds_dir = project_root / "build" / "builds"
    if not builds_dir.exists():
        return []
    return sorted(
        d.name for d in builds_dir.iterdir() if d.is_dir()
    )


# ---------------------------------------------------------------------------
# ato search parts
# ---------------------------------------------------------------------------


@search_app.command()
def parts(
    query: Annotated[str, typer.Argument(help="Search query or LCSC part number")],
    limit: Annotated[int, typer.Option(help="Maximum results to show")] = 20,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
):
    """Search JLCPCB parts or get details for a specific part."""
    from atopile.server.domains.parts_search import (
        handle_get_part_details,
        handle_search_parts,
    )

    is_lcsc = _LCSC_RE.match(query.strip())

    if is_lcsc:
        # Detail view
        detail = handle_get_part_details(query.strip())
        if detail is None:
            console.print(f"[yellow]No part found for {query}[/yellow]")
            raise typer.Exit(1)

        if json_output:
            print(json.dumps(detail, indent=2, default=str))
            return

        _print_part_detail(detail)
    else:
        # Search view
        results, error = handle_search_parts(query, limit=limit)
        if error:
            console.print(f"[red]Error: {error}[/red]")
            raise typer.Exit(1)

        if not results:
            console.print(f"[yellow]No parts found for '{query}'[/yellow]")
            return

        if json_output:
            print(json.dumps(results, indent=2, default=str))
            return

        _print_parts_table(results)
        console.print(
            "\n[dim]Tip: ato search parts <LCSC_ID>  for details[/dim]"
        )


def _print_parts_table(parts: list[dict]) -> None:
    from rich.table import Table

    table = Table(title="Parts Search Results", show_lines=False)
    table.add_column("LCSC", style="cyan", no_wrap=True)
    table.add_column("MPN", style="bold")
    table.add_column("Manufacturer")
    table.add_column("Description", max_width=40)
    table.add_column("Package")
    table.add_column("Stock", justify="right")
    table.add_column("Price", justify="right")

    for part in parts:
        table.add_row(
            str(part.get("lcsc", "")),
            str(part.get("mpn", "")),
            str(part.get("manufacturer", "")),
            str(part.get("description", ""))[:40],
            str(part.get("package", "")),
            _format_stock(part.get("stock")),
            _format_price(part.get("unit_cost")),
        )

    console.print(table)


def _print_part_detail(detail: dict) -> None:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    lines = Text()
    lcsc = str(detail.get("lcsc", ""))
    if lcsc and not lcsc.upper().startswith("C"):
        lcsc = f"C{lcsc}"
    lines.append(f"LCSC: ", style="bold")
    lines.append(f"{lcsc}\n", style="cyan")
    lines.append(f"MPN: ", style="bold")
    lines.append(f"{detail.get('mpn', '')}\n")
    lines.append(f"Manufacturer: ", style="bold")
    lines.append(f"{detail.get('manufacturer', '')}\n")
    lines.append(f"Description: ", style="bold")
    lines.append(f"{detail.get('description', '')}\n")
    lines.append(f"Package: ", style="bold")
    lines.append(f"{detail.get('footprint', detail.get('package', ''))}\n")
    lines.append(f"Stock: ", style="bold")
    lines.append(f"{_format_stock(detail.get('stock'))}\n")

    panel = Panel(lines, title="[bold]Part Details[/bold]", border_style="cyan")
    console.print(panel)

    # Attributes table
    attributes = detail.get("attributes") or {}
    if attributes:
        attr_table = Table(title="Attributes")
        attr_table.add_column("Name", style="bold")
        attr_table.add_column("Value")
        for name, value in attributes.items():
            attr_table.add_row(name, str(value))
        console.print(attr_table)

    # Pricing tiers
    price_list = detail.get("price") or []
    if price_list:
        price_table = Table(title="Pricing")
        price_table.add_column("Qty From", justify="right")
        price_table.add_column("Qty To", justify="right")
        price_table.add_column("Unit Price", justify="right")
        for tier in price_list:
            price_table.add_row(
                str(tier.get("qFrom", "-")),
                str(tier.get("qTo", "-")),
                _format_price(tier.get("price")),
            )
        console.print(price_table)


# ---------------------------------------------------------------------------
# ato search packages
# ---------------------------------------------------------------------------


@search_app.command()
def packages(
    query: Annotated[
        Optional[str], typer.Argument(help="Search query or package identifier")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
):
    """Search the atopile package registry."""
    from atopile.server.domains.packages import (
        get_package_details_from_registry,
        search_registry_packages,
    )

    # Try to get installed packages for the current project
    installed_ids: set[str] = set()
    try:
        project_root = _find_project_root()
        from atopile.server.domains.packages import (
            get_installed_packages_for_project,
        )

        for pkg in get_installed_packages_for_project(project_root):
            installed_ids.add(pkg.identifier)
    except (UserNoProjectException, Exception):
        pass

    if query and "/" in query:
        # Detail view for publisher/name
        details = get_package_details_from_registry(query)
        if details is None:
            console.print(f"[yellow]Package not found: {query}[/yellow]")
            raise typer.Exit(1)

        if json_output:
            print(json.dumps(details.model_dump(), indent=2, default=str))
            return

        _print_package_detail(details, installed=details.identifier in installed_ids)
    else:
        # Search / list view
        results = search_registry_packages(query or "")
        if not results:
            console.print("[yellow]No packages found[/yellow]")
            return

        # Mark installed packages
        for pkg in results:
            if pkg.identifier in installed_ids:
                pkg.installed = True

        if json_output:
            print(
                json.dumps(
                    [p.model_dump() for p in results], indent=2, default=str
                )
            )
            return

        _print_packages_table(results)
        console.print(
            "\n[dim]Tip: ato search packages <publisher/name>  for details"
            "  |  ato add <identifier>  to install[/dim]"
        )


def _print_packages_table(pkgs: list) -> None:
    from rich.table import Table

    table = Table(title="Packages", show_lines=False)
    table.add_column("", no_wrap=True, width=1)
    table.add_column("Identifier", style="cyan", no_wrap=True)
    table.add_column("Version")
    table.add_column("Summary", max_width=50)
    table.add_column("Downloads", justify="right")

    for pkg in pkgs:
        installed_marker = "[green]*[/green]" if pkg.installed else ""
        table.add_row(
            installed_marker,
            pkg.identifier,
            pkg.latest_version or pkg.version or "-",
            (pkg.summary or pkg.description or "")[:50],
            _format_stock(pkg.downloads),
        )

    console.print(table)


def _print_package_detail(details, installed: bool = False) -> None:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    lines = Text()
    lines.append(f"Identifier: ", style="bold")
    lines.append(f"{details.identifier}\n", style="cyan")
    lines.append(f"Version: ", style="bold")
    lines.append(f"{details.version}\n")
    lines.append(f"Publisher: ", style="bold")
    lines.append(f"{details.publisher}\n")
    if installed:
        lines.append(f"Status: ", style="bold")
        lines.append(f"installed\n", style="green")
    if details.summary:
        lines.append(f"Summary: ", style="bold")
        lines.append(f"{details.summary}\n")
    if details.homepage:
        lines.append(f"Homepage: ", style="bold")
        lines.append(f"{details.homepage}\n")
    if details.repository:
        lines.append(f"Repository: ", style="bold")
        lines.append(f"{details.repository}\n")
    if details.license:
        lines.append(f"License: ", style="bold")
        lines.append(f"{details.license}\n")
    if details.downloads is not None:
        lines.append(f"Downloads: ", style="bold")
        lines.append(f"{details.downloads:,}\n")

    panel = Panel(lines, title="[bold]Package Details[/bold]", border_style="cyan")
    console.print(panel)

    # Import statements
    if details.import_statements:
        console.print("\n[bold]Import Statements:[/bold]")
        for stmt in details.import_statements:
            console.print(f"  [green]{stmt.import_statement}[/green]")
            if stmt.build_name:
                console.print(f"    [dim]build: {stmt.build_name}[/dim]")

    # Dependencies
    if details.dependencies:
        dep_table = Table(title="Dependencies")
        dep_table.add_column("Package", style="cyan")
        dep_table.add_column("Version")
        for dep in details.dependencies:
            dep_table.add_row(dep.identifier, dep.version or "-")
        console.print(dep_table)

    # Versions
    if details.versions:
        ver_table = Table(title="Versions")
        ver_table.add_column("Version")
        ver_table.add_column("Released")
        for ver in details.versions[:10]:
            ver_table.add_row(
                ver.version,
                ver.released_at or "-",
            )
        if len(details.versions) > 10:
            console.print(
                f"[dim]  ... and {len(details.versions) - 10} more versions[/dim]"
            )
        console.print(ver_table)

    console.print(
        f"\n[dim]Tip: ato add {details.identifier}  to install[/dim]"
    )


# ---------------------------------------------------------------------------
# ato search stdlib
# ---------------------------------------------------------------------------


@search_app.command()
def stdlib(
    query: Annotated[
        Optional[str], typer.Argument(help="Search query or exact type name")
    ] = None,
    modules: Annotated[
        bool, typer.Option("--modules/--no-modules", help="Include modules")
    ] = True,
    interfaces: Annotated[
        bool,
        typer.Option("--interfaces/--no-interfaces", help="Include interfaces"),
    ] = True,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
):
    """Browse the atopile standard library."""
    from atopile.server.domains.stdlib import handle_get_stdlib, handle_get_stdlib_item

    # Try exact match for detail view
    if query:
        item = handle_get_stdlib_item(query)
        if item is not None:
            if json_output:
                print(json.dumps(item.model_dump(), indent=2, default=str))
                return
            _print_stdlib_detail(item)
            return

    # Build type filter
    type_filter = None
    if modules and not interfaces:
        type_filter = "module"
    elif interfaces and not modules:
        type_filter = "interface"

    response = handle_get_stdlib(type_filter=type_filter, search=query)

    if not response.items:
        console.print("[yellow]No stdlib items found[/yellow]")
        return

    if json_output:
        print(
            json.dumps(
                [i.model_dump() for i in response.items], indent=2, default=str
            )
        )
        return

    _print_stdlib_table(response.items)
    console.print(
        "\n[dim]Tip: ato search stdlib <TypeName>  for details[/dim]"
    )


def _print_stdlib_table(items: list) -> None:
    from rich.table import Table

    table = Table(title=f"Standard Library ({len(items)} items)", show_lines=False)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="bold")
    table.add_column("Description", max_width=60)

    for item in items:
        table.add_row(
            item.name,
            item.type.value,
            (item.description or "")[:60],
        )

    console.print(table)


def _print_stdlib_detail(item) -> None:
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree

    lines = Text()
    lines.append(f"Name: ", style="bold")
    lines.append(f"{item.name}\n", style="cyan")
    lines.append(f"Type: ", style="bold")
    lines.append(f"{item.type.value}\n")
    if item.description:
        lines.append(f"Description: ", style="bold")
        lines.append(f"{item.description}\n")

    panel = Panel(lines, title="[bold]Stdlib Item[/bold]", border_style="cyan")
    console.print(panel)

    # Children as a tree
    if item.children:
        tree = Tree(f"[bold]{item.name}[/bold]")
        for child in item.children:
            _add_child_to_tree(tree, child)
        console.print(tree)

    # Usage example
    if item.usage:
        console.print("\n[bold]Usage Example:[/bold]")
        from rich.syntax import Syntax

        console.print(Syntax(item.usage, "python", theme="monokai"))


def _add_child_to_tree(tree, child) -> None:
    label = f"[cyan]{child.name}[/cyan]: [dim]{child.type}[/dim]"
    if child.item_type.value == "parameter":
        label = f"[green]{child.name}[/green]: [dim]{child.type}[/dim]"
    if child.enum_values:
        label += f" [{', '.join(child.enum_values)}]"
    branch = tree.add(label)
    for nested in child.children:
        _add_child_to_tree(branch, nested)


# ---------------------------------------------------------------------------
# ato search bom
# ---------------------------------------------------------------------------


@search_app.command()
def bom(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Filter by value/type/MPN/LCSC"),
    ] = None,
    target: Annotated[str, typer.Option(help="Build target name")] = "default",
    limit: Annotated[int, typer.Option(help="Maximum rows to show")] = 20,
    all_rows: Annotated[
        bool, typer.Option("--all", help="Show all rows")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
):
    """Show bill of materials from a build."""
    project_root = _find_project_root()
    bom_path = project_root / "build" / "builds" / target / f"{target}.bom.json"

    if not bom_path.exists():
        available = _list_available_targets(project_root)
        if available:
            targets_str = ", ".join(available)
            console.print(
                f"[yellow]No BOM found for target '{target}'. "
                f"Available targets: {targets_str}[/yellow]"
            )
        else:
            console.print(
                f"[yellow]No BOM found for target '{target}'. "
                f"Run [bold]ato build[/bold] first.[/yellow]"
            )
        raise typer.Exit(1)

    data = json.loads(bom_path.read_text())

    if json_output:
        print(json.dumps(data, indent=2, default=str))
        return

    components = data.get("components", [])

    # Filter if query given
    if query:
        q = query.lower()
        components = [
            c
            for c in components
            if q in (c.get("value", "") or "").lower()
            or q in (c.get("type", "") or "").lower()
            or q in (c.get("mpn", "") or "").lower()
            or q in (c.get("lcsc", "") or "").lower()
            or q in (c.get("manufacturer", "") or "").lower()
            or q in (c.get("description", "") or "").lower()
        ]

    total = len(components)

    # Calculate total cost (BOM JSON uses camelCase: unitCost)
    total_cost = sum(
        (c.get("unitCost") or 0) * c.get("quantity", 1) for c in components
    )

    # Apply limit
    if not all_rows and total > limit:
        display = components[:limit]
    else:
        display = components

    _print_bom_table(display, total, total_cost, limit, all_rows)

    if not all_rows and total > limit:
        console.print(
            f"\n[dim]Showing {limit} of {total} components "
            f"(est. ${total_cost:.2f} total). "
            f"Use --all for full BOM.[/dim]"
        )
    else:
        console.print(f"\n[dim]{total} components (est. ${total_cost:.2f} total)[/dim]")

    console.print(
        "[dim]Tip: ato search parts <LCSC>  for part details[/dim]"
    )


def _print_bom_table(
    components: list[dict],
    total: int,
    total_cost: float,
    limit: int,
    all_rows: bool,
) -> None:
    from rich.table import Table

    table = Table(title="Bill of Materials", show_lines=False)
    table.add_column("Value", style="bold")
    table.add_column("Package")
    table.add_column("MPN")
    table.add_column("Manufacturer")
    table.add_column("Qty", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("LCSC", style="cyan")

    for comp in components:
        qty = comp.get("quantity", 1)
        unit_cost = comp.get("unitCost")
        line_cost = (unit_cost or 0) * qty

        table.add_row(
            str(comp.get("value", "")),
            str(comp.get("package", "")),
            str(comp.get("mpn", "") or ""),
            str(comp.get("manufacturer", "") or ""),
            str(qty),
            _format_price(line_cost) if unit_cost else "-",
            str(comp.get("lcsc", "") or ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# ato search variables
# ---------------------------------------------------------------------------


@search_app.command()
def variables(
    query: Annotated[
        Optional[str],
        typer.Argument(help="Filter variables by name/path"),
    ] = None,
    target: Annotated[str, typer.Option(help="Build target name")] = "default",
    limit: Annotated[int, typer.Option(help="Maximum items to show")] = 20,
    all_rows: Annotated[
        bool, typer.Option("--all", help="Show all items")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output raw JSON")
    ] = False,
):
    """Show design variables from a build."""
    project_root = _find_project_root()
    variables_path = (
        project_root / "build" / "builds" / target / f"{target}.variables.json"
    )

    if not variables_path.exists():
        available = _list_available_targets(project_root)
        if available:
            targets_str = ", ".join(available)
            console.print(
                f"[yellow]No variables found for target '{target}'. "
                f"Available targets: {targets_str}[/yellow]"
            )
        else:
            console.print(
                f"[yellow]No variables found for target '{target}'. "
                f"Run [bold]ato build[/bold] first.[/yellow]"
            )
        raise typer.Exit(1)

    data = json.loads(variables_path.read_text())

    if json_output:
        print(json.dumps(data, indent=2, default=str))
        return

    nodes = data.get("nodes", [])

    # Collect all variables with their paths
    all_vars = _collect_variables(nodes, "")
    total = len(all_vars)

    # Filter if query given
    if query:
        q = query.lower()
        all_vars = [
            v for v in all_vars if q in v["path"].lower() or q in v["name"].lower()
        ]

    filtered_total = len(all_vars)

    # Apply limit
    if not all_rows and filtered_total > limit:
        display_vars = all_vars[:limit]
    else:
        display_vars = all_vars

    _print_variables_table(display_vars)

    if not all_rows and filtered_total > limit:
        console.print(
            f"\n[dim]Showing {limit} of {filtered_total} variables. "
            f"Use --all for all variables.[/dim]"
        )
    else:
        console.print(f"\n[dim]{filtered_total} variables[/dim]")


def _collect_variables(
    nodes: list[dict], parent_path: str
) -> list[dict]:
    """Flatten the variable tree into a list with full paths."""
    result = []
    for node in nodes:
        node_name = node.get("name", "")
        path = f"{parent_path}.{node_name}" if parent_path else node_name

        for var in node.get("variables", []) or []:
            result.append(
                {
                    "path": f"{path}.{var.get('name', '')}",
                    "name": var.get("name", ""),
                    "spec": var.get("spec"),
                    "actual": var.get("actual"),
                    "unit": var.get("unit"),
                    "meets_spec": var.get("meetsSpec"),
                    "source": var.get("source"),
                }
            )

        for child in node.get("children", []) or []:
            result.extend(_collect_variables([child], path))

    return result


def _print_variables_table(vars_list: list[dict]) -> None:
    from rich.table import Table

    table = Table(title="Design Variables", show_lines=False)
    table.add_column("Path", style="cyan")
    table.add_column("Actual")
    table.add_column("Spec")
    table.add_column("Unit")
    table.add_column("Status", justify="center")

    for var in vars_list:
        meets = var.get("meets_spec")
        if meets is True:
            status = "[green]OK[/green]"
        elif meets is False:
            status = "[red]FAIL[/red]"
        else:
            status = "[dim]-[/dim]"

        table.add_row(
            var["path"],
            str(var.get("actual") or "-"),
            str(var.get("spec") or "-"),
            str(var.get("unit") or ""),
            status,
        )

    console.print(table)

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import glob
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import typer
from more_itertools import partition

from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.jlcpcb.picker_lib import (
    find_component_by_lcsc_id,
    find_component_by_mfr,
)
from faebryk.libs.picker.lcsc import download_easyeda_info
from faebryk.libs.pycodegen import (
    fix_indent,
    format_and_write,
    gen_block,
    gen_repeated_block,
    sanitize_name,
)
from faebryk.libs.tools.typer import typer_callback
from faebryk.libs.util import KeyErrorAmbiguous, KeyErrorNotFound, find

# TODO use AST instead of string


@dataclass
class CTX:
    path: Path
    pypath: str
    overwrite: bool


def get_ctx(ctx: typer.Context) -> "CTX":
    return ctx.obj


def write(ctx: typer.Context, contents: str, filename=""):
    path: Path = get_ctx(ctx).path
    if filename:
        path = path.with_stem(filename)

    if path.exists() and not get_ctx(ctx).overwrite:
        raise FileExistsError(f"File {path} already exists")

    format_and_write(contents, path)

    typer.echo(f"File {path} created")


def get_name(ctx: typer.Context):
    return get_ctx(ctx).path.stem


@typer_callback(None)
def main(ctx: typer.Context, name: str, local: bool = True, overwrite: bool = False):
    """
    Can be called like this: > faebryk libadd
    Or python -m faebryk libadd
    Or python -m faebryk.tools.libadd
    For help invoke command without arguments.
    """

    if not local:
        import faebryk.library._F as F

        libfolder = Path(F.__file__).parent
        pypath = f"faebryk.library.{name}"
    else:
        libfolder = Path("library")
        if not libfolder.is_dir():
            if Path("src").is_dir():
                candidates = glob.glob("src/*/library")
                if not len(candidates) == 1:
                    raise FileNotFoundError(
                        f"Library folder not found, are you in the right directory? "
                        f"{candidates}"
                    )
                libfolder = Path(candidates[0])

        pypath = f".library.{name}"

    if not libfolder.exists():
        raise FileNotFoundError(
            f"Library folder {libfolder} not found, are you in the right directory?"
        )

    path = libfolder / (name + ".py")

    ctx.obj = CTX(path=path, pypath=pypath, overwrite=overwrite)


@main.command()
def module(
    ctx: typer.Context, interface: bool = False, mfr: bool = False, lcsc: bool = False
):
    name = get_name(ctx)

    docstring = "TODO: Docstring describing your module"
    base = "Module" if not interface else "ModuleInterface"

    part: Component | None = None
    traits = []
    nodes = []

    imports = [
        "import faebryk.library._F as F  # noqa: F401",
        f"from faebryk.core.{base.lower()} import {base}",
        "from faebryk.libs.library import L  # noqa: F401",
        "from faebryk.libs.units import P  # noqa: F401",
    ]

    if mfr and lcsc:
        raise ValueError("Cannot use both mfr and lcsc")
    if mfr or lcsc:
        import faebryk.libs.picker.lcsc as lcsc_

        BUILD_DIR = Path("./build")
        lcsc_.BUILD_FOLDER = BUILD_DIR
        lcsc_.LIB_FOLDER = BUILD_DIR / Path("kicad/libs")
        lcsc_.MODEL_PATH = None

    if lcsc:
        part = find_component_by_lcsc_id(name)
        traits.append(
            "lcsc_id = L.f_field(F.has_descriptive_properties_defined)"
            f"({{'LCSC': '{name}'}})"
        )
    elif mfr:
        if "," in name:
            mfr_, mfr_pn = name.split(",", maxsplit=1)
        else:
            mfr_, mfr_pn = "", name
        try:
            part = find_component_by_mfr(mfr_, mfr_pn)
        except KeyErrorAmbiguous as e:
            # try find exact match
            try:
                part = find(e.duplicates, lambda x: x.mfr == mfr_pn)
            except KeyErrorNotFound:
                print(
                    f"Error: Ambiguous mfr_pn({mfr_pn}):"
                    f" {[(x.mfr_name, x.mfr) for x in e.duplicates]}"
                )
                print("Tip: Specify the full mfr_pn of your choice")
                sys.exit(1)

    if part:
        name = sanitize_name(f"{part.mfr_name}_{part.mfr}")
        assert isinstance(name, str)
        ki_footprint, _, easyeda_footprint, _, easyeda_symbol = download_easyeda_info(
            part.partno, get_model=False
        )

        designator_prefix = easyeda_symbol.info.prefix.replace("?", "")
        traits.append(
            f"designator_prefix = L.f_field(F.has_designator_prefix_defined)"
            f"('{designator_prefix}')"
        )

        imports.append("from faebryk.libs.picker.picker import DescriptiveProperties")
        traits.append(
            f"descriptive_properties = L.f_field(F.has_descriptive_properties_defined)"
            f"({{DescriptiveProperties.manufacturer: '{part.mfr_name}', "
            f"DescriptiveProperties.partno: '{part.mfr}'}})"
        )

        if part.datasheet:
            traits.append(
                f"datasheet = L.f_field(F.has_datasheet_defined)('{part.datasheet}')"
            )

        partdoc = part.description.replace("  ", "\n")
        docstring = f"{docstring}\n\n{partdoc}"

        # pins --------------------------------
        pins, noname = (
            list(x)
            for x in partition(
                lambda x: re.match(r"^[0-9]+$", x[1]),
                (
                    (pin.settings.spice_pin_number, pin.name.text)
                    for unit in easyeda_symbol.units
                    for pin in unit.pins
                ),
            )
        )

        pins = sorted(pins, key=lambda x: x[0])

        assert all(k == v for k, v in noname)
        noname = [k for k, v in sorted(noname, key=lambda x: int(x[0]))]
        noname_mapping = {pin_num: i for i, pin_num in enumerate(noname)}

        interface_names_by_pin_name = {
            pin_name: sanitize_name(pin_name) for _, pin_name in pins
        }

        nodes.append(
            "#TODO: Change auto-generated interface types to actual high level types"
        )
        nodes += [
            f"{pin_name}: F.Electrical"
            for pin_name in set(interface_names_by_pin_name.values())
        ]
        if noname:
            nodes.append(f"unnamed = L.list_field({len(noname)}, F.Electrical)")

        traits.append(f"""
            @L.rt_field
            def attach_via_pinmap(self):
                return F.can_attach_to_footprint_via_pinmap(
                    {{
                        {", ".join([f"'{pin_number}': {f'self.{interface_names_by_pin_name[pin_name]}'}"
                                    for pin_number, pin_name in sorted(pins)]
                                    + [
                                        f"'{pin_num}': self.unnamed[{i}]"
                                        for pin_num, i in noname_mapping.items()
                                    ])}
                    }}
                )
        """)

    out = fix_indent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging

        {gen_repeated_block(imports)}

        logger = logging.getLogger(__name__)

        class {name}({base}):
            \"\"\"
            {gen_block(docstring)}
            \"\"\"

            # ----------------------------------------
            #     modules, interfaces, parameters
            # ----------------------------------------
            {gen_repeated_block(nodes)}

            # ----------------------------------------
            #                 traits
            # ----------------------------------------
            {gen_repeated_block(traits)}

            def __preinit__(self):
                # ------------------------------------
                #           connections
                # ------------------------------------

                # ------------------------------------
                #          parametrization
                # ------------------------------------
                pass
    """)

    write(ctx, out, filename=name)


@main.command()
def trait(ctx: typer.Context, defined: bool = False):
    traitname = get_name(ctx)
    out = dedent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging
        from abc import abstractmethod

        from faebryk.core.trait import Trait

        logger = logging.getLogger(__name__)

        class {traitname}(Trait):
            \"\"\"
            Docstring describing your module
            \"\"\"

            @abstractmethod
            def DO_SOMETHING(self) -> None:
                \"\"\"
                Docstring describing the function
                \"\"\"
                pass
    """)

    write(ctx, out)

    if not defined:
        return

    implname = get_name(ctx) + "_defined"

    out = dedent(f"""
        # This file is part of the faebryk project
        # SPDX-License-Identifier: MIT

        import logging

        from {get_ctx(ctx).pypath} import {traitname}

        logger = logging.getLogger(__name__)

        class {implname}({traitname}.impl()):
            def DO_SOMETHING(self) -> None:
                pass
    """)

    write(ctx, out, filename=implname)


if __name__ == "__main__":
    main()

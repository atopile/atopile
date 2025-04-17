# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent, indent

import typer

from faebryk.libs.tools.typer import typer_callback


@dataclass
class CTX: ...


def get_ctx(ctx: typer.Context) -> "CTX":
    return ctx.obj


@typer_callback(None)
def main(ctx: typer.Context):
    """
    Can be called like this: > faebryk refactor
    """
    pass


pyname = r"[_a-zA-Z][_a-zA-Z0-9]*"


@main.command()
def libtof(ctx: typer.Context, root: Path):
    file_paths = list(root.rglob("**/*.py"))
    print(f"Found {len(file_paths)} files in path.")

    detection_pattern = re.compile(r"^from faebryk.library.[^_]")

    refactor_files = [
        path
        for path in file_paths
        if not path.stem.startswith("_")
        and any(
            detection_pattern.match(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    ]

    print(f"Found {len(refactor_files)} files to refactor.")

    # TO match:
    # from faebryk.library.has_kicad_footprint import has_kicad_footprint
    # from faebryk.library.has_simple_value_representation import (
    #     has_simple_value_representation,
    # )

    import_pattern = re.compile(
        r"^from faebryk.library.([^_][^ ]*) import ("
        f"{pyname}$"
        "|"
        f"\\([\n ]*{pyname},[\n ]*\\)$"  # multiline import
        r")",
        re.MULTILINE,
    )

    def refactor_file(path: Path):
        text = path.read_text(encoding="utf-8")
        import_symbols = [m[0] for m in import_pattern.findall(text)]
        text = import_pattern.subn("import faebryk.library._F as F", text, count=1)[0]
        text = import_pattern.sub("", text)

        for sym in import_symbols:
            if re.search(rf"from faebryk.library.{sym} import {sym} as", text):
                print(f"Warning: skipping {sym} in {path}")
                continue

            text = re.sub(rf"^\s*from faebryk.library.{sym} import {sym}$", "", text)
            text = re.sub(
                rf"^\s*from faebryk.library.{sym} import \(\n\s*{sym},\n\)$", "", text
            )
            text = re.sub(rf"(?<!F\.)\b{sym}\b", f"F.{sym}", text)

        # print(path, import_symbols)
        path.write_text(text, encoding="utf-8")

    for path in refactor_files:
        refactor_file(path)

    # Run ruff
    subprocess.check_call(["ruff", "check", "--fix", root])


maybe_f = r"(?:F\.)?"


@main.command()
def fabll(ctx: typer.Context, root: Path):
    file_paths = list(root.rglob("**/*.py"))
    print(f"Found {len(file_paths)} files in path.")

    types = r"(?:IF|NODE|PARAM)"
    ano_class = rf"class _{types}s\("
    # detection_pattern = re.compile(ano_class)

    refactor_files = file_paths
    # refactor_files = [
    #    path
    #    for path in file_paths
    #    if not path.stem.startswith("_") and detection_pattern.search(
    # path.read_text(encoding="utf-8"))
    # ]

    print(f"Found {len(refactor_files)} files to refactor.")

    holder_header = rf"[ ]*{ano_class}.*?\):\n"
    holder_pattern = re.compile(
        rf"({holder_header})(.*?)\n\n", re.MULTILINE | re.DOTALL
    )

    instance_holder = re.compile(rf"self.{types}s = _{types}s\(self\)", re.MULTILINE)
    holder_attr = re.compile(rf"\.{types}s\.")

    def refactor_file(path: Path):
        text = path.read_text(encoding="utf-8")

        print(path, "=" * 40)

        def process(m: re.Match) -> str:
            # print("Block", "|||")
            header, fields = m.groups()
            fields: str = fields + "\n"
            out = []
            for f in fields.split(")\n"):
                if not f:
                    continue
                f += ")"
                # print(f)
                # print(indent("|\nv", " " * 12))

                if "times" in f:
                    f = re.sub(r"\n\s*", "", f)
                    f = f.replace(",)", ")")

                    # case 3: screw_holes = times(3, lambda: F.Mounting_Hole())
                    f = re.sub(r"times\((\d+),", r"L.list_field(\1,", f)

                    # case 5:  leds = times(\n self.pixels.value, \n ...,\n)
                    f = re.sub(
                        rf"\s*({pyname}) = (times\(.*\))",
                        r"@L.rt_field\ndef \1(self):\n    return \2",
                        f,
                    )

                # case 1: uart_in = F.UART_Base()
                # case 4:  if buffered:\n power_data = F.ElectricPower()
                f = re.sub(rf" = ({maybe_f}{pyname})\(\)", r": \1", f)

                # case 2: fan_power_switch = F.PowerSwitchMOSFET(lowside=True, ...)
                f = re.sub(
                    rf" = ({maybe_f}{pyname})\((.*)\)", r" = L.f_field(\1)(\2)", f
                )

                # print(f)
                # print("--")
                out.append(dedent(f))

            outstr = indent("\n".join(out), " " * 4)
            # print(outstr)
            return outstr

        # Holders -------------------------------------
        text = holder_pattern.sub(process, text)
        text = instance_holder.sub("", text)
        text = holder_attr.sub(".", text)

        # Init ----------------------------------------
        # convert empty constructor to __preinit__
        text = re.sub(
            r"def __init__\(self\).*?:(.*?)super\(\).__init__\(\)",
            r"def __preinit__(self):\1pass",
            text,
            flags=re.DOTALL | re.MULTILINE,
        )

        # remove -> None from init
        text = re.sub(
            r"(def __init__\(self.*?\)).*?:",
            r"\1:",
            text,
        )

        def process_constructor(m: re.Match) -> str:
            str_: str = m.group(0)
            args = m.group(1)
            out = str_
            prefix = re.match(r"^\s*", str_).group(0)

            # find names of args
            arg_names = re.findall(rf",\s*({pyname})\s*(?:[:,]|$)", args)
            for arg in arg_names:
                out += indent(f"\n    self._{arg} = {arg}", prefix)

            out += indent("\n\ndef __preinit__(self):\n    pass", prefix)
            return out

        # split args of constructor into init and pre_init
        text = re.sub(
            r"^[ ]*def __init__\(self(, .*?)\):.*?super\(\).__init__\(\)",
            process_constructor,
            text,
            flags=re.DOTALL | re.MULTILINE,
        )

        # Done ----------------------------------------
        text = "\n".join(line.rstrip() for line in text.splitlines())
        text = text.strip() + "\n"
        path.write_text(text, encoding="utf-8")

    for path in refactor_files:
        refactor_file(path)


if __name__ == "__main__":
    main()

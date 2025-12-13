import logging
import re
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Protocol,
    cast,
    overload,
)

from faebryk.libs.checksum import Checksum
from faebryk.libs.kicad.other_fileformats import (
    UUID,
    C_kicad_config_common,
    C_kicad_drc_report_file,
    C_kicad_model_file,
    C_kicad_project_file,
)
from faebryk.libs.util import compare_dataclasses, find, find_or

logger = logging.getLogger(__name__)


# TODO find complete examples of the fileformats, maybe in the kicad repo


# zig shims


class Named(Protocol):
    name: str


# namespace
class kicad:
    from faebryk.core.zig.gen.sexp import (
        footprint,  # noqa: E402, F401 # type: ignore[import-untyped]
        footprint_v5,  # noqa: E402, F401 # type: ignore[import-untyped]
        fp_lib_table,  # noqa: E402, F401 # type: ignore[import-untyped]
        netlist,  # noqa: E402, F401 # type: ignore[import-untyped]
        pcb,  # noqa: E402, F401 # type: ignore[import-untyped]
        schematic,  # noqa: E402, F401 # type: ignore[import-untyped]
        symbol,  # noqa: E402, F401 # type: ignore[import-untyped]
        symbol_v6,  # noqa: E402, F401 # type: ignore[import-untyped]
    )

    class project:
        ProjectFile = C_kicad_project_file

    class drc:
        DrcFile = C_kicad_drc_report_file

    class model:
        ModelFile = C_kicad_model_file

    class config:
        ConfigFile = C_kicad_config_common

    type types = (
        pcb.PcbFile
        | footprint.FootprintFile
        | fp_lib_table.FpLibTableFile
        | netlist.NetlistFile
        | symbol.SymbolFile
        | schematic.SchematicFile
        | C_kicad_drc_report_file
        | C_kicad_model_file
        | C_kicad_project_file
        | C_kicad_config_common
        | footprint_v5.FootprintFile
        | symbol_v6.SymbolFile
    )

    @staticmethod
    def type_to_module(t: type[types] | types):
        def instance_or_subclass(_t: type | object, target: type):
            return _t is target or type(_t) is target

        if instance_or_subclass(t, kicad.pcb.PcbFile):
            return kicad.pcb
        elif instance_or_subclass(t, kicad.footprint.FootprintFile):
            return kicad.footprint
        elif instance_or_subclass(t, kicad.fp_lib_table.FpLibTableFile):
            return kicad.fp_lib_table
        elif instance_or_subclass(t, kicad.netlist.NetlistFile):
            return kicad.netlist
        elif instance_or_subclass(t, kicad.symbol.SymbolFile):
            return kicad.symbol
        elif instance_or_subclass(t, kicad.schematic.SchematicFile):
            return kicad.schematic
        elif instance_or_subclass(t, kicad.footprint_v5.FootprintFile):
            return kicad.footprint_v5
        elif instance_or_subclass(t, kicad.symbol_v6.SymbolFile):
            return kicad.symbol_v6
        elif instance_or_subclass(t, kicad.drc.DrcFile):
            return kicad.drc.DrcFile
        # TODO need to switch to bytes instead of str in sexp load
        # elif instance_or_subclass(t, kicad.model.ModelFile):
        #    return kicad.model.ModelFile
        elif instance_or_subclass(t, kicad.project.ProjectFile):
            return kicad.project.ProjectFile
        elif instance_or_subclass(t, kicad.config.ConfigFile):
            return kicad.config.ConfigFile

        raise ValueError(f"Unsupported type: {t} ({type(t)})")

    @staticmethod
    def loads[T: kicad.types](t: type[T], path_or_sexpstring: Path | str) -> T:
        """
        Attention: object returned is shared, so be careful with mutations!
        """
        path = None
        if isinstance(path_or_sexpstring, Path):
            path = path_or_sexpstring
            if not hasattr(kicad.loads, "cache"):
                kicad.loads.cache = {}
            if path in kicad.loads.cache:
                out = kicad.loads.cache[path]
                assert isinstance(out, t)
                return out
            data = path.read_text(encoding="utf-8")
        else:
            data = path_or_sexpstring

        out = cast(T, kicad.type_to_module(t).loads(data))
        if path:
            kicad.loads.cache[path] = out
        return out

    @staticmethod
    def dumps(obj: types, path: Path | None = None):
        raw = kicad.type_to_module(obj).dumps(
            obj,  # type: ignore
        )

        # TODO should live in zig
        # some files have trailing newlines, some don't
        if isinstance(obj, kicad.footprint.FootprintFile):
            if raw.endswith("\n"):
                raw = raw[: -len("\n")]

        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw, encoding="utf-8")
        return raw

    @staticmethod
    def gen_uuid(mark: str = ""):
        import uuid

        # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
        value = uuid.uuid4().hex

        suffix = mark.encode().hex()
        if suffix:
            value = value[: -len(suffix)] + suffix

        DASH_IDX = [8, 12, 16, 20]
        formatted = value
        for i, idx in enumerate(DASH_IDX):
            formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

        return UUID(formatted)

    @staticmethod
    def fp_get_base_name(fp: footprint.Footprint | pcb.Footprint) -> str:
        return fp.name.split(":")[-1]

    @staticmethod
    def get[T: Named](obj: Iterable[T], name: str) -> T:
        return find(obj, lambda o: o.name == name)

    @staticmethod
    def try_get[T: Named](
        obj: Iterable[T], name: str, default: T | None = None
    ) -> T | None:
        return find_or(obj, lambda o: o.name == name, default=cast(T, default))

    @staticmethod
    def set[T: Named](
        parent,
        field: str,
        container: list[T],
        value: T,
        index: int | None = None,
        preserve_uuid: bool = True,
    ) -> T:
        uuid = None
        if index is None:
            index = next(
                (i for i, o in enumerate(container) if o.name == value.name), -1
            )
            if index != -1:
                uuid = getattr(container[index], "uuid", None)
        kicad.filter(parent, field, container, lambda o: o.name != value.name)

        if preserve_uuid and hasattr(value, "uuid") and uuid:
            setattr(value, "uuid", uuid)

        return kicad.insert(parent, field, container, value, index=index)

    @staticmethod
    def insert[T](parent, field: str, container: list[T], *value: T, index=-1) -> T:
        obj = getattr(parent, field)
        for i, val in enumerate(value):
            obj.insert(index + i, val)

        return obj[index]

    @staticmethod
    def filter[T](
        parent, field: str, container: list[T], predicate: Callable[[T], bool]
    ):
        obj = getattr(parent, field)

        # Iterate backwards to avoid index shifting issues
        for i in range(len(obj) - 1, -1, -1):
            if not predicate(obj[i]):
                obj.pop(i)

        return obj

    @staticmethod
    def delete[T: Named](parent, field: str, container: list[T], name: str):
        kicad.filter(parent, field, container, lambda o: o.name != name)

    @staticmethod
    def clear_and_set[T](parent, field: str, container: list[T], values: list[T]):
        obj = getattr(parent, field)

        obj.clear()
        for val in values:
            obj.append(val)

    class geo:
        @staticmethod
        def rotate(obj: "kicad.pcb.Xy", center: "kicad.pcb.Xy", angle: float):
            import math

            angle = -angle  # rotate kicad style counter-clockwise

            # Translate point to origin
            translated_x = obj.x - center.x
            translated_y = obj.y - center.y

            # Convert angle to radians
            angle = math.radians(angle)

            # Rotate
            rotated_x = translated_x * math.cos(angle) - translated_y * math.sin(angle)
            rotated_y = translated_x * math.sin(angle) + translated_y * math.cos(angle)

            # Translate back
            new_x = rotated_x + center.x
            new_y = rotated_y + center.y

            return kicad.pcb.Xy(x=new_x, y=new_y)

        @overload
        @staticmethod
        def add(obj: "kicad.pcb.Xy", *other: "kicad.pcb.Xy") -> "kicad.pcb.Xy": ...

        @overload
        @staticmethod
        def add(
            obj: "kicad.pcb.Xyr", *other: "kicad.pcb.Xyr | kicad.pcb.Xy"
        ) -> "kicad.pcb.Xyr": ...

        @staticmethod
        def add(obj, *other):
            x = obj.x
            y = obj.y
            r = getattr(obj, "r", None) or 0
            for o in other:
                x += o.x
                y += o.y
                r += getattr(o, "r", None) or 0
            if hasattr(obj, "r"):
                return kicad.pcb.Xyr(x=x, y=y, r=r)
            else:
                return kicad.pcb.Xy(x=x, y=y)

        @overload
        @staticmethod
        def sub(obj: "kicad.pcb.Xy", *other: "kicad.pcb.Xy") -> "kicad.pcb.Xy": ...

        @overload
        @staticmethod
        def sub(
            obj: "kicad.pcb.Xyr", *other: "kicad.pcb.Xyr | kicad.pcb.Xy"
        ) -> "kicad.pcb.Xyr": ...

        @staticmethod
        def sub(obj, *other):
            x = obj.x
            y = obj.y
            r = getattr(obj, "r", None) or 0
            for o in other:
                x -= o.x
                y -= o.y
                r -= getattr(o, "r", None) or 0
            if hasattr(obj, "r"):
                return kicad.pcb.Xy(x=x, y=y)
            else:
                return kicad.pcb.Xyr(x=x, y=y, r=r)

        @staticmethod
        def neg(obj: "kicad.pcb.Xy") -> "kicad.pcb.Xy":
            return kicad.pcb.Xy(x=-obj.x, y=-obj.y)

        @staticmethod
        def get_layers(obj):
            if obj.layer is not None:
                return [obj.layer]
            if obj.layers is not None:
                return obj.layers
            return []

        @staticmethod
        def apply_to_layers(obj, func: Callable[[str], str]):
            if hasattr(obj, "layer") and obj.layer is not None:
                if isinstance(obj.layer, str):
                    obj.layer = func(obj.layer)
                elif hasattr(obj.layer, "layer"):
                    obj.layer.layer = func(obj.layer.layer)
            if hasattr(obj, "layers") and obj.layers is not None:
                obj.layers = [func(layer) for layer in obj.layers]

    @staticmethod
    @overload
    def convert(
        old: "kicad.footprint_v5.FootprintFile",
    ) -> "kicad.footprint.FootprintFile": ...

    @staticmethod
    @overload
    def convert(
        old: "kicad.symbol_v6.SymbolFile",
    ) -> "kicad.symbol.SymbolFile": ...

    @staticmethod
    def convert(old: Any) -> Any:
        old = kicad.copy(old)
        if isinstance(old, kicad.footprint_v5.FootprintFile):

            def _calc_arc_midpoint(arc: kicad.footprint_v5.Arc):
                start = arc.end
                center = arc.start

                mid = kicad.geo.rotate(start, center, -arc.angle / 2.0)
                end = kicad.geo.rotate(start, center, -arc.angle)

                return {"start": start, "mid": mid, "end": end}

            for k in old.footprint.fp_texts:
                if (name := k.type.capitalize()) in ("Reference", "Value"):
                    Property.set_property(
                        old.footprint,
                        kicad.pcb.Property(
                            name=name,
                            value=k.text,
                            at=k.at,
                            layer=k.layer.layer,
                            uuid=k.uuid or kicad.gen_uuid(),
                            hide=k.hide,
                            effects=k.effects,
                            unlocked=None,
                        ),
                        index=0 if name == "Reference" else 1,
                    )
            texts = [
                t
                for t in old.footprint.fp_texts
                if t.type
                not in (
                    kicad.pcb.E_fp_text_type.REFERENCE,
                    kicad.pcb.E_fp_text_type.VALUE,
                )
            ]
            for t in old.footprint.fp_texts:
                if t.type == kicad.pcb.E_fp_text_type.REFERENCE:
                    # already added it as property
                    continue
                    texts.append(
                        kicad.pcb.FpText(
                            type=kicad.pcb.E_fp_text_type.USER,
                            text=t.text.replace("REF**", "${REFERENCE}"),
                            at=t.at,
                            layer=t.layer,
                            uuid=t.uuid or kicad.gen_uuid(),
                            effects=t.effects,
                            hide=t.hide,
                        )
                    )
                elif not t.uuid:
                    t.uuid = kicad.gen_uuid()

            for p in old.footprint.pads:
                if p.uuid:
                    continue
                p.uuid = kicad.gen_uuid()

            if old.footprint.layer not in [None, "F.Cu"]:
                raise ValueError(
                    f"Invalid library footprint: layer must be F.Cu, got"
                    f" {old.footprint.layer}"
                )

            return kicad.footprint.FootprintFile(
                footprint=kicad.footprint.Footprint(
                    name=old.footprint.name,
                    layer=old.footprint.layer,
                    uuid=old.footprint.uuid or kicad.gen_uuid(),
                    path=old.footprint.path,
                    propertys=old.footprint.propertys,
                    fp_texts=texts,
                    attr=old.footprint.attr,
                    fp_lines=[
                        kicad.pcb.Line(
                            start=line.start,
                            end=line.end,
                            layer=line.layer,
                            layers=[line.layer],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=line.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for line in old.footprint.fp_lines
                    ],
                    fp_arcs=[
                        kicad.pcb.Arc(
                            **_calc_arc_midpoint(arc),
                            layer=arc.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=arc.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for arc in old.footprint.fp_arcs
                    ],
                    fp_circles=[
                        kicad.pcb.Circle(
                            center=circle.center,
                            end=circle.end,
                            layer=circle.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=circle.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for circle in old.footprint.fp_circles
                    ],
                    fp_rects=[
                        kicad.pcb.Rect(
                            start=rect.start,
                            end=rect.end,
                            layer=rect.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=rect.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for rect in old.footprint.fp_rects
                    ],
                    fp_poly=old.footprint.fp_poly,
                    pads=old.footprint.pads,
                    models=[
                        kicad.pcb.Model(
                            path=old.footprint.model.path,
                            offset=old.footprint.model.offset
                            or old.footprint.model.at
                            or kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=0, y=0, z=0)),
                            scale=old.footprint.model.scale,
                            rotate=old.footprint.model.rotate,
                        )
                    ]
                    if old.footprint.model
                    else [],
                    description=old.footprint.description,
                    tags=old.footprint.tags,
                    version=20241229,
                    generator="faebryk_convert",
                    generator_version="v5",
                    tedit=old.footprint.tedit,
                    embedded_fonts=False,
                )
            )
        elif isinstance(old, kicad.symbol_v6.SymbolFile):
            return kicad.symbol.SymbolFile(
                kicad_sym=kicad.symbol.SymbolLib(
                    version=20241229,
                    generator="faebryk_convert",
                    symbols=[
                        kicad.schematic.Symbol(
                            name=symbol.name,
                            power=symbol.power,
                            propertys=symbol.propertys,
                            pin_numbers=symbol.pin_numbers,
                            pin_names=symbol.pin_names,
                            in_bom=symbol.in_bom,
                            on_board=symbol.on_board,
                            symbols=[
                                kicad.schematic.SymbolUnit(
                                    name=sym.name,
                                    polylines=sym.polylines,
                                    circles=[
                                        kicad.schematic.Circle(
                                            center=circle.center,
                                            end=kicad.pcb.Xy(
                                                x=circle.center.x + circle.radius,
                                                y=circle.center.y,
                                            ),
                                            stroke=circle.stroke,
                                            fill=circle.fill,
                                        )
                                        for circle in sym.circles
                                    ],
                                    rectangles=sym.rectangles,
                                    arcs=sym.arcs,
                                    pins=sym.pins,
                                )
                                for sym in symbol.symbols
                            ],
                            convert=symbol.convert,
                        )
                        for symbol in old.kicad_sym.symbols
                    ],
                )
            )
        raise ValueError(f"Unsupported type: {type(old)}")

    @staticmethod
    def compare_without_uuid(old: Any, new: Any):
        return compare_dataclasses(
            before=old,
            after=new,
            skip_keys=("uuid",),
            require_dataclass_type_match=False,
            float_precision=2,
        )

    class KicadStruct(Protocol):
        @staticmethod
        def __field_names__() -> list[str]: ...

    type Primitive = str | list | int | float | bool | tuple | None

    @staticmethod
    def copy[T: KicadStruct | Primitive](old: T) -> T:
        if old is None:
            return old
        if isinstance(old, (str, int, float, bool, tuple)):
            return old
        # Accept both Python lists and pyzig MutableList wrappers
        # pyzig exposes lists as a C-extension type named 'pyzig.MutableList'
        if isinstance(old, list) or (
            type(old).__name__ == "MutableList"
            and type(old).__module__ in ("pyzig", "pyzig_local")
        ):
            return [kicad.copy(item) for item in old]  # type: ignore
        t = type(old)
        copied = {
            name: kicad.copy(getattr(old, name)) for name in old.__field_names__()
        }
        return t(**copied)

    @staticmethod
    def decompress(data: list[str]) -> bytes:
        from base64 import b64decode

        import zstd

        merged = "".join(str(v) for v in data)
        assert merged.startswith("|") and merged.endswith("|")
        return zstd.decompress(b64decode(merged[1:-1]))

    @staticmethod
    def compress(data: bytes) -> list[str]:
        from base64 import b64encode

        import zstd

        # from kicad:common/embedded_files.cpp
        b64 = b64encode(zstd.compress(data)).decode()
        CHUNK_LEN = 76
        # chunk string to 76 characters
        chunks = [b64[i : i + CHUNK_LEN] for i in range(0, len(b64), CHUNK_LEN)]
        chunks[0] = "|" + chunks[0]
        chunks[-1] = chunks[-1] + "|"
        return chunks


class Property:
    class _Property(Protocol):
        name: str
        value: str
        at: kicad.pcb.Xyr

        # def __init__(self, name: str, value: str): ...

    class _PropertyHolder(Protocol):  # [T: _Property](kicad.KicadStruct):
        propertys: list  # [T]

    class PropertyNotSet(Exception):
        pass

    class checksum:
        @staticmethod
        def _hashable(obj: "Property._PropertyHolder", remove_uuid: bool = True):
            # TODO: only used by ato part for verifying user didnt accidentally modify
            # will fix later when we care about that
            raise NotImplementedError("Not implemented")
            copy = kicad.copy(obj)

            Property.checksum.delete_checksum(copy)
            # TODO: this doesn't work atm
            # out = kicad.dumps(copy)
            out = repr(copy)

            if remove_uuid:
                out = re.sub(r"\(uuid \"[^\"]*\"\)", "", out)

            return out

        @staticmethod
        def set_checksum(
            obj: "Property._PropertyHolder", p_type: type["Property._Property"]
        ):
            Property.checksum.delete_checksum(obj)

            attrs = {
                "name": "checksum",
                "value": Checksum.build(Property.checksum._hashable(obj)),
                "at": kicad.pcb.Xyr(x=0, y=0, r=0),
                "hide": True,
            }
            if p_type is kicad.pcb.Property:
                attrs["layer"] = "F.Cu"
            Property.set_property(
                obj,
                p_type(**attrs),
            )

        @staticmethod
        def verify_checksum(obj: "Property._PropertyHolder"):
            checksum_stated = Property.checksum.get_checksum(obj)
            try:
                Checksum.verify(checksum_stated, Property.checksum._hashable(obj))
            except Checksum.Mismatch:
                # legacy
                Checksum.verify(
                    checksum_stated, Property.checksum._hashable(obj, remove_uuid=False)
                )

        @staticmethod
        def delete_checksum(obj: "Property._PropertyHolder"):
            Property.delete_property(obj, "checksum")

        @staticmethod
        def get_checksum(obj: "Property._PropertyHolder") -> str:
            return Property.get_property(obj.propertys, "checksum")

    @staticmethod
    def get_property_obj[T: _Property](obj: Iterable[T], name: str) -> T:
        for prop in obj:
            if prop.name == name:
                return prop
        raise Property.PropertyNotSet(f"Property `{name}` not set")

    @staticmethod
    def get_property(obj: Iterable[_Property], name: str) -> str:
        out = Property.try_get_property(obj, name)
        if out is None:
            raise Property.PropertyNotSet(f"Property `{name}` not set")
        return out

    @staticmethod
    def delete_property[T: _Property](parent: _PropertyHolder, name: str):
        kicad.delete(parent, "propertys", parent.propertys, name)

    @staticmethod
    def set_property[T: _Property](
        parent: _PropertyHolder, prop: T, index: int | None = None
    ) -> T:
        for p in parent.propertys:
            if p.name == prop.name:
                p.value = prop.value
                return p

        return kicad.set(parent, "propertys", parent.propertys, prop, index=index)

    @staticmethod
    def try_get_property(obj: Iterable[_Property], name: str) -> str | None:
        for prop in obj:
            if prop.name == name:
                return prop.value
        return None

    @staticmethod
    def property_dict(obj: Iterable[_Property]) -> dict[str, str]:
        return {prop.name: prop.value for prop in obj}

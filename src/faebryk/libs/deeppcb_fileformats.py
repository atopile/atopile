from __future__ import annotations

import json
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any

from dataclasses_json import CatchAll, Undefined, dataclass_json


class JSON_File:
    @classmethod
    def loads(cls, path_or_content: Path | str):
        if isinstance(path_or_content, Path):
            text = path_or_content.read_text(encoding="utf-8")
        else:
            text = path_or_content
        return cls.from_json(text)  # type: ignore[attr-defined]

    def dumps(self, path: PathLike | None = None) -> str:
        text = self.to_json(indent=2)  # type: ignore[attr-defined]
        if path is not None:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(text, encoding="utf-8")
        return text


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass(kw_only=True)
class C_deeppcb_board_file(JSON_File):
    """Typed DeepPCB board JSON container.

    The schema is evolving, so unknown fields are preserved in `unknown`.
    """

    name: str = ""
    rules: list[dict[str, Any]] = field(default_factory=list)
    resolution: dict[str, Any] = field(default_factory=lambda: {"unit": "mm", "value": 1000})
    boundary: dict[str, Any] = field(default_factory=dict)

    padstacks: list[dict[str, Any]] = field(default_factory=list)
    componentDefinitions: list[dict[str, Any]] = field(default_factory=list)
    viaDefinitions: list[str] = field(default_factory=list)

    netClasses: list[dict[str, Any]] = field(default_factory=list)
    netPreferences: list[dict[str, Any]] = field(default_factory=list)
    nets: list[dict[str, Any]] = field(default_factory=list)
    differentialPairs: list[dict[str, Any]] = field(default_factory=list)

    layers: list[dict[str, Any]] = field(default_factory=list)
    components: list[dict[str, Any]] = field(default_factory=list)
    wires: list[dict[str, Any]] = field(default_factory=list)
    vias: list[dict[str, Any]] = field(default_factory=list)
    planes: list[dict[str, Any]] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
    unknown: CatchAll = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "C_deeppcb_board_file":
        return cls.schema().load(payload)

    def to_mapping(self) -> dict[str, Any]:
        payload = self.to_dict()  # type: ignore[attr-defined]
        # Keep output stable and avoid noisy empty metadata in non-lossless mode.
        if isinstance(payload.get("metadata"), dict) and not payload["metadata"]:
            payload.pop("metadata", None)
        return payload


class deeppcb:
    class board:
        BoardFile = C_deeppcb_board_file

    type types = C_deeppcb_board_file

    @staticmethod
    def loads(t: type[types], path_or_content: Path | str):
        if t is not C_deeppcb_board_file:
            raise ValueError(f"Unsupported DeepPCB type: {t}")
        return t.loads(path_or_content)

    @staticmethod
    def dumps(obj: types, path: Path | None = None) -> str:
        if not isinstance(obj, C_deeppcb_board_file):
            raise ValueError(f"Unsupported DeepPCB object: {type(obj)}")
        if path is None:
            return json.dumps(obj.to_mapping(), indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj.to_mapping(), indent=2), encoding="utf-8")
        return path.read_text(encoding="utf-8")

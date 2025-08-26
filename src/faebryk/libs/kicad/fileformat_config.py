from dataclasses import dataclass

from dataclasses_json import CatchAll, DataClassJsonMixin, Undefined, dataclass_json


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass(kw_only=True)
class C_kicad_config_common(DataClassJsonMixin):
    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass(kw_only=True)
    class C_kicad_config_common_api(DataClassJsonMixin):
        enable_server: bool
        interpreter_path: str
        unknown: CatchAll = None

    api: C_kicad_config_common_api
    unknown: CatchAll = None

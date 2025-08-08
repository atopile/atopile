class FpLibEntry:
    name: str
    type: str
    uri: str
    options: str
    descr: str

class FpLibTable:
    version: str | None
    libs: list[FpLibEntry]

class FpLibTableFile:
    fp_lib_table: FpLibTable

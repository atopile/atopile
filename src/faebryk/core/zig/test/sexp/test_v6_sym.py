from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

PATH = "test/common/resources/fileformats/kicad/v6/sym/easyeda.kicad_sym"


def test_v6_sym():
    raw = Path(PATH).read_text()
    # Create a proper v6 symbol library structure with required fields
    wrapped = f"""(kicad_sym
        (version 20211014)
        (generator "test")
        {raw}
    )""".replace("hide", "")
    sym = kicad.loads(kicad.symbol_v6.SymbolFile, wrapped)
    print(f"Loaded {len(sym.kicad_sym.symbols)} symbols")
    if sym.kicad_sym.symbols:
        print(f"First symbol name: {sym.kicad_sym.symbols[0].name}")
        print(
            f"First symbol properties: {len(sym.kicad_sym.symbols[0].propertys)} properties"
        )


if __name__ == "__main__":
    test_v6_sym()

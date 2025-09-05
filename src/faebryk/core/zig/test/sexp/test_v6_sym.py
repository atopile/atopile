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
    symnew = kicad.convert(sym)
    out = kicad.dumps(symnew)
    print(out)


if __name__ == "__main__":
    test_v6_sym()

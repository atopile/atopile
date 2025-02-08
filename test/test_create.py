import pytest

from atopile.cli.create import AtoTemplate, FabllTemplate
from atopile.parse import parse_text_as_file
from faebryk.libs.picker.api.picker_lib import client


# Test a variety of component types
@pytest.mark.parametrize(
    "lcsc_id,description",
    [
        (2040, "RP2040"),
        (404010, "STM32H7"),
        (80100, "RC4580IDR"),
    ],
)
def test_ato_create_component(lcsc_id, description):
    components = client.fetch_part_by_lcsc(lcsc_id)

    # Create and populate template
    template = AtoTemplate(name="test_component", base="Module")
    template.add_part(components[0])

    # Generate the output
    output = template.dumps()

    # Basic assertions
    assert f'lcsc_id = "C{lcsc_id}"' in output
    assert "manufacturer =" in output
    assert "mpn =" in output

    tree = parse_text_as_file(output)
    assert tree is not None, "Failed to parse generated template"


@pytest.mark.parametrize(
    "lcsc_id,description",
    [
        (2040, "RP2040"),
        (404010, "STM32H7"),
        (80100, "RC4580IDR"),
    ],
)
def test_fabll_create_component(lcsc_id, description):
    components = client.fetch_part_by_lcsc(lcsc_id)

    if not components:
        pytest.skip(f"No components found for LCSC ID {lcsc_id} ({description})")

    # Create and populate template
    template = FabllTemplate(name="test_component", base="Module")
    template.add_part(components[0])

    # Generate the output
    output = template.dumps()

    # Make sure the code is valid
    compile(output, "<string>", "exec")

    # Basic assertions for expected content
    assert "lcsc_id = L.f_field" in output
    assert "descriptive_properties = L.f_field" in output
    assert "attach_via_pinmap" in output

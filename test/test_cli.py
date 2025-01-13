import os
import sys
from subprocess import run

import pytest

from atopile.cli.create import AtoTemplate, FabllTemplate
from atopile.parse import parse_text_as_file
from faebryk.libs.picker.api.api import ApiHTTPError
from faebryk.libs.picker.api.picker_lib import client
from faebryk.libs.util import run_live


@pytest.mark.slow
@pytest.mark.parametrize("config", ["ato", "fab"])
def test_app(config):
    stdout, _ = run_live(
        [sys.executable, "-m", "atopile", "build", "examples", "-b", config],
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        stdout=print,
        stderr=print,
    )
    assert "Build successful!" in stdout
    assert "ERROR" not in stdout


@pytest.mark.xfail(reason="Absolute performance will vary w/ hardware")
@pytest.mark.benchmark(
    min_rounds=10,
    max_time=0.3,
)
def test_snapiness(benchmark):
    def run_cli():
        return run(
            [sys.executable, "-m", "atopile", "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        )

    result = benchmark(run_cli)
    assert result.returncode == 0


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
    try:
        components = client.fetch_part_by_lcsc(lcsc_id)

        if not components:
            pytest.skip(f"No components found for LCSC ID {lcsc_id} ({description})")

        # Create and populate template
        template = AtoTemplate(name="test_component", base="Module")
        template.add_part(components[0])

        # Generate the output
        output = template.dumps()

        # Basic assertions
        assert f'lcsc_id = "C{lcsc_id}"' in output
        assert "manufacturer =" in output
        assert "mpn =" in output

        # Try parse the generated output to verify it's valid
        try:
            tree = parse_text_as_file(output)
            assert tree is not None, "Failed to parse generated template"
        except Exception as e:
            pytest.fail(f"Failed to parse template: {str(e)}\nTemplate was:\n{output}")

    except ApiHTTPError as e:
        if e.response.status_code == 404:
            pytest.skip(f"Component with LCSC ID {lcsc_id} ({description}) not found")
        raise


@pytest.mark.parametrize(
    "lcsc_id,description",
    [
        (2040, "RP2040"),
        (404010, "STM32H7"),
        (80100, "RC4580IDR"),
    ],
)
def test_fabll_create_component(lcsc_id, description):
    try:
        components = client.fetch_part_by_lcsc(lcsc_id)

        if not components:
            pytest.skip(f"No components found for LCSC ID {lcsc_id} ({description})")

        # Create and populate template
        template = FabllTemplate(name="test_component", base="Module")
        template.add_part(components[0])

        # Generate the output
        output = template.dumps()

        # Basic assertions for Python syntax
        try:
            # Try to compile the Python code to check syntax
            compile(output, "<string>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Fabll code has syntax errors: {str(e)}\nCode was:\n{output}")

        # Basic assertions for expected content
        assert "lcsc_id = L.f_field" in output
        assert "descriptive_properties = L.f_field" in output
        assert "attach_via_pinmap" in output

        print(f"\nGenerated Python template for {description} (C{lcsc_id}):")
        print(output)

    except ApiHTTPError as e:
        if e.response.status_code == 404:
            pytest.skip(f"Component with LCSC ID {lcsc_id} ({description}) not found")
        raise

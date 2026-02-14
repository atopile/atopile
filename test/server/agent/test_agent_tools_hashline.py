from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from atopile.dataclasses import (
    AppContext,
    BuildStatus,
)
from atopile.server.agent import policy, tools
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    utc_now_iso,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clear_agent_tool_caches() -> None:
    tools._openai_file_cache.clear()
    tools._datasheet_read_cache.clear()


def test_tool_definitions_advertise_hashline_editor() -> None:
    names = {tool_def["name"] for tool_def in tools.get_tool_definitions()}

    assert "project_edit_file" in names
    assert "project_list_modules" in names
    assert "project_module_children" in names
    assert "examples_list" in names
    assert "examples_search" in names
    assert "examples_read_ato" in names
    assert "stdlib_list" in names
    assert "stdlib_get_item" in names
    assert "datasheet_read" in names
    assert "design_diagnostics" in names
    assert "project_rename_path" in names
    assert "project_delete_path" in names
    assert "manufacturing_generate" in names
    assert "autolayout_run" in names
    assert "autolayout_status" in names
    assert "autolayout_fetch_to_layout" in names
    assert "autolayout_request_screenshot" in names
    assert "layout_get_component_position" in names
    assert "layout_set_component_position" in names
    assert "autolayout_configure_board_intent" in names
    assert "project_write_file" not in names
    assert "project_replace_text" not in names


def test_manager_tool_definitions_exclude_mutating_tools() -> None:
    names = {tool_def["name"] for tool_def in tools.get_tool_definitions_for_actor("manager")}

    assert "project_read_file" in names
    assert "project_search" in names
    assert "layout_get_component_position" in names
    assert "autolayout_request_screenshot" in names
    assert "layout_set_component_position" not in names
    assert "project_edit_file" not in names
    assert "project_write_file" not in names
    assert "project_replace_text" not in names
    assert "parts_install" not in names
    assert "packages_install" not in names
    assert "build_run" not in names
    assert "manufacturing_generate" not in names


def test_execute_tool_rejects_disallowed_manager_tool(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        _run(
            tools.execute_tool(
                name="project_edit_file",
                arguments={},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
                actor="manager",
            )
        )


def test_execute_tool_rejects_layout_set_for_manager(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        _run(
            tools.execute_tool(
                name="layout_set_component_position",
                arguments={"address": "app.mcu", "x_mm": 10, "y_mm": 10},
                project_root=tmp_path,
                ctx=AppContext(workspace_paths=[tmp_path]),
                actor="manager",
            )
        )


def test_execute_tool_allows_manager_read_tool(tmp_path: Path) -> None:
    (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

    result = _run(
        tools.execute_tool(
            name="project_read_file",
            arguments={"path": "main.ato", "start_line": 1, "max_lines": 20},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
            actor="manager",
        )
    )

    assert result["path"] == "main.ato"
    assert "module App:" in result["content"]


def test_execute_tool_allows_manager_layout_screenshot(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "layouts" / "default").mkdir(parents=True)
    (tmp_path / "layouts" / "default" / "default.kicad_pcb").write_text(
        "(kicad_pcb (version 20221018) (generator test))\n",
        encoding="utf-8",
    )
    (tmp_path / "ato.yaml").write_text(
        (
            "paths:\n"
            "  src: ./\n"
            "  layout: ./layouts\n"
            "builds:\n"
            "  default:\n"
            "    entry: main.ato:App\n"
        ),
        encoding="utf-8",
    )

    def fake_export_svg(
        pcb_file: Path,
        svg_file: Path,
        flip_board: bool = False,
        project_dir: Path | None = None,
        layers: str | None = None,
    ) -> None:
        svg_file.write_text("<svg />\n", encoding="utf-8")

    monkeypatch.setattr(
        "faebryk.exporters.pcb.kicad.artifacts.export_svg",
        fake_export_svg,
    )

    result = _run(
        tools.execute_tool(
            name="autolayout_request_screenshot",
            arguments={"target": "default", "view": "2d", "side": "top"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
            actor="manager",
        )
    )

    assert result["success"] is True
    assert Path(result["screenshot_paths"]["2d"]).exists()


@dataclass
class _FakeAt:
    x: float
    y: float
    r: float


@dataclass
class _FakeFootprint:
    at: _FakeAt
    layer: str


def _make_layout_record(
    *,
    reference: str,
    atopile_address: str,
    x: float,
    y: float,
    r: float,
    layer: str = "F.Cu",
) -> tools._LayoutComponentRecord:
    footprint = _FakeFootprint(at=_FakeAt(x=x, y=y, r=r), layer=layer)
    return tools._LayoutComponentRecord(
        reference=reference,
        atopile_address=atopile_address,
        layer=layer,
        x_mm=x,
        y_mm=y,
        rotation_deg=r,
        footprint=footprint,
    )


def test_layout_get_component_position_returns_exact_match(
    monkeypatch,
    tmp_path: Path,
) -> None:
    layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
    layout_path.parent.mkdir(parents=True)
    layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
    records = [
        _make_layout_record(
            reference="U1",
            atopile_address="App.mcu",
            x=12.5,
            y=8.0,
            r=90.0,
        )
    ]

    monkeypatch.setattr(
        tools,
        "_resolve_layout_file_for_tool",
        lambda *, project_root, target: layout_path,
    )
    monkeypatch.setattr(
        tools,
        "_load_layout_component_index",
        lambda _layout_path: (object(), records),
    )

    result = tools._layout_get_component_position(
        project_root=tmp_path,
        target="default",
        address="App.mcu",
        fuzzy_limit=5,
    )

    assert result["found"] is True
    assert result["matched_by"] == "atopile_address_exact"
    assert result["component"]["reference"] == "U1"
    assert result["component"]["x_mm"] == pytest.approx(12.5)
    assert result["component"]["rotation_deg"] == pytest.approx(90.0)


def test_layout_get_component_position_returns_fuzzy_suggestions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
    layout_path.parent.mkdir(parents=True)
    layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
    records = [
        _make_layout_record(
            reference="U1",
            atopile_address="App.mcu",
            x=10.0,
            y=10.0,
            r=0.0,
        ),
        _make_layout_record(
            reference="J1",
            atopile_address="App.usb",
            x=2.0,
            y=4.0,
            r=180.0,
        ),
    ]

    monkeypatch.setattr(
        tools,
        "_resolve_layout_file_for_tool",
        lambda *, project_root, target: layout_path,
    )
    monkeypatch.setattr(
        tools,
        "_load_layout_component_index",
        lambda _layout_path: (object(), records),
    )

    result = tools._layout_get_component_position(
        project_root=tmp_path,
        target="default",
        address="App.mcc",
        fuzzy_limit=3,
    )

    assert result["found"] is False
    assert result["suggestions"]
    assert result["suggestions"][0]["reference"] == "U1"
    assert result["suggestions"][0]["score"] >= 0.35


def test_layout_set_component_position_supports_absolute_and_relative(
    monkeypatch,
    tmp_path: Path,
) -> None:
    layout_path = tmp_path / "layouts" / "default" / "default.kicad_pcb"
    layout_path.parent.mkdir(parents=True)
    layout_path.write_text("(kicad_pcb)\n", encoding="utf-8")
    record = _make_layout_record(
        reference="U1",
        atopile_address="App.mcu",
        x=10.0,
        y=6.0,
        r=15.0,
        layer="F.Cu",
    )

    monkeypatch.setattr(
        tools,
        "_resolve_layout_file_for_tool",
        lambda *, project_root, target: layout_path,
    )
    footprint = record.footprint

    def fake_load_layout_index(_layout_path: Path):
        refreshed = tools._LayoutComponentRecord(
            reference="U1",
            atopile_address="App.mcu",
            layer=footprint.layer,
            x_mm=footprint.at.x,
            y_mm=footprint.at.y,
            rotation_deg=footprint.at.r,
            footprint=footprint,
        )
        return object(), [refreshed]

    monkeypatch.setattr(
        tools,
        "_load_layout_component_index",
        fake_load_layout_index,
    )
    monkeypatch.setattr(
        tools,
        "_write_layout_component_file",
        lambda _layout_path, _pcb_file: None,
    )

    def fake_move_fp(footprint: _FakeFootprint, coord, layer: str) -> None:
        footprint.at.x = float(coord.x)
        footprint.at.y = float(coord.y)
        footprint.at.r = float(coord.r)
        footprint.layer = layer

    monkeypatch.setattr(
        "faebryk.exporters.pcb.kicad.transformer.PCB_Transformer.move_fp",
        fake_move_fp,
    )

    absolute = tools._layout_set_component_position(
        project_root=tmp_path,
        target="default",
        address="App.mcu",
        mode="absolute",
        x_mm=25.0,
        y_mm=30.0,
        rotation_deg=45.0,
        dx_mm=None,
        dy_mm=None,
        drotation_deg=None,
        layer="B.Cu",
        fuzzy_limit=5,
    )
    assert absolute["updated"] is True
    assert absolute["after"]["x_mm"] == pytest.approx(25.0)
    assert absolute["after"]["y_mm"] == pytest.approx(30.0)
    assert absolute["after"]["rotation_deg"] == pytest.approx(45.0)
    assert absolute["after"]["layer"] == "B.Cu"

    relative = tools._layout_set_component_position(
        project_root=tmp_path,
        target="default",
        address="App.mcu",
        mode="relative",
        x_mm=None,
        y_mm=None,
        rotation_deg=None,
        dx_mm=-1.5,
        dy_mm=2.0,
        drotation_deg=10.0,
        layer=None,
        fuzzy_limit=5,
    )
    assert relative["updated"] is True
    assert relative["after"]["x_mm"] == pytest.approx(23.5)
    assert relative["after"]["y_mm"] == pytest.approx(32.0)
    assert relative["after"]["rotation_deg"] == pytest.approx(55.0)
    assert relative["delta"]["dx_mm"] == pytest.approx(-1.5)
    assert relative["delta"]["dy_mm"] == pytest.approx(2.0)
    assert relative["delta"]["drotation_deg"] == pytest.approx(10.0)


def test_examples_tools_list_search_and_read(monkeypatch, tmp_path: Path) -> None:
    examples_root = tmp_path / "examples"
    quickstart = examples_root / "quickstart"
    quickstart.mkdir(parents=True)
    (quickstart / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
    (quickstart / "quickstart.ato").write_text(
        "import Resistor\n\nmodule App:\n    r1 = new Resistor\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        tools,
        "_resolve_examples_root",
        lambda _project_root: examples_root,
    )

    listed = _run(
        tools.execute_tool(
            name="examples_list",
            arguments={},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    assert listed["total"] == 1
    assert listed["examples"][0]["name"] == "quickstart"
    assert listed["examples"][0]["ato_files"] == ["quickstart.ato"]

    searched = _run(
        tools.execute_tool(
            name="examples_search",
            arguments={"query": "new Resistor"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    assert searched["total"] == 1
    assert searched["matches"][0]["example"] == "quickstart"
    assert searched["matches"][0]["line"] == 4

    read = _run(
        tools.execute_tool(
            name="examples_read_ato",
            arguments={"example": "quickstart", "start_line": 1, "max_lines": 20},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    assert read["example"] == "quickstart"
    assert read["path"] == "quickstart.ato"
    assert "module App:" in read["content"]


def test_project_read_file_returns_hashline_content(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    file_path.write_text("a\nb\n", encoding="utf-8")

    result = _run(
        tools.execute_tool(
            name="project_read_file",
            arguments={"path": "main.ato", "start_line": 1, "max_lines": 10},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["path"] == "main.ato"
    lines = result["content"].splitlines()
    assert re.fullmatch(r"1:[0-9a-f]{4}\|a", lines[0])
    assert re.fullmatch(r"2:[0-9a-f]{4}\|b", lines[1])


def test_project_edit_file_executes_atomic_edit(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    file_path.write_text("a\nb\nc\n", encoding="utf-8")
    anchor = f"2:{policy.compute_line_hash(2, 'b')}"

    result = _run(
        tools.execute_tool(
            name="project_edit_file",
            arguments={
                "path": "main.ato",
                "edits": [
                    {
                        "set_line": {
                            "anchor": anchor,
                            "new_text": "B",
                        }
                    }
                ],
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["operations_applied"] == 1
    assert result["first_changed_line"] == 2
    assert file_path.read_text(encoding="utf-8") == "a\nB\nc\n"


def test_project_rename_and_delete_path_execute(tmp_path: Path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("hello\n", encoding="utf-8")

    renamed = _run(
        tools.execute_tool(
            name="project_rename_path",
            arguments={"old_path": "notes.md", "new_path": "docs/notes.md"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    assert renamed["old_path"] == "notes.md"
    assert renamed["new_path"] == "docs/notes.md"
    assert renamed["kind"] == "file"
    assert (tmp_path / "docs" / "notes.md").exists()
    assert not source.exists()

    deleted = _run(
        tools.execute_tool(
            name="project_delete_path",
            arguments={"path": "docs/notes.md"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    assert deleted["path"] == "docs/notes.md"
    assert deleted["deleted"] is True
    assert not (tmp_path / "docs" / "notes.md").exists()


def test_parts_install_returns_datasheet_followup_hint(monkeypatch) -> None:
    def fake_install_part(lcsc_id: str, project_root: str) -> dict[str, str]:
        assert lcsc_id == "C521608"
        assert project_root == "/tmp/project"
        return {
            "identifier": "STMicroelectronics_STM32G474RET6_package",
            "path": "/tmp/project/elec/src/parts/stm32g4/stm32g4.ato",
        }

    monkeypatch.setattr(tools.parts_domain, "handle_install_part", fake_install_part)

    result = _run(
        tools.execute_tool(
            name="parts_install",
            arguments={"lcsc_id": "c521608"},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["success"] is True
    assert result["lcsc_id"] == "C521608"
    assert "datasheet_read" in result["implementation_hint"]


def test_autolayout_run_maps_common_options(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        def start_job(
            self,
            project_root: str,
            build_target: str,
            provider_name: str | None,
            constraints: dict,
            options: dict,
        ) -> AutolayoutJob:
            captured["project_root"] = project_root
            captured["build_target"] = build_target
            captured["provider_name"] = provider_name
            captured["constraints"] = constraints
            captured["options"] = options
            return AutolayoutJob(
                job_id="al-123456789abc",
                project_root=project_root,
                build_target=build_target,
                provider="deeppcb",
                state=AutolayoutState.RUNNING,
                created_at=utc_now_iso(),
                updated_at=utc_now_iso(),
                provider_job_ref="board-123",
                constraints=constraints,
                options=options,
            )

    monkeypatch.setattr(tools, "get_autolayout_service", lambda: FakeService())

    result = _run(
        tools.execute_tool(
            name="autolayout_run",
            arguments={
                "build_target": "default",
                "provider": "deeppcb",
                "job_type": "Routing",
                "timeout_minutes": 15,
                "max_batch_timeout": 45,
                "webhook_url": "https://example.com/hook",
                "webhook_token": "tok",
                "constraints": {"keepouts": []},
                "options": {"responseBoardFormat": 3},
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["job_id"] == "al-123456789abc"
    assert result["background"] is True
    assert captured["build_target"] == "default"
    assert captured["provider_name"] == "deeppcb"
    assert captured["constraints"] == {"keepouts": []}
    options = captured["options"]
    assert isinstance(options, dict)
    assert options["jobType"] == "Routing"
    assert options["timeout"] == 15
    assert options["maxBatchTimeout"] == 45
    assert options["responseBoardFormat"] == 3


def test_autolayout_fetch_to_layout_archives_iteration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    layout_dir = tmp_path / "layouts" / "default"
    layout_dir.mkdir(parents=True)
    layout_path = layout_dir / "default.kicad_pcb"
    layout_path.write_text("old-board", encoding="utf-8")

    work_dir = tmp_path / "build" / "builds" / "default" / "autolayout" / "al-job"
    downloads_dir = work_dir / "downloads"
    downloads_dir.mkdir(parents=True)
    (downloads_dir / "cand-1.kicad_pcb").write_text("new-board", encoding="utf-8")
    (downloads_dir / "cand-1.json").write_text("{}", encoding="utf-8")
    (downloads_dir / "cand-1.ses").write_text('(session "")', encoding="utf-8")

    base_job = AutolayoutJob(
        job_id="al-123456789abc",
        project_root=str(tmp_path),
        build_target="default",
        provider="deeppcb",
        state=AutolayoutState.RUNNING,
        created_at=utc_now_iso(),
        updated_at=utc_now_iso(),
        provider_job_ref="board-123",
        layout_path=str(layout_path),
        work_dir=str(work_dir),
    )

    class FakeService:
        def refresh_job(self, job_id: str) -> AutolayoutJob:
            assert job_id == "al-123456789abc"
            return base_job

        def list_candidates(
            self,
            job_id: str,
            refresh: bool = True,
        ) -> list[AutolayoutCandidate]:
            assert job_id == "al-123456789abc"
            return [AutolayoutCandidate(candidate_id="cand-1", score=0.91)]

        def select_candidate(self, job_id: str, candidate_id: str) -> AutolayoutJob:
            assert job_id == "al-123456789abc"
            assert candidate_id == "cand-1"
            return base_job

        def apply_candidate(
            self,
            job_id: str,
            candidate_id: str | None = None,
            manual_layout_path: str | None = None,
        ) -> AutolayoutJob:
            assert job_id == "al-123456789abc"
            assert candidate_id == "cand-1"
            return AutolayoutJob(
                job_id=base_job.job_id,
                project_root=base_job.project_root,
                build_target=base_job.build_target,
                provider=base_job.provider,
                state=AutolayoutState.COMPLETED,
                created_at=base_job.created_at,
                updated_at=utc_now_iso(),
                provider_job_ref=base_job.provider_job_ref,
                layout_path=base_job.layout_path,
                work_dir=base_job.work_dir,
                applied_layout_path=str(layout_path),
                selected_candidate_id="cand-1",
                applied_candidate_id="cand-1",
            )

    monkeypatch.setattr(tools, "get_autolayout_service", lambda: FakeService())

    result = _run(
        tools.execute_tool(
            name="autolayout_fetch_to_layout",
            arguments={"job_id": "al-123456789abc"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["selected_candidate_id"] == "cand-1"
    assert result["downloaded_candidate_path"]
    artifacts = result["downloaded_artifacts"]
    assert isinstance(artifacts, dict)
    assert artifacts["kicad_pcb"].endswith("cand-1.kicad_pcb")
    assert artifacts["json"].endswith("cand-1.json")
    assert artifacts["ses"].endswith("cand-1.ses")
    archived = result["archived_iteration_path"]
    assert isinstance(archived, str)
    assert "autolayout_iterations" in archived
    assert Path(archived).exists()


def test_autolayout_request_screenshot_renders_images(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "layouts" / "default").mkdir(parents=True)
    (tmp_path / "layouts" / "default" / "default.kicad_pcb").write_text(
        "(kicad_pcb (version 20221018) (generator test))\n",
        encoding="utf-8",
    )
    (tmp_path / "ato.yaml").write_text(
        (
            "paths:\n"
            "  src: ./\n"
            "  layout: ./layouts\n"
            "builds:\n"
            "  default:\n"
            "    entry: main.ato:App\n"
        ),
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    def fake_export_svg(
        pcb_file: Path,
        svg_file: Path,
        flip_board: bool = False,
        project_dir: Path | None = None,
        layers: str | None = None,
    ) -> None:
        calls["svg_layers"] = layers
        calls["svg_pcb_file"] = str(pcb_file)
        svg_file.write_text("<svg />\n", encoding="utf-8")

    def fake_export_3d_board_render(
        pcb_file: Path,
        image_file: Path,
        project_dir: Path | None = None,
    ) -> None:
        calls["render_pcb_file"] = str(pcb_file)
        image_file.write_bytes(b"PNG")

    monkeypatch.setattr(
        "faebryk.exporters.pcb.kicad.artifacts.export_svg",
        fake_export_svg,
    )
    monkeypatch.setattr(
        "faebryk.exporters.pcb.kicad.artifacts.export_3d_board_render",
        fake_export_3d_board_render,
    )

    result = _run(
        tools.execute_tool(
            name="autolayout_request_screenshot",
            arguments={
                "target": "default",
                "view": "both",
                "side": "top",
                "layers": ["F.Cu", "Edge.Cuts"],
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["success"] is True
    assert result["view"] == "both"
    assert result["drawing_sheet_excluded"] is True
    assert result["layers"] == ["F.Cu", "Edge.Cuts"]
    assert calls["svg_layers"] == "F.Cu,Edge.Cuts"
    assert Path(result["screenshot_paths"]["2d"]).exists()
    assert Path(result["screenshot_paths"]["3d"]).exists()


def test_autolayout_request_screenshot_uses_default_bottom_layers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "layouts" / "default").mkdir(parents=True)
    (tmp_path / "layouts" / "default" / "default.kicad_pcb").write_text(
        "(kicad_pcb (version 20221018) (generator test))\n",
        encoding="utf-8",
    )
    (tmp_path / "ato.yaml").write_text(
        (
            "paths:\n"
            "  src: ./\n"
            "  layout: ./layouts\n"
            "builds:\n"
            "  default:\n"
            "    entry: main.ato:App\n"
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_export_svg(
        pcb_file: Path,
        svg_file: Path,
        flip_board: bool = False,
        project_dir: Path | None = None,
        layers: str | None = None,
    ) -> None:
        captured["layers"] = layers
        svg_file.write_text("<svg />\n", encoding="utf-8")

    monkeypatch.setattr(
        "faebryk.exporters.pcb.kicad.artifacts.export_svg",
        fake_export_svg,
    )

    result = _run(
        tools.execute_tool(
            name="autolayout_request_screenshot",
            arguments={"target": "default", "view": "2d", "side": "bottom"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["layers"] == ["B.Cu", "B.Paste", "B.Mask", "Edge.Cuts"]
    assert captured["layers"] == "B.Cu,B.Paste,B.Mask,Edge.Cuts"


def test_autolayout_configure_board_intent_updates_ato_yaml(tmp_path: Path) -> None:
    ato_yaml = tmp_path / "ato.yaml"
    ato_yaml.write_text(
        (
            "paths:\n"
            "  src: ./\n"
            "  layout: ./layouts\n"
            "builds:\n"
            "  default:\n"
            "    entry: main.ato:App\n"
        ),
        encoding="utf-8",
    )

    result = _run(
        tools.execute_tool(
            name="autolayout_configure_board_intent",
            arguments={
                "build_target": "default",
                "enable_ground_pours": True,
                "plane_nets": ["GND", "5V"],
                "layer_count": 4,
                "board_thickness_mm": 1.6,
                "outer_copper_oz": 1.0,
                "dielectric_er": 4.2,
                "preserve_existing_routing": True,
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["success"] is True
    assert result["build_target"] == "default"
    after = result["constraints_after"]
    assert after["plane_intent"]["enabled"] is True
    assert after["plane_intent"]["nets"] == ["GND", "5V"]
    assert after["stackup_intent"]["layer_count"] == 4
    assert after["stackup_intent"]["board_thickness_mm"] == 1.6
    assert after["preserve_existing_routing"] is True


def test_datasheet_read_uploads_pdf_and_returns_file_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_collect_project_datasheets(
        project_root: str,
        *,
        build_target: str | None = None,
        lcsc_ids: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict:
        assert project_root == str(tmp_path)
        assert build_target == "default"
        assert lcsc_ids == ["C521608"]
        assert overwrite is False
        return {
            "build_target": "default",
            "directory": str(tmp_path / "build" / "documentation" / "datasheets"),
            "matches": [
                {
                    "url": "https://example.com/tps7a02.pdf",
                    "path": str(
                        tmp_path
                        / "build"
                        / "documentation"
                        / "datasheets"
                        / "tps7a02.pdf"
                    ),
                    "filename": "tps7a02.pdf",
                    "lcsc_ids": ["C521608"],
                    "modules": ["regulator"],
                    "downloaded": True,
                    "skipped_existing": False,
                }
            ],
        }

    def fake_read_datasheet_file(
        project_root: Path,
        *,
        path: str | None = None,
        url: str | None = None,
    ) -> tuple[bytes, dict[str, object]]:
        assert project_root == tmp_path
        assert path and path.endswith("tps7a02.pdf")
        assert url is None
        return (
            b"%PDF-1.4\n",
            {
                "source_kind": "path",
                "source": "build/documentation/datasheets/tps7a02.pdf",
                "format": "pdf",
                "content_type": "application/pdf",
                "filename": "tps7a02.pdf",
                "sha256": "deadbeef",
                "size_bytes": 9,
            },
        )

    async def fake_upload_openai_user_file(
        *,
        filename: str,
        content: bytes,
        cache_key: str,
    ) -> tuple[str, bool]:
        assert filename == "tps7a02.pdf"
        assert content.startswith(b"%PDF-")
        assert cache_key == "deadbeef"
        return ("file-test-123", False)

    monkeypatch.setattr(
        tools.datasheets_domain,
        "handle_collect_project_datasheets",
        fake_collect_project_datasheets,
    )
    monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
    monkeypatch.setattr(
        tools,
        "_upload_openai_user_file",
        fake_upload_openai_user_file,
    )

    result = _run(
        tools.execute_tool(
            name="datasheet_read",
            arguments={
                "lcsc_id": "C521608",
                "target": "default",
                "query": "decoupling around vdd/vdda/vref+",
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["found"] is True
    assert result["openai_file_id"] == "file-test-123"
    assert result["openai_file_cached"] is False
    assert result["filename"] == "tps7a02.pdf"
    assert result["lcsc_id"] == "C521608"
    assert result["resolution"]["mode"] == "project_graph"


def test_datasheet_read_falls_back_when_graph_resolution_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_collect_project_datasheets(
        project_root: str,
        *,
        build_target: str | None = None,
        lcsc_ids: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict:
        _ = project_root, build_target, lcsc_ids, overwrite
        raise AssertionError("simulated graph failure")

    def fake_get_part_details(lcsc_id: str) -> dict | None:
        assert lcsc_id == "C521608"
        return {
            "datasheet_url": "https://example.com/stm32g4.pdf",
            "manufacturer": "STMicroelectronics",
            "part_number": "STM32G474RET6",
            "description": "MCU",
        }

    def fake_read_datasheet_file(
        project_root: Path,
        *,
        path: str | None = None,
        url: str | None = None,
    ) -> tuple[bytes, dict[str, object]]:
        assert project_root == tmp_path
        assert path is None
        assert url == "https://example.com/stm32g4.pdf"
        return (
            b"%PDF-1.7\n",
            {
                "source_kind": "url",
                "source": "https://example.com/stm32g4.pdf",
                "format": "pdf",
                "content_type": "application/pdf",
                "filename": "stm32g4.pdf",
                "sha256": "feedface",
                "size_bytes": 9,
            },
        )

    async def fake_upload_openai_user_file(
        *,
        filename: str,
        content: bytes,
        cache_key: str,
    ) -> tuple[str, bool]:
        assert filename == "stm32g4.pdf"
        assert content.startswith(b"%PDF-")
        assert cache_key == "feedface"
        return ("file-test-fallback", False)

    monkeypatch.setattr(
        tools.datasheets_domain,
        "handle_collect_project_datasheets",
        fake_collect_project_datasheets,
    )
    monkeypatch.setattr(
        tools.parts_domain,
        "handle_get_part_details",
        fake_get_part_details,
    )
    monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
    monkeypatch.setattr(
        tools,
        "_upload_openai_user_file",
        fake_upload_openai_user_file,
    )

    result = _run(
        tools.execute_tool(
            name="datasheet_read",
            arguments={"lcsc_id": "C521608", "target": "default"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["found"] is True
    assert result["openai_file_id"] == "file-test-fallback"
    assert result["resolution"]["mode"] == "parts_api_fallback"
    assert result["resolution"]["graph_error"]["type"] == "AssertionError"


def test_datasheet_read_uses_cached_reference_for_repeat_calls(
    monkeypatch,
    tmp_path: Path,
) -> None:
    counters = {"collect": 0, "read": 0, "upload": 0}

    def fake_collect_project_datasheets(
        project_root: str,
        *,
        build_target: str | None = None,
        lcsc_ids: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict:
        counters["collect"] += 1
        assert project_root == str(tmp_path)
        assert build_target == "default"
        assert lcsc_ids == ["C123456"]
        assert overwrite is False
        return {
            "build_target": "default",
            "directory": str(tmp_path / "build" / "documentation" / "datasheets"),
            "matches": [
                {
                    "url": "https://example.com/component.pdf",
                    "path": str(
                        tmp_path
                        / "build"
                        / "documentation"
                        / "datasheets"
                        / "component.pdf"
                    ),
                    "filename": "component.pdf",
                    "lcsc_ids": ["C123456"],
                    "modules": ["u1"],
                    "downloaded": True,
                    "skipped_existing": False,
                }
            ],
        }

    def fake_read_datasheet_file(
        project_root: Path,
        *,
        path: str | None = None,
        url: str | None = None,
    ) -> tuple[bytes, dict[str, object]]:
        counters["read"] += 1
        assert project_root == tmp_path
        assert path and path.endswith("component.pdf")
        assert url is None
        return (
            b"%PDF-1.7\ncached\n",
            {
                "source_kind": "path",
                "source": "build/documentation/datasheets/component.pdf",
                "format": "pdf",
                "content_type": "application/pdf",
                "filename": "component.pdf",
                "sha256": "cafebabe",
                "size_bytes": 16,
            },
        )

    async def fake_upload_openai_user_file(
        *,
        filename: str,
        content: bytes,
        cache_key: str,
    ) -> tuple[str, bool]:
        counters["upload"] += 1
        assert filename == "component.pdf"
        assert content.startswith(b"%PDF-")
        assert cache_key == "cafebabe"
        return ("file-cached-1", False)

    monkeypatch.setattr(
        tools.datasheets_domain,
        "handle_collect_project_datasheets",
        fake_collect_project_datasheets,
    )
    monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
    monkeypatch.setattr(
        tools,
        "_upload_openai_user_file",
        fake_upload_openai_user_file,
    )

    first = _run(
        tools.execute_tool(
            name="datasheet_read",
            arguments={
                "lcsc_id": "C123456",
                "target": "default",
                "query": "first query",
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )
    second = _run(
        tools.execute_tool(
            name="datasheet_read",
            arguments={
                "lcsc_id": "C123456",
                "target": "default",
                "query": "second query",
            },
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert first["openai_file_id"] == "file-cached-1"
    assert first["datasheet_cache_hit"] is False
    assert second["openai_file_id"] == "file-cached-1"
    assert second["datasheet_cache_hit"] is True
    assert second["openai_file_cached"] is True
    assert second["query"] == "second query"
    assert counters == {"collect": 1, "read": 1, "upload": 1}


def test_datasheet_read_tries_jlc_fallback_urls_when_primary_url_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    read_attempts: list[str] = []

    def fake_collect_project_datasheets(
        project_root: str,
        *,
        build_target: str | None = None,
        lcsc_ids: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict:
        _ = project_root, build_target, lcsc_ids, overwrite
        return {
            "build_target": "default",
            "directory": str(tmp_path / "build" / "documentation" / "datasheets"),
            "matches": [],
        }

    def fake_get_part_details(lcsc_id: str) -> dict | None:
        assert lcsc_id == "C5360602"
        return {
            "datasheet_url": "https://example.com/dead.pdf",
            "manufacturer": "Sensirion",
            "part_number": "SHT4x",
            "description": "Humidity sensor",
        }

    def fake_search_jlc_parts(
        query: str,
        *,
        limit: int = 50,
    ) -> tuple[list[dict], str | None]:
        assert query == "C5360602"
        assert limit == 6
        return (
            [
                {
                    "lcsc": "C5360602",
                    "mpn": "SHT40-AD1B-R2",
                    "datasheet_url": "https://example.com/working.pdf",
                }
            ],
            None,
        )

    def fake_read_datasheet_file(
        project_root: Path,
        *,
        path: str | None = None,
        url: str | None = None,
    ) -> tuple[bytes, dict[str, object]]:
        assert project_root == tmp_path
        assert path is None
        assert url is not None
        read_attempts.append(url)
        if url.endswith("/dead.pdf"):
            raise policy.ScopeError("Failed to fetch datasheet url: dead")
        assert url.endswith("/working.pdf")
        return (
            b"%PDF-1.7\n",
            {
                "source_kind": "url",
                "source": url,
                "format": "pdf",
                "content_type": "application/pdf",
                "filename": "sht4x.pdf",
                "sha256": "11223344",
                "size_bytes": 9,
            },
        )

    async def fake_upload_openai_user_file(
        *,
        filename: str,
        content: bytes,
        cache_key: str,
    ) -> tuple[str, bool]:
        assert filename == "sht4x.pdf"
        assert content.startswith(b"%PDF-")
        assert cache_key == "11223344"
        return ("file-sht4x", False)

    monkeypatch.setattr(
        tools.datasheets_domain,
        "handle_collect_project_datasheets",
        fake_collect_project_datasheets,
    )
    monkeypatch.setattr(
        tools.parts_domain,
        "handle_get_part_details",
        fake_get_part_details,
    )
    monkeypatch.setattr(
        tools.parts_domain,
        "search_jlc_parts",
        fake_search_jlc_parts,
    )
    monkeypatch.setattr(policy, "read_datasheet_file", fake_read_datasheet_file)
    monkeypatch.setattr(
        tools,
        "_upload_openai_user_file",
        fake_upload_openai_user_file,
    )

    result = _run(
        tools.execute_tool(
            name="datasheet_read",
            arguments={"lcsc_id": "C5360602", "target": "default"},
            project_root=tmp_path,
            ctx=AppContext(workspace_paths=[tmp_path]),
        )
    )

    assert result["found"] is True
    assert result["openai_file_id"] == "file-sht4x"
    assert read_attempts == [
        "https://example.com/dead.pdf",
        "https://example.com/working.pdf",
    ]
    assert result["resolution"]["url_fallback"]["selected_url"].endswith("/working.pdf")


def test_build_run_forwards_include_and_exclude_targets(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def model_dump(self, by_alias: bool = False) -> dict:
            _ = by_alias
            return {"success": True, "message": "queued", "buildTargets": []}

    def fake_start_build(request):
        captured["include_targets"] = list(request.include_targets)
        captured["exclude_targets"] = list(request.exclude_targets)
        return FakeResponse()

    monkeypatch.setattr(tools.builds_domain, "handle_start_build", fake_start_build)

    result = _run(
        tools.execute_tool(
            name="build_run",
            arguments={
                "targets": ["default"],
                "include_targets": ["datasheets-lite"],
                "exclude_targets": ["mfg-data"],
            },
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["success"] is True
    assert captured["include_targets"] == ["datasheets-lite"]
    assert captured["exclude_targets"] == ["mfg-data"]


def test_report_bom_returns_summary_fields(monkeypatch) -> None:
    def fake_get_bom(project_root: str, target: str):
        assert project_root == "/tmp/project"
        assert target == "default"
        return {
            "build_id": "abc123",
            "items": [
                {"designator": "R1", "mpn": "RC0603", "quantity": 1},
                {"designator": "C1", "mpn": "CL10A", "quantity": 2},
            ],
            "meta": {"currency": "USD"},
        }

    monkeypatch.setattr(tools.artifacts_domain, "handle_get_bom", fake_get_bom)

    result = _run(
        tools.execute_tool(
            name="report_bom",
            arguments={"target": "default"},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["found"] is True
    assert result["summary"]["records_key"] == "items"
    assert result["summary"]["records_count"] == 2
    assert "designator" in result["summary"]["sample_fields"]


def test_report_variables_not_found_returns_actionable_message(monkeypatch) -> None:
    def fake_get_variables(project_root: str, target: str):
        assert project_root == "/tmp/project"
        assert target == "default"
        return None

    monkeypatch.setattr(
        tools.artifacts_domain,
        "handle_get_variables",
        fake_get_variables,
    )

    result = _run(
        tools.execute_tool(
            name="report_variables",
            arguments={"target": "default"},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["found"] is False
    assert "build_run" in result["message"]


def test_manufacturing_generate_queues_mfg_data_build(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        success = True
        message = "Build queued for project"

        @property
        def build_targets(self):
            @dataclass
            class _Target:
                target: str
                build_id: str

            return [_Target(target="default", build_id="build-xyz")]

    def fake_start_build(request):
        captured["project_root"] = request.project_root
        captured["targets"] = list(request.targets)
        captured["frozen"] = request.frozen
        captured["include_targets"] = list(request.include_targets)
        captured["exclude_targets"] = list(request.exclude_targets)
        return FakeResponse()

    @dataclass
    class FakeOutputs:
        gerbers: str | None = None
        bom_json: str | None = None
        bom_csv: str | None = None
        pick_and_place: str | None = None
        step: str | None = None
        glb: str | None = None
        kicad_pcb: str | None = None
        kicad_sch: str | None = None
        pcb_summary: str | None = None

    def fake_get_build_outputs(project_root: str, target: str):
        assert project_root == "/tmp/project"
        assert target == "default"
        return FakeOutputs(
            gerbers="/tmp/project/build/builds/default/default.gerber.zip",
            bom_json="/tmp/project/build/builds/default/default.bom.json",
        )

    monkeypatch.setattr(tools.builds_domain, "handle_start_build", fake_start_build)
    monkeypatch.setattr(
        tools.manufacturing_domain,
        "get_build_outputs",
        fake_get_build_outputs,
    )

    result = _run(
        tools.execute_tool(
            name="manufacturing_generate",
            arguments={"target": "default"},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["success"] is True
    assert result["queued_build_id"] == "build-xyz"
    assert result["include_targets"] == ["mfg-data"]
    assert "gerbers" in result["present_outputs_before"]
    assert "pick_and_place" in result["missing_outputs_before"]
    assert captured == {
        "project_root": "/tmp/project",
        "targets": ["default"],
        "frozen": False,
        "include_targets": ["mfg-data"],
        "exclude_targets": [],
    }


def test_build_logs_search_defaults_to_non_debug_levels(monkeypatch) -> None:
    @dataclass
    class FakeBuild:
        build_id: str = "abc123"
        status: BuildStatus = BuildStatus.FAILED
        return_code: int = 1
        error: str = "compile failed"
        stages: list[dict] = field(
            default_factory=lambda: [
                {"name": "compile", "status": "success", "elapsedSeconds": 1.2},
                {"name": "route", "status": "failed", "elapsedSeconds": 0.7},
            ]
        )
        total_stages: int = 2

    captured: dict[str, object] = {}

    def fake_build_get(build_id: str):
        assert build_id == "abc123"
        return FakeBuild()

    def fake_load_build_logs(
        *,
        build_id: str,
        stage: str | None,
        log_levels: list[str] | None,
        audience: str | None,
        count: int,
    ) -> list[dict]:
        captured.update(
            {
                "build_id": build_id,
                "stage": stage,
                "log_levels": log_levels,
                "audience": audience,
                "count": count,
            }
        )
        return [
            {
                "build_id": build_id,
                "stage": "compile",
                "level": "ERROR",
                "audience": "developer",
                "message": "compile failed",
            }
        ]

    monkeypatch.setattr(tools.BuildHistory, "get", fake_build_get)
    monkeypatch.setattr(tools, "load_build_logs", fake_load_build_logs)

    result = _run(
        tools.execute_tool(
            name="build_logs_search",
            arguments={"build_id": "abc123", "limit": 25},
            project_root=Path("."),
            ctx=AppContext(),
        )
    )

    assert captured["log_levels"] == ["INFO", "WARNING", "ERROR", "ALERT"]
    assert captured["stage"] is None
    assert result["filters"]["log_levels"] == ["INFO", "WARNING", "ERROR", "ALERT"]
    assert result["stage_summary"]["counts"]["failed"] == 1


def test_build_logs_search_honors_explicit_filters(monkeypatch) -> None:
    @dataclass
    class FakeBuild:
        build_id: str = "abc123"
        status: BuildStatus = BuildStatus.SUCCESS
        return_code: int = 0
        error: str | None = None
        stages: list[dict] = field(default_factory=list)
        total_stages: int = 0

    captured: dict[str, object] = {}

    def fake_build_get(build_id: str):
        assert build_id == "abc123"
        return FakeBuild()

    def fake_load_build_logs(
        *,
        build_id: str,
        stage: str | None,
        log_levels: list[str] | None,
        audience: str | None,
        count: int,
    ) -> list[dict]:
        captured.update(
            {
                "build_id": build_id,
                "stage": stage,
                "log_levels": log_levels,
                "audience": audience,
                "count": count,
            }
        )
        return []

    monkeypatch.setattr(tools.BuildHistory, "get", fake_build_get)
    monkeypatch.setattr(tools, "load_build_logs", fake_load_build_logs)

    result = _run(
        tools.execute_tool(
            name="build_logs_search",
            arguments={
                "build_id": "abc123",
                "stage": "compile",
                "log_levels": ["DEBUG"],
                "audience": "developer",
                "limit": 10,
            },
            project_root=Path("."),
            ctx=AppContext(),
        )
    )

    assert captured["stage"] == "compile"
    assert captured["log_levels"] == ["DEBUG"]
    assert captured["audience"] == "developer"
    assert result["filters"]["stage"] == "compile"
    assert result["filters"]["log_levels"] == ["DEBUG"]


def test_build_logs_search_null_query_does_not_filter_to_literal_none(
    monkeypatch,
) -> None:
    @dataclass
    class FakeBuild:
        build_id: str = "abc123"
        status: BuildStatus = BuildStatus.SUCCESS
        return_code: int = 0
        error: str | None = None
        stages: list[dict] = field(default_factory=list)
        total_stages: int = 0

    def fake_build_get(build_id: str):
        assert build_id == "abc123"
        return FakeBuild()

    def fake_load_build_logs(
        *,
        build_id: str,
        stage: str | None,
        log_levels: list[str] | None,
        audience: str | None,
        count: int,
    ) -> list[dict]:
        return [
            {
                "build_id": build_id,
                "stage": "compile",
                "level": "INFO",
                "audience": "developer",
                "message": "compile started",
            }
        ]

    monkeypatch.setattr(tools.BuildHistory, "get", fake_build_get)
    monkeypatch.setattr(tools, "load_build_logs", fake_load_build_logs)

    result = _run(
        tools.execute_tool(
            name="build_logs_search",
            arguments={"build_id": "abc123", "query": None, "limit": 10},
            project_root=Path("."),
            ctx=AppContext(),
        )
    )

    assert result["total"] == 1
    assert result["logs"][0]["message"] == "compile started"
    assert result["filters"]["query"] is None


def test_stdlib_tools_execute_with_expected_shape(monkeypatch) -> None:
    @dataclass
    class FakeItem:
        id: str
        name: str

        def model_dump(self) -> dict:
            return {"id": self.id, "name": self.name}

    @dataclass
    class FakeResponse:
        items: list[FakeItem]
        total: int

    def fake_get_stdlib(
        type_filter: str | None,
        search: str | None,
        refresh: bool,
        max_depth: int | None,
    ) -> FakeResponse:
        assert type_filter == "module"
        assert search == "usb"
        assert refresh is False
        assert max_depth == 1
        return FakeResponse(
            items=[
                FakeItem(id="USB_C", name="USB_C"),
                FakeItem(id="Resistor", name="Resistor"),
            ],
            total=2,
        )

    def fake_get_item(item_id: str) -> FakeItem | None:
        if item_id == "USB_C":
            return FakeItem(id="USB_C", name="USB_C")
        return None

    monkeypatch.setattr(tools.stdlib_domain, "handle_get_stdlib", fake_get_stdlib)
    monkeypatch.setattr(tools.stdlib_domain, "handle_get_stdlib_item", fake_get_item)

    listed = _run(
        tools.execute_tool(
            name="stdlib_list",
            arguments={
                "type_filter": "module",
                "search": "usb",
                "max_depth": 1,
                "limit": 1,
            },
            project_root=Path("."),
            ctx=AppContext(),
        )
    )
    assert listed["total"] == 2
    assert listed["returned"] == 1
    assert listed["items"][0]["id"] == "USB_C"

    found = _run(
        tools.execute_tool(
            name="stdlib_get_item",
            arguments={"item_id": "USB_C"},
            project_root=Path("."),
            ctx=AppContext(),
        )
    )
    assert found["found"] is True
    assert found["item"]["id"] == "USB_C"


def test_project_module_tools_execute_with_expected_shape(monkeypatch) -> None:
    @dataclass
    class FakeModule:
        name: str
        type: str
        file: str
        entry: str

        def model_dump(self, by_alias: bool = False) -> dict:
            _ = by_alias
            return {
                "name": self.name,
                "type": self.type,
                "file": self.file,
                "entry": self.entry,
            }

    @dataclass
    class FakeModulesResponse:
        modules: list[FakeModule]
        total: int

    @dataclass
    class FakeChild:
        name: str
        item_type: str
        children: list["FakeChild"]

        def model_dump(self, by_alias: bool = False) -> dict:
            _ = by_alias
            return {
                "name": self.name,
                "itemType": self.item_type,
                "children": [
                    child.model_dump(by_alias=True) for child in self.children
                ],
            }

    def fake_get_modules(project_root: str, type_filter: str | None):
        assert project_root == "/tmp/project"
        assert type_filter == "module"
        return FakeModulesResponse(
            modules=[
                FakeModule(
                    name="App",
                    type="module",
                    file="main.ato",
                    entry="main.ato:App",
                )
            ],
            total=1,
        )

    def fake_introspect_module(
        project_root: Path, entry_point: str, max_depth: int
    ) -> list[FakeChild]:
        assert str(project_root) == "/tmp/project"
        assert entry_point == "main.ato:App"
        assert max_depth == 2
        return [FakeChild(name="i2c", item_type="interface", children=[])]

    monkeypatch.setattr(tools.projects_domain, "handle_get_modules", fake_get_modules)
    monkeypatch.setattr(
        tools.module_introspection,
        "introspect_module",
        fake_introspect_module,
    )

    listed = _run(
        tools.execute_tool(
            name="project_list_modules",
            arguments={"type_filter": "module", "limit": 10},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )
    assert listed["total"] == 1
    assert listed["returned"] == 1
    assert listed["types"]["module"] == 1
    assert listed["modules"][0]["entry"] == "main.ato:App"

    children = _run(
        tools.execute_tool(
            name="project_module_children",
            arguments={"entry_point": "main.ato:App", "max_depth": 2},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )
    assert children["found"] is True
    assert children["counts"]["interface"] == 1


def test_build_logs_search_returns_stub_for_silent_failure(monkeypatch) -> None:
    @dataclass
    class FakeBuild:
        build_id: str
        project_root: str
        target: str
        status: BuildStatus
        started_at: float
        elapsed_seconds: float
        warnings: int
        errors: int
        return_code: int | None
        error: str | None
        timestamp: str | None

    def fake_load_build_logs(**kwargs):
        assert kwargs["build_id"] == "build-123"
        return []

    def fake_get(build_id: str):
        assert build_id == "build-123"
        return FakeBuild(
            build_id="build-123",
            project_root="/tmp/project",
            target="default",
            status=BuildStatus.FAILED,
            started_at=1.0,
            elapsed_seconds=2.0,
            warnings=0,
            errors=0,
            return_code=1,
            error="compiler crashed",
            timestamp=None,
        )

    monkeypatch.setattr(tools, "load_build_logs", fake_load_build_logs)
    monkeypatch.setattr(tools.BuildHistory, "get", fake_get)

    result = _run(
        tools.execute_tool(
            name="build_logs_search",
            arguments={"build_id": "build-123", "limit": 10},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["synthesized_stub"] is True
    assert result["total"] == 1
    assert "No log lines were captured" in result["logs"][0]["message"]
    assert result["status"] == "failed"


def test_build_logs_search_normalizes_interrupted_history(monkeypatch) -> None:
    @dataclass
    class FakeBuild:
        build_id: str
        project_root: str
        target: str
        status: BuildStatus
        started_at: float
        elapsed_seconds: float
        warnings: int
        errors: int
        return_code: int | None
        error: str | None
        timestamp: str | None

    def fake_get_all(limit: int):
        assert limit == 120
        return [
            FakeBuild(
                build_id="stale-build",
                project_root="/tmp/project",
                target="default",
                status=BuildStatus.BUILDING,
                started_at=1.0,
                elapsed_seconds=20.0,
                warnings=0,
                errors=0,
                return_code=None,
                error=None,
                timestamp=None,
            )
        ]

    monkeypatch.setattr(tools.BuildHistory, "get_all", fake_get_all)
    monkeypatch.setattr(tools, "_active_or_pending_build_ids", lambda: set())

    result = _run(
        tools.execute_tool(
            name="build_logs_search",
            arguments={},
            project_root=Path("/tmp/project"),
            ctx=AppContext(),
        )
    )

    assert result["total"] == 1
    assert result["builds"][0]["status"] == "failed"
    assert "interrupted" in result["builds"][0]["error"]

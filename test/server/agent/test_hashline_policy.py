"""Agent module tests moved from colocated runtime modules."""

import pytest

import re
from io import BytesIO
from pathlib import Path

from atopile.server.agent import policy

def _anchor(line: int, text: str) -> str:
    return f"{line}:{policy.compute_line_hash(line, text)}"

def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

def _test_format_hashline_content_shape() -> None:
    output = policy.format_hashline_content(["alpha", "beta"], start_line=10)
    lines = output.splitlines()

    assert re.fullmatch(r"10:[0-9a-f]{4}\|alpha", lines[0])
    assert re.fullmatch(r"11:[0-9a-f]{4}\|beta", lines[1])

def _test_parse_line_anchor_tolerates_copied_suffix() -> None:
    assert policy.parse_line_anchor("7:beef|value") == policy.LineAnchor(
        line=7,
        hash="beef",
    )
    assert policy.parse_line_anchor("7 : beef  value") == policy.LineAnchor(
        line=7,
        hash="beef",
    )

def _test_apply_hashline_set_line(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\nc\n")

    result = policy.apply_hashline_edits(
        tmp_path,
        "main.ato",
        [
            {
                "set_line": {
                    "anchor": _anchor(2, "b"),
                    "new_text": "B",
                }
            }
        ],
    )

    assert result["operations_applied"] == 1
    assert result["first_changed_line"] == 2
    assert result["diff"]["added_lines"] == 1
    assert result["diff"]["removed_lines"] == 1
    assert "preview" in result["diff"]
    assert result["_ui"]["edit_diff"]["path"] == "main.ato"
    assert file_path.read_text(encoding="utf-8") == "a\nB\nc\n"

def _test_apply_hashline_replace_range(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\nc\nd\n")

    result = policy.apply_hashline_edits(
        tmp_path,
        "main.ato",
        [
            {
                "replace_lines": {
                    "start_anchor": _anchor(2, "b"),
                    "end_anchor": _anchor(3, "c"),
                    "new_text": "X\nY",
                }
            }
        ],
    )

    assert result["operations_applied"] == 1
    assert result["first_changed_line"] == 2
    assert file_path.read_text(encoding="utf-8") == "a\nX\nY\nd\n"

def _test_apply_hashline_insert_after(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\n")

    result = policy.apply_hashline_edits(
        tmp_path,
        "main.ato",
        [
            {
                "insert_after": {
                    "anchor": _anchor(1, "a"),
                    "text": "x\ny",
                }
            }
        ],
    )

    assert result["operations_applied"] == 1
    assert result["first_changed_line"] == 2
    assert file_path.read_text(encoding="utf-8") == "a\nx\ny\nb\n"

def _test_apply_hashline_rejects_overlapping_operations(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\nc\n")

    with pytest.raises(policy.ScopeError, match="Overlapping edit spans"):
        policy.apply_hashline_edits(
            tmp_path,
            "main.ato",
            [
                {
                    "set_line": {
                        "anchor": _anchor(2, "b"),
                        "new_text": "B",
                    }
                },
                {
                    "replace_lines": {
                        "start_anchor": _anchor(1, "a"),
                        "end_anchor": _anchor(3, "c"),
                        "new_text": "A\nB\nC",
                    }
                },
            ],
        )

def _test_apply_hashline_rejects_noop_edits(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\n")

    with pytest.raises(policy.ScopeError, match="No changes made"):
        policy.apply_hashline_edits(
            tmp_path,
            "main.ato",
            [
                {
                    "set_line": {
                        "anchor": _anchor(2, "b"),
                        "new_text": "b",
                    }
                }
            ],
        )

def _test_apply_hashline_mismatch_includes_remap_hints(tmp_path: Path) -> None:
    file_path = tmp_path / "main.ato"
    _write(file_path, "a\nb\nc\n")

    with pytest.raises(policy.HashlineMismatchError) as exc_info:
        policy.apply_hashline_edits(
            tmp_path,
            "main.ato",
            [
                {
                    "set_line": {
                        "anchor": "2:dead",
                        "new_text": "B",
                    }
                }
            ],
        )

    message = str(exc_info.value)
    actual = policy.compute_line_hash(2, "b")

    assert ">>> 2:" in message
    assert "Quick fix - replace stale refs:" in message
    assert f"2:dead -> 2:{actual}" in message

def _test_read_file_chunk_resolves_legacy_deps_path(tmp_path: Path) -> None:
    package_file = (
        tmp_path
        / ".ato"
        / "modules"
        / "atopile"
        / "sensirion-sht45"
        / "sensirion-sht45.ato"
    )
    package_file.parent.mkdir(parents=True, exist_ok=True)
    _write(package_file, "module Sensor:\n")

    result = policy.read_file_chunk(
        tmp_path,
        ".ato/deps/atopile/sensirion-sht45/sht45.ato",
        start_line=1,
        max_lines=20,
    )

    assert (
        result["path"] == ".ato/modules/atopile/sensirion-sht45/sensirion-sht45.ato"
    )
    assert (
        result["resolved_from"] == ".ato/modules/atopile/sensirion-sht45/sht45.ato"
    )
    assert "1:" in result["content"]

def _test_read_file_chunk_missing_path_includes_package_suggestions(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".ato" / "modules" / "atopile" / "foo-sensor"
    package_dir.mkdir(parents=True, exist_ok=True)
    _write(package_dir / "foo-sensor.ato", "module Foo:\n")
    _write(package_dir / "foo-sensor-alt.ato", "module FooAlt:\n")

    with pytest.raises(
        policy.ScopeError,
        match=r"Try: .*\.ato/modules/atopile/foo-sensor/foo-sensor\.ato",
    ):
        policy.read_file_chunk(
            tmp_path,
            ".ato/deps/atopile/foo-sensor/missing.ato",
            start_line=1,
            max_lines=20,
        )

def _test_detect_datasheet_format_does_not_trust_pdf_suffix_for_html() -> None:
    detected = policy._detect_datasheet_format(
        source_value="https://example.com/datasheet.pdf",
        content_type="application/pdf",
        raw_bytes=b"<!doctype html><html><body>redirect</body></html>",
    )
    assert detected == "html"

def _test_create_path_supports_directories_and_allowed_files(
    tmp_path: Path,
) -> None:
    created_dir = policy.create_path(tmp_path, "plans", kind="directory")
    assert created_dir["path"] == "plans"
    assert created_dir["kind"] == "directory"
    assert created_dir["created"] is True

    created_file = policy.create_path(
        tmp_path,
        "plans/roadmap.md",
        kind="file",
        content="# Roadmap\n",
    )
    assert created_file["path"] == "plans/roadmap.md"
    assert created_file["kind"] == "file"
    assert created_file["extension"] == ".md"
    assert created_file["created"] is True
    roadmap_text = (tmp_path / "plans" / "roadmap.md").read_text(encoding="utf-8")
    assert roadmap_text.startswith("# Roadmap")

def _test_create_path_rejects_disallowed_extensions(tmp_path: Path) -> None:
    with pytest.raises(policy.ScopeError, match="Only .ato, .md, .py"):
        policy.create_path(tmp_path, "plans/notes.txt", kind="file", content="")

def _test_create_path_restricts_python_files_to_fabll_modules(
    tmp_path: Path,
) -> None:
    with pytest.raises(policy.ScopeError, match="fabll modules"):
        policy.create_path(tmp_path, "scripts/helper.py", kind="file")

    created = policy.create_path(
        tmp_path,
        "src/faebryk/library/NewModule.py",
        kind="file",
        content="class NewModule:\n    pass\n",
    )
    assert created["path"] == "src/faebryk/library/NewModule.py"
    assert created["extension"] == ".py"
    assert created["created"] is True

def _test_read_datasheet_file_rejects_non_pdf_payload_from_pdf_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_read_datasheet_bytes_from_url(
        url: str,
    ) -> tuple[bytes, str, str | None]:
        assert url == "https://example.com/datasheet.pdf"
        return (
            b"<html><body>not a pdf</body></html>",
            "https://example.com/datasheet.pdf",
            "application/pdf",
        )

    monkeypatch.setattr(
        policy,
        "_read_datasheet_bytes_from_url",
        fake_read_datasheet_bytes_from_url,
    )

    with pytest.raises(policy.ScopeError, match="not a valid PDF"):
        policy.read_datasheet_file(
            tmp_path,
            url="https://example.com/datasheet.pdf",
        )

def _test_lcsc_wmsc_url_extracts_part_number() -> None:
    url = (
        "https://www.lcsc.com/datasheet/"
        "lcsc_datasheet_2304140030_STMicroelectronics-STM32G474RET6_C521608.pdf"
    )
    fallback = policy.lcsc_wmsc_url(url)
    assert fallback == "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/C521608.pdf"

def _test_lcsc_wmsc_url_ignores_non_lcsc_urls() -> None:
    assert policy.lcsc_wmsc_url("https://www.st.com/resource/doc.pdf") is None

def _test_read_datasheet_bytes_from_url_falls_back_to_wmsc_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeResponse:
        def __init__(self, *, final_url: str, content_type: str, payload: bytes):
            self._final_url = final_url
            self.headers = {"Content-Type": content_type}
            self._buf = BytesIO(payload)

        def read(self, amount: int = -1) -> bytes:
            return self._buf.read(amount)

        def geturl(self) -> str:
            return self._final_url

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            _ = (exc_type, exc, tb)
            return False

    def _fake_urlopen(request, timeout):  # noqa: ANN001
        _ = timeout
        raw_url = getattr(request, "full_url", None) or request.get_full_url()
        if "wmsc.lcsc.com" in raw_url:
            return _FakeResponse(
                final_url=raw_url,
                content_type="application/pdf",
                payload=b"%PDF-1.4\n",
            )
        return _FakeResponse(
            final_url="https://www.lcsc.com/datasheet/C521608.pdf",
            content_type="text/html",
            payload=b"<!doctype html><html>not-pdf</html>",
        )

    monkeypatch.setattr(policy.urllib_request, "urlopen", _fake_urlopen)

    raw, source_value, content_type = policy._read_datasheet_bytes_from_url(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_demo_C521608.pdf"
    )
    assert raw.startswith(b"%PDF-")
    assert "wmsc.lcsc.com" in source_value
    assert content_type == "application/pdf"

class TestHashlinePolicy:
    test_format_hashline_content_shape = staticmethod(
        _test_format_hashline_content_shape
    )
    test_parse_line_anchor_tolerates_copied_suffix = staticmethod(
        _test_parse_line_anchor_tolerates_copied_suffix
    )
    test_apply_hashline_set_line = staticmethod(_test_apply_hashline_set_line)
    test_apply_hashline_replace_range = staticmethod(
        _test_apply_hashline_replace_range
    )
    test_apply_hashline_insert_after = staticmethod(
        _test_apply_hashline_insert_after
    )
    test_apply_hashline_rejects_overlapping_operations = staticmethod(
        _test_apply_hashline_rejects_overlapping_operations
    )
    test_apply_hashline_rejects_noop_edits = staticmethod(
        _test_apply_hashline_rejects_noop_edits
    )
    test_apply_hashline_mismatch_includes_remap_hints = staticmethod(
        _test_apply_hashline_mismatch_includes_remap_hints
    )
    test_read_file_chunk_resolves_legacy_deps_path = staticmethod(
        _test_read_file_chunk_resolves_legacy_deps_path
    )
    test_read_file_chunk_missing_path_includes_package_suggestions = staticmethod(
        _test_read_file_chunk_missing_path_includes_package_suggestions
    )
    test_detect_datasheet_format_does_not_trust_pdf_suffix_for_html = staticmethod(
        _test_detect_datasheet_format_does_not_trust_pdf_suffix_for_html
    )
    test_create_path_supports_directories_and_allowed_files = staticmethod(
        _test_create_path_supports_directories_and_allowed_files
    )
    test_create_path_rejects_disallowed_extensions = staticmethod(
        _test_create_path_rejects_disallowed_extensions
    )
    test_create_path_restricts_python_files_to_fabll_modules = staticmethod(
        _test_create_path_restricts_python_files_to_fabll_modules
    )
    test_read_datasheet_file_rejects_non_pdf_payload_from_pdf_url = staticmethod(
        _test_read_datasheet_file_rejects_non_pdf_payload_from_pdf_url
    )
    test_lcsc_wmsc_url_extracts_part_number = staticmethod(
        _test_lcsc_wmsc_url_extracts_part_number
    )
    test_lcsc_wmsc_url_ignores_non_lcsc_urls = staticmethod(
        _test_lcsc_wmsc_url_ignores_non_lcsc_urls
    )
    test_read_datasheet_bytes_from_url_falls_back_to_wmsc_pdf = staticmethod(
        _test_read_datasheet_bytes_from_url_falls_back_to_wmsc_pdf
    )

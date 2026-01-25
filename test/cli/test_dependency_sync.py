"""
Tests for _select_compatible_registry_release
"""

from unittest.mock import MagicMock, patch

import pytest
from semver import Version

import atopile.config as config
from atopile import errors
from faebryk.libs.backend.packages.api import _Schemas
from faebryk.libs.project.dependencies import (
    ProjectDependencies,
    ProjectDependency,
    _select_compatible_registry_release,
)


def _make_release_info(
    version: str, requires_atopile: str
) -> _Schemas.PackageReleaseInfo:
    """Create a minimal PackageReleaseInfo for testing."""
    return _Schemas.PackageReleaseInfo(
        created_at="2024-01-01T00:00:00",
        released_at="2024-01-01T00:00:00",
        key="test-key",
        identifier="test/package",
        version=version,
        repository="https://github.com/test/package",
        authors=[],
        license="MIT",
        summary="Test package",
        homepage=None,
        readme_url=None,
        url="https://packages.atopile.io/test/package",
        stats=_Schemas.PackageStats(
            total_downloads=0,
            this_week_downloads=0,
            this_month_downloads=0,
        ),
        hashes=_Schemas.FileHashes(sha256="abc123"),
        filename="test-package-1.0.0.zip",
        git_ref=None,
        requires_atopile=requires_atopile,
        size=1000,
        download_url="https://example.com/download",
        builds=None,
        dependencies=_Schemas.PackageDependencies(requires=[]),
        artifacts=None,
        layouts=None,
        yanked_at=None,
        yanked_reason=None,
    )


class TestSelectCompatibleRegistryRelease:
    """Tests for _select_compatible_registry_release."""

    def _mock_api(self, releases):
        api = MagicMock()
        api.get_package_releases.return_value = releases
        return api

    # --- No requested release (upgrade / find latest compatible) ---

    @patch("atopile.version.get_installed_atopile_version")
    def test_returns_latest_compatible_when_no_version_requested(self, mock_version):
        """When no version is requested, return the latest compatible release."""
        mock_version.return_value = Version(0, 14, 0)
        # API returns releases in descending order (newest first)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^1.0.0"),  # incompatible
                _make_release_info("1.2.0", "^0.14.0"),  # compatible (latest)
                _make_release_info("1.1.0", "^0.13.0"),  # compatible
                _make_release_info("1.0.0", "^0.12.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.2.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_skips_incompatible_latest(self, mock_version):
        """When the latest release requires a newer atopile, fall back."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^1.0.0"),  # incompatible
                _make_release_info("1.1.0", "^0.14.0"),  # first compatible
                _make_release_info("1.0.0", "^0.12.0"),  # also compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.1.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_raises_when_no_compatible_release(self, mock_version):
        """When no releases are compatible, raise UserException."""
        mock_version.return_value = Version(0, 10, 0)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^0.14.0"),
                _make_release_info("1.0.0", "^0.12.0"),
            ]
        )

        with pytest.raises(errors.UserException, match="No compatible versions"):
            _select_compatible_registry_release(api, "test/package", None)

    @patch("atopile.version.get_installed_atopile_version")
    def test_raises_when_no_releases_exist(self, mock_version):
        """When there are no releases at all, raise UserException."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api([])

        with pytest.raises(errors.UserException, match="No releases found"):
            _select_compatible_registry_release(api, "test/package", None)

    @patch("atopile.version.get_installed_atopile_version")
    def test_upgrade_downgrades_to_compatible_version(self, mock_version):
        """
        Key scenario: user has atopile 0.12.6 but dep is pinned to a version
        requiring ^0.14.0. Upgrade should select the latest version compatible
        with the installed atopile (effectively a downgrade of the dep).
        """
        mock_version.return_value = Version(0, 12, 6)
        # Releases in descending order - latest requires newer atopile
        api = self._mock_api(
            [
                _make_release_info("3.0.0", "^0.14.0"),  # incompatible with 0.12.6
                _make_release_info("2.5.0", "^0.14.0"),  # incompatible with 0.12.6
                _make_release_info(
                    "2.0.0", "^0.12.0"
                ),  # compatible (latest for 0.12.x)
                _make_release_info("1.5.0", "^0.12.0"),  # compatible
                _make_release_info("1.0.0", "^0.10.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "2.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_tilde_version_spec(self, mock_version):
        """Tilde spec ~0.14.0 means >=0.14.0 <0.15.0."""
        mock_version.return_value = Version(0, 14, 5)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "~0.15.0"),  # incompatible
                _make_release_info("1.0.0", "~0.14.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_gte_version_spec(self, mock_version):
        """>=0.12.0 means any version 0.12.0 or above."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", ">=0.15.0"),  # incompatible
                _make_release_info("1.0.0", ">=0.12.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_range_version_spec(self, mock_version):
        """Combined spec >=0.12.0,<0.15.0 restricts to a range."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", ">=0.12.0,<0.14.0"),  # incompatible
                _make_release_info("1.0.0", ">=0.12.0,<0.15.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_major_version_boundary(self, mock_version):
        """Caret spec ^1.0.0 allows up to <2.0.0."""
        mock_version.return_value = Version(1, 5, 0)
        api = self._mock_api(
            [
                _make_release_info("3.0.0", "^2.0.0"),  # incompatible
                _make_release_info("2.0.0", "^1.0.0"),  # compatible (1.5 is in ^1.0)
                _make_release_info("1.0.0", "^1.0.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "2.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_prerelease_atopile_version(self, mock_version):
        """Pre-release atopile versions still match against clean version."""
        mock_version.return_value = Version(0, 14, 0, "dev5")
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^0.15.0"),  # incompatible
                _make_release_info("1.0.0", "^0.14.0"),  # compatible
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "1.0.0"

    # --- With requested release (pinned version check) ---

    @patch("atopile.version.get_installed_atopile_version")
    def test_requested_compatible_version_returns_it(self, mock_version):
        """When a specific compatible version is requested, return it."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^0.14.0"),
                _make_release_info("1.0.0", "^0.12.0"),
            ]
        )

        result = _select_compatible_registry_release(api, "test/package", "1.0.0")
        assert result == "1.0.0"

    @patch("atopile.version.get_installed_atopile_version")
    def test_requested_incompatible_version_raises(self, mock_version):
        """When a specific incompatible version is requested, raise error."""
        mock_version.return_value = Version(0, 12, 6)
        api = self._mock_api(
            [
                _make_release_info("2.0.0", "^0.14.0"),
                _make_release_info("1.0.0", "^0.12.0"),
            ]
        )

        with pytest.raises(errors.UserException, match="requires atopile"):
            _select_compatible_registry_release(api, "test/package", "2.0.0")

    @patch("atopile.version.get_installed_atopile_version")
    def test_requested_nonexistent_version_raises(self, mock_version):
        """When a requested version doesn't exist, raise error."""
        mock_version.return_value = Version(0, 14, 0)
        api = self._mock_api(
            [
                _make_release_info("1.0.0", "^0.12.0"),
            ]
        )

        with pytest.raises(errors.UserException, match="Release not found"):
            _select_compatible_registry_release(api, "test/package", "9.9.9")

    @patch("atopile.version.get_installed_atopile_version")
    def test_upgrade_from_incompatible_pinned_to_compatible(self, mock_version):
        """
        Full upgrade scenario: user has pinned 3.0.0 (requires ^0.14.0) but runs
        atopile 0.12.6. Calling with requested_release=None should find 2.0.0
        (the latest compatible), not error out or keep the incompatible version.
        This simulates what update_versions() does.
        """
        mock_version.return_value = Version(0, 12, 6)
        api = self._mock_api(
            [
                _make_release_info("3.0.0", "^0.14.0"),
                _make_release_info("2.5.0", "^0.14.0"),
                _make_release_info("2.0.0", "^0.12.0"),
                _make_release_info("1.0.0", "^0.10.0"),
            ]
        )

        # Upgrade: pass None to find latest compatible
        result = _select_compatible_registry_release(api, "test/package", None)
        assert result == "2.0.0"

        # Verify the pinned version would be rejected if requested directly
        with pytest.raises(errors.UserException, match="requires atopile"):
            _select_compatible_registry_release(api, "test/package", "3.0.0")


class TestBuildDepChain:
    """Tests for ProjectDependencies._build_dep_chain."""

    def _make_dep(self, identifier: str, release: str | None = None):
        spec = config.RegistryDependencySpec(identifier=identifier, release=release)
        return ProjectDependency(spec)

    def test_direct_dep_no_parent(self):
        """A direct dependency with no parent shows just its identifier."""
        parent_map: dict[str, ProjectDependency] = {}
        result = ProjectDependencies._build_dep_chain(
            "atopile/indicator-leds", parent_map
        )
        assert result == "atopile/indicator-leds"

    def test_direct_dep_with_version(self):
        """A direct dependency with a version shows identifier@version."""
        parent_map: dict[str, ProjectDependency] = {}
        result = ProjectDependencies._build_dep_chain(
            "atopile/indicator-leds", parent_map, release="0.1.5"
        )
        assert result == "atopile/indicator-leds@0.1.5"

    def test_single_parent(self):
        """A dep with one parent shows parent → child with versions."""
        parent_dep = self._make_dep("atopile/realtek-package", "0.5.0")
        parent_map = {"atopile/indicator-leds": parent_dep}
        result = ProjectDependencies._build_dep_chain(
            "atopile/indicator-leds", parent_map, release="0.1.5"
        )
        assert result == "atopile/realtek-package@0.5.0 → atopile/indicator-leds@0.1.5"

    def test_multi_level_chain(self):
        """A dep with multiple ancestor levels shows the full chain."""
        root_dep = self._make_dep("my-project/dsp", "1.0.0")
        mid_dep = self._make_dep("atopile/realtek-package", "0.5.0")
        parent_map = {
            "atopile/realtek-package": root_dep,
            "atopile/indicator-leds": mid_dep,
        }
        result = ProjectDependencies._build_dep_chain(
            "atopile/indicator-leds", parent_map, release="0.1.5"
        )
        assert result == (
            "my-project/dsp@1.0.0 → "
            "atopile/realtek-package@0.5.0 → "
            "atopile/indicator-leds@0.1.5"
        )

    def test_parent_without_release(self):
        """A parent without a pinned release shows just the identifier."""
        parent_dep = self._make_dep("atopile/realtek-package", None)
        parent_map = {"atopile/indicator-leds": parent_dep}
        result = ProjectDependencies._build_dep_chain(
            "atopile/indicator-leds", parent_map, release="0.1.5"
        )
        assert result == "atopile/realtek-package → atopile/indicator-leds@0.1.5"

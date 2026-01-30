# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import cast

import atopile.config as config
from atopile import errors, version
from faebryk.libs.backend.packages.api import Errors as ApiErrors
from faebryk.libs.backend.packages.api import PackagesAPIClient
from faebryk.libs.package.dist import Dist, DistValidationError
from faebryk.libs.util import (
    DAG,
    clone_repo,
    duplicates,
    find_or,
    md_list,
    not_none,
    robustly_rm_dir,
)

logger = logging.getLogger(__name__)


def _log_add_package(identifier: str, version: str):
    logger.info(
        f"[green]+[/] {identifier}@{version}",
        extra={"markup": True},
    )


def _log_pin_package(identifier: str, version: str):
    logger.info(
        f"📌 {identifier}@{version}",
        extra={"markup": True},
    )


def _log_remove_package(identifier: str, version: str | None):
    dep_str = f"{identifier}@{version}" if version else identifier
    logger.info(f"[red]-[/] {dep_str}", extra={"markup": True})


def _select_compatible_registry_release(
    api: PackagesAPIClient, identifier: str, requested_release: str | None
) -> str:
    """
    Select a compatible release for a package based on the installed atopile version.

    The API returns releases in descending order (newest first), which is part of the
    API contract. If the user has specified a version, we check that specific version
    for compatibility and raise an error if it's incompatible. If no version is
    specified, we fall back to older versions if the latest is incompatible.
    """
    releases = api.get_package_releases(identifier)
    if not releases:
        raise errors.UserException(f"No releases found for {identifier}")

    # API returns releases in descending order (newest first) by contract
    installed_version = version.get_installed_atopile_version()

    if requested_release is not None:
        # User specified a version - find it and check compatibility
        requested = next(
            (release for release in releases if release.version == requested_release),
            None,
        )
        if requested is None:
            raise errors.UserException(
                f"Release not found: {identifier}@{requested_release}"
            )

        # If user explicitly specified a version, it must be compatible - no fallback
        if not version.match(requested.requires_atopile, installed_version):
            raise errors.UserException(
                f"Package {identifier}@{requested_release} requires atopile "
                f"{requested.requires_atopile}, but you have "
                f"{version.clean_version(installed_version)} installed."
            )

        return requested.version

    # No version specified - find the first compatible release (fallback behavior)
    latest_release = releases[0]
    compatible_release = next(
        (
            release
            for release in releases
            if version.match(release.requires_atopile, installed_version)
        ),
        None,
    )
    if compatible_release is None:
        raise errors.UserException(
            f"No compatible versions were found of package {identifier} "
            f"for atopile version {version.clean_version(installed_version)}"
        )

    if compatible_release.version != latest_release.version:
        logger.warning(
            "Package %s@%s requires atopile %s which is incompatible with %s; "
            "using %s@%s instead.",
            identifier,
            latest_release.version,
            latest_release.requires_atopile,
            version.clean_version(installed_version),
            identifier,
            compatible_release.version,
        )

    return compatible_release.version


class BrokenDependencyError(Exception):
    def __init__(
        self,
        identifier: str,
        error: Exception,
        parent: "ProjectDependency | None" = None,
        release: str | None = None,
    ):
        self.identifier = identifier
        self.error = error
        self.parent = parent
        self.release = release


class ProjectDependency:
    def __init__(
        self,
        spec: config.DependencySpec,
        pcfg: config.ProjectConfig | None = None,
        gcfg: config.Config | None = None,
    ):
        self.spec = spec
        self.dist: Dist | None = None
        self.gcfg = gcfg or config.config
        self.pcfg = pcfg or self.gcfg.project

        self.cfg: config.ProjectConfig | None = None

    # TODO see __eq__
    def __hash__(self) -> int:
        # used for BFS resolution
        return hash(self.spec.identifier)

    # TODO don't make property of object, but use as comparator where needed
    def __eq__(self, other: object) -> bool:
        # used for BFS resolution
        if not isinstance(other, ProjectDependency):
            return False
        if self.spec.identifier == other.spec.identifier:
            # TODO do some asserts about the equivalence
            return True
        return False

    @property
    def identifier(self) -> str:
        if self.spec.identifier is not None:
            return self.spec.identifier
        assert self.dist is not None
        return self.dist.identifier

    @property
    def project_config(self) -> config.ProjectConfig:
        if self.cfg is not None:
            return self.cfg
        assert self.dist is not None
        return self.dist.manifest

    @property
    def target_path(self) -> Path:
        # TODO don't really like using identifier as import path
        # would be nicer to use source name and indirect imports
        return self.gcfg.project.paths.modules / self.identifier

    @property
    def cache_dir(self) -> Path:
        return self.gcfg.project.paths.modules / ".cache"

    def add_to_manifest(self):
        config.ProjectConfig.set_or_add_dependency(self.gcfg, self.spec)

    def remove_from_manifest(self):
        config.ProjectConfig.remove_dependency(self.gcfg, self.spec)

    def load_dist(self):
        if self.dist is not None:
            return
        # TODO implement cache
        temp_dir = self.cache_dir
        if isinstance(self.spec, (config.FileDependencySpec, config.GitDependencySpec)):
            if isinstance(self.spec, config.FileDependencySpec):
                path = self.spec.path
                if not path.exists():
                    raise errors.UserFileNotFoundError(
                        f"Local dependency path {path} does not exist", markdown=False
                    )
            else:
                repo_cache = Path(temp_dir) / ".git_repo.cache"
                if repo_cache.exists():
                    robustly_rm_dir(repo_cache)
                try:
                    path = clone_repo(
                        self.spec.repo_url,
                        clone_target=repo_cache,
                        ref=self.spec.ref,
                    )
                except ImportError as e:
                    # no git executable
                    raise errors.UserException(
                        f"Could not clone repo {self.spec.repo_url}: {e}"
                    ) from e

                if self.spec.path_within_repo:
                    path = path / self.spec.path_within_repo

            dist = Dist.build_dist(
                cfg=path,
                output_path=Path(temp_dir),
            )
            self.spec.identifier = dist.identifier

        elif isinstance(self.spec, config.RegistryDependencySpec):
            api = PackagesAPIClient()
            requested_release = self.spec.release
            try:
                selected_release = _select_compatible_registry_release(
                    api, self.spec.identifier, requested_release
                )
                dist = api.get_release_dist(
                    self.spec.identifier,
                    Path(temp_dir),
                    version=selected_release,
                )
            except ApiErrors.ReleaseNotFoundError as e:
                raise errors.UserException(
                    f"Release not found: {self.spec.identifier}@{selected_release}"
                ) from e
            self.spec.release = dist.version
        else:
            raise NotImplementedError(f"Loading dist for {self.spec} not implemented")
        self.dist = dist

    @property
    def direct_dependencies(self) -> list["ProjectDependency"]:
        return [
            not_none(ProjectDependency(spec, pcfg=self.project_config, gcfg=self.gcfg))
            for spec in self.project_config.dependencies or []
        ]

    def try_load(self):
        if self.cfg:
            return
        if not self.target_path:
            return
        if not self.target_path.exists():
            return
        self.cfg = config.ProjectConfig.from_path(self.target_path)

    def __str__(self) -> str:
        return f"{type(self).__name__}(spec={self.spec}, path={self.target_path})"

    def __repr__(self) -> str:
        return str(self)


class ProjectDependencies:
    gcfg: config.Config | None = None

    def __init__(
        self,
        pcfg: config.ProjectConfig | None = None,
        sync_versions: bool = True,
        install_missing: bool = False,
        clean_unmanaged_dirs: bool = False,
        pin_versions: bool = False,
        update_versions: bool = False,
    ):
        if pcfg is None:
            if self.gcfg is None:
                pcfg = config.config.project
                self.gcfg = config.config
            else:
                pcfg = self.gcfg.project

        self.pcfg = pcfg

        self.direct_deps = {
            ProjectDependency(spec, pcfg=pcfg) for spec in pcfg.dependencies or []
        }

        if update_versions:
            # Update manifest specs BEFORE resolving dependencies.
            # This avoids loading/validating old installed packages that may have
            # config errors in their ato.yaml (which would fail resolution).
            if self._update_manifest_versions():
                if self.gcfg is not None:
                    self.gcfg.reload()
                    self.pcfg = self.gcfg.project
                    pcfg = self.pcfg
                self.direct_deps = {
                    ProjectDependency(spec, pcfg=pcfg)
                    for spec in pcfg.dependencies or []
                }

        self.dag = self.resolve_dependencies()

        if sync_versions:
            self.sync_versions()
        if install_missing:
            self.install_missing_dependencies()
        if clean_unmanaged_dirs:
            self.clean_unmanaged_directories()
        if pin_versions:
            self.pin_versions()

    @property
    def all_deps(self) -> set[ProjectDependency]:
        return self.dag.values

    def reload(self):
        if self.gcfg is not None:
            self.gcfg.reload()
            self.pcfg = self.gcfg.project

        self.__init__(pcfg=self.pcfg, sync_versions=False)

    @property
    def not_installed_dependencies(self) -> set[ProjectDependency]:
        return {dep for dep in self.all_deps if not dep.cfg}

    def install_missing_dependencies(self):
        for dep in self.not_installed_dependencies:
            assert dep.dist is not None
            _log_add_package(dep.identifier, dep.dist.version)
            dep.dist.install(dep.target_path)

    def clean_unmanaged_directories(self):
        module_dir = self.pcfg.paths.modules
        if not module_dir.exists():
            return
        local_dep_dirs = set()
        for owner_dir in module_dir.iterdir():
            if owner_dir.name.startswith("."):
                continue
            if not owner_dir.is_dir():
                continue
            for dep_dir in owner_dir.iterdir():
                if not dep_dir.is_dir():
                    continue
                local_dep_dirs.add(dep_dir.relative_to(module_dir))

        dep_dirs = {
            not_none(dep.target_path).relative_to(module_dir) for dep in self.all_deps
        }
        # Get the first two parts of the path (owner/repo) to use as prefixes
        dep_dir_prefixes = {Path(*dep_dir.parts[:2]) for dep_dir in dep_dirs}

        unmanaged_dirs = local_dep_dirs - dep_dir_prefixes

        for unmanaged_dir in unmanaged_dirs:
            dep_cfg = config.ProjectConfig.from_path(module_dir / unmanaged_dir)
            if dep_cfg is None or dep_cfg.package is None:
                logger.warning(f"Removing unmanaged module directory: {unmanaged_dir}")
            else:
                _log_remove_package(dep_cfg.package.identifier, dep_cfg.package.version)

            robustly_rm_dir(module_dir / unmanaged_dir)

    @staticmethod
    def _build_dep_chain(
        identifier: str,
        parent_map: dict[str, ProjectDependency],
        release: str | None = None,
    ) -> str:
        """Build a dependency chain string like 'root@1.0 → parent@2.0 → child@3.0'."""
        chain: list[str] = []
        current_id: str | None = identifier
        while current_id is not None:
            parent = parent_map.get(current_id)
            if parent is not None:
                spec = parent.spec
                if isinstance(spec, config.RegistryDependencySpec) and spec.release:
                    chain.append(f"{parent.identifier}@{spec.release}")
                else:
                    chain.append(parent.identifier)
                current_id = parent.identifier
            else:
                current_id = None
        chain.reverse()
        leaf = f"{identifier}@{release}" if release else identifier
        chain.append(leaf)
        return " → ".join(chain)

    def resolve_dependencies(self):
        dag = DAG[ProjectDependency]()
        # TODO: can be replaced with dag.values
        all_deps: set[ProjectDependency] = set()

        # Track parent relationships for error reporting
        parent_map: dict[str, ProjectDependency] = {}

        # Good old BFS for dependency resolution
        deps_to_process: list[tuple[ProjectDependency | None, ProjectDependency]] = [
            (None, dep) for dep in self.direct_deps
        ]

        acc_errors: list[BrokenDependencyError] = []
        while deps_to_process:
            to_add = []
            for parent, dep in deps_to_process:
                try:
                    # Record parent for chain reporting (first parent wins)
                    if parent is not None and dep.identifier not in parent_map:
                        parent_map[dep.identifier] = parent

                    dups = all_deps.intersection({dep})
                    assert len(dups) <= 1
                    dup = dups.pop() if dups else None
                    if dup:
                        if dup.spec != dep.spec:
                            # TODO better error
                            raise errors.UserException(
                                f"Incompatible dependency specs in tree: {dep.spec}"
                            )
                        assert parent is not None, "Can't have duplicates in root"
                        dag.add_edge(parent, dup)
                        continue

                    dep.try_load()
                    if dep.cfg is None:
                        dep.load_dist()
                    to_add.extend((dep, child) for child in dep.direct_dependencies)
                    all_deps.add(dep)
                    if parent is not None:
                        dag.add_edge(parent, dep)
                    else:
                        dag.add_or_get(dep)
                except Exception as e:
                    release = (
                        dep.spec.release
                        if isinstance(dep.spec, config.RegistryDependencySpec)
                        else None
                    )
                    acc_errors.append(
                        BrokenDependencyError(
                            dep.identifier, e, parent=parent, release=release
                        )
                    )

            deps_to_process.clear()
            deps_to_process.extend(to_add)
        if acc_errors:
            error_list = []
            for e in acc_errors:
                chain = self._build_dep_chain(e.identifier, parent_map, e.release)
                error_list.append(f"{chain}: {e.error}")
            raise errors.UserException(f"Broken dependencies:\n {md_list(error_list)}")

        if dag.contains_cycles:
            # TODO better error
            raise errors.UserException("Cycle in dependencies")

        assert dag.values == all_deps
        return dag

    def remove(self, spec: config.DependencySpec):
        raise NotImplementedError("Removing dependencies is not implemented")

    def install_from_spec_to_manifest(
        self, dep: ProjectDependency, upgrade: bool = False
    ):
        # loaded identifier from dist
        identifier = dep.identifier

        existing_dep = find_or(
            self.dag.values,
            lambda d: not_none(d).identifier == identifier,
            default=None,
        )

        if existing_dep is not None:
            existing_dep.spec = config.DependencySpec.from_str(str(dep.spec))
            if type(existing_dep.spec) is not type(dep.spec):
                raise errors.UserException(
                    f"Cannot install {identifier} as it is already installed "
                    f"from a different source: {existing_dep.spec}"
                )
            if (
                isinstance(dep.spec, config.RegistryDependencySpec)
                and isinstance(existing_dep.spec, config.RegistryDependencySpec)
                and dep.spec.release != existing_dep.spec.release
            ):
                if existing_dep not in self.direct_deps:
                    parents = self.dag.all_parents(existing_dep)
                    direct_parents = parents & self.direct_deps
                    parent_list = (
                        md_list([dep.identifier for dep in direct_parents])
                        if direct_parents
                        else "unknown"
                    )
                    existing_version = (
                        existing_dep.spec.release
                        or (existing_dep.dist.version if existing_dep.dist else None)
                        or (
                            existing_dep.cfg.package.version
                            if existing_dep.cfg and existing_dep.cfg.package
                            else None
                        )
                        or "unknown"
                    )
                    raise errors.UserException(
                        f"Cannot install {identifier} as it is already installed "
                        f"with a different version from a transitive dependency: "
                        f"{existing_version}\n\nRequired by:\n{parent_list}"
                    )
                if not upgrade:
                    raise errors.UserException(
                        f"Cannot install {identifier} as it is already installed "
                        f"with a different version: {existing_dep.spec.release}. "
                        f"Use --upgrade to install anyway."
                    )
            if isinstance(
                existing_dep.spec,
                (config.FileDependencySpec, config.GitDependencySpec),
            ):
                if not upgrade:
                    raise errors.UserException(
                        f"Cannot install {identifier} as it is already installed. "
                        f"Use --upgrade to install anyway."
                    )

        target_path = dep.target_path
        if target_path.exists():
            robustly_rm_dir(target_path)

        dep.load_dist()
        assert dep.dist is not None

        dep.dist.install(target_path)
        dep.add_to_manifest()
        _log_add_package(dep.identifier, dep.dist.version)

    def add_dependencies(self, *specs: config.DependencySpec, upgrade: bool = False):
        # Load specs and fetch dists if needed
        new_deps = []
        for spec in specs:
            dep = ProjectDependency(spec)
            if dep.spec.identifier is None:
                try:
                    dep.load_dist()
                except DistValidationError as e:
                    raise errors.UserException(
                        f"Could not load distribution for {spec}: {e}"
                    ) from e
            new_deps.append(dep)

        # Check for duplicates
        dups = duplicates(new_deps, lambda x: x.spec.identifier)
        if dups:
            raise errors.UserException(f"Duplicate specs provided: {dups}")

        # Check if in manifest and/or already installed
        # install locally and in manifest
        for dep in new_deps:
            self.install_from_spec_to_manifest(dep, upgrade=upgrade)

        self.reload()

    def remove_dependencies(self, *identifiers: str):
        all_deps_by_identifier = {dep.identifier: dep for dep in self.all_deps}

        to_remove = {
            identifier: all_deps_by_identifier.get(identifier)
            for identifier in identifiers
            if identifier in all_deps_by_identifier
        }

        not_found = [item for item in to_remove.items() if item[1] is None]
        if not_found:
            raise errors.UserException(
                "Could not find dependencies to remove:"
                f" {md_list(dict(not_found).keys())}"
            )
        to_remove_deps = cast(set[ProjectDependency], set(to_remove.values()))

        non_root_deps = to_remove_deps - self.direct_deps
        if non_root_deps:
            raise errors.UserException(
                "Cannot remove dependencies"
                " that are not direct dependencies of this project:"
                f"\n{md_list(non_root_deps)}"
            )

        uninstall = set[ProjectDependency]()
        no_uninstall = set[ProjectDependency]()
        for dep in to_remove_deps:
            transitive_removals = self.dag.all_parents(dep)
            # direct project dependencies that depend on a to_be_removed dependency
            # and are not to_be_removed themselves
            non_removable = (transitive_removals - to_remove_deps) & self.direct_deps
            if non_removable:
                no_uninstall.add(dep)
                continue
            uninstall.add(dep)

        if no_uninstall:
            logger.info(
                f"Will remove dependencies but not uninstall following packages as they"
                f" are required by downstream dependencies:"
                f"\n{md_list([dep.identifier for dep in no_uninstall])}",
                extra={"markdown": True},
            )

        for dep in to_remove_deps:
            dep.remove_from_manifest()
            _log_remove_package(dep.identifier, dep.dist.version if dep.dist else None)

        for dep in uninstall:
            if dep.target_path.exists():
                robustly_rm_dir(dep.target_path)

        # reload and clean orphaned packages
        self.reload()
        self.clean_unmanaged_directories()

    def sync_versions(self):
        """
        Ensure that installed dependency versions match the manifest
        """

        def _sync_dep(dep: ProjectDependency, installed_version: str) -> bool:
            dep.load_dist()
            assert dep.dist is not None

            if dep.dist.version == installed_version:
                return False

            target_path = dep.target_path
            if target_path.exists():
                _log_remove_package(dep.identifier, installed_version)
                robustly_rm_dir(target_path)

            _log_add_package(dep.identifier, dep.dist.version)
            dep.dist.install(target_path)
            return True

        dirty = False
        for dep in self.direct_deps:
            match dep.spec.type:
                case "registry":
                    if dep.cfg is None or dep.cfg.package is None:
                        installed_version = "<unknown>"
                    else:
                        installed_version = dep.cfg.package.version

                    spec = cast(config.RegistryDependencySpec, dep.spec)
                    desired_version = spec.release

                    if installed_version != desired_version:
                        logger.info(
                            f"Syncing {dep.identifier}: "
                            f"{installed_version} -> {desired_version}"
                        )
                        dirty |= _sync_dep(dep, installed_version)

                case "file" | "git":
                    logger.warning(
                        f"Ignoring possible changes to {dep.identifier} "
                        f"({dep.spec.type} dependency)"
                    )
                    continue
                case _:
                    raise NotImplementedError(
                        f"Syncing versions for {dep.spec.type} not implemented"
                    )

        if dirty:
            self.reload()
            self.clean_unmanaged_directories()

    def pin_versions(self):
        """
        Pin any unpinned registry dependencies to their current installed versions
        """
        for dep in self.direct_deps:
            if (
                isinstance(dep.spec, config.RegistryDependencySpec)
                and dep.cfg is not None
                and dep.cfg.package is not None
            ):
                dep.spec.release = dep.cfg.package.version
                dep.add_to_manifest()
                _log_pin_package(dep.identifier, dep.cfg.package.version)

    def _clear_all_installed_packages(self) -> None:
        """
        Remove all installed package directories from the modules folder.

        Preserves hidden directories (like .cache) but removes all owner/package
        directories. This ensures a clean slate for dependency resolution.
        """
        module_dir = self.pcfg.paths.modules
        if not module_dir.exists():
            return

        for owner_dir in module_dir.iterdir():
            # Skip hidden directories (e.g., .cache)
            if owner_dir.name.startswith("."):
                continue
            if not owner_dir.is_dir():
                continue
            # Remove the entire owner directory (contains all packages from that owner)
            robustly_rm_dir(owner_dir)

    def _update_manifest_versions(self) -> bool:
        """
        Update registry dependency specs in the manifest to their latest
        compatible versions. Returns True if any specs were changed.

        Removes ALL installed package directories (including transitive
        dependencies) so that resolve_dependencies() downloads fresh copies.
        This ensures nested dependencies are updated when their parent's
        required version changes.
        """
        # Clear all installed packages first - this ensures transitive
        # dependencies are also removed and will be re-downloaded with
        # the correct versions required by their updated parents.
        self._clear_all_installed_packages()

        api = PackagesAPIClient()
        dirty = False
        for dep in self.direct_deps:
            if not isinstance(dep.spec, config.RegistryDependencySpec):
                continue
            # Pass None to get the latest compatible release (fallback behavior)
            latest_version = _select_compatible_registry_release(
                api, dep.spec.identifier, None
            )
            if dep.spec.release != latest_version:
                logger.info(
                    f"Updating {dep.spec.identifier}: "
                    f"{dep.spec.release or '<unpinned>'} -> {latest_version}"
                )
                dep.spec.release = latest_version
                dep.add_to_manifest()
                dirty = True

        return dirty

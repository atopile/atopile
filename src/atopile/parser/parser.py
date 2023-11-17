import concurrent.futures
import logging
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import List

from atopile.model.accessors import ModelVertexView
from atopile.model.differ import Delta
from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.utils import generate_edge_uid
from atopile.model2.errors import AtoError, write_errors_to_log, ReraiseBehavior
from atopile.model2.parse import parse_file as parse_file2
from atopile.parser.AtopileParser import AtopileParser
from atopile.parser.AtopileParserVisitor import AtopileParserVisitor
from atopile.project.config import BuildConfig
from atopile.project.project import Project
from atopile.utils import profile

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Builder(AtopileParserVisitor):
    def __init__(self, project: Project) -> None:
        self.model = Model()
        self.project = project

        self._block_stack: List[str] = []
        self._file_stack: List[Path] = []

        self._tree_cache = {}

        # if something's in parsed files, we must skip building it a second time
        super().__init__()

    @property
    def current_block(self) -> str:
        return self._block_stack[-1]

    @property
    def current_file(self):
        return self._file_stack[-1]

    @contextmanager
    def working_block(self, ref: str):
        self._block_stack.append(ref)
        yield
        self._block_stack.pop()

    @contextmanager
    def working_file(self, abs_path: Path):
        std_path = self.project.standardise_import_path(abs_path)
        self._file_stack.append(abs_path)
        with self.working_block(str(std_path)):
            yield
        self._file_stack.pop()
        self.model.src_files.append(std_path)

    def parse_file(self, abs_path: Path):
        if str(abs_path) in self._tree_cache:
            return self._tree_cache[str(abs_path)]

        tree = parse_file2(abs_path)

        self._tree_cache[str(abs_path)] = tree
        return tree

    def build(self, path: Path) -> Model:
        """
        Start the build from the specified file.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        abs_path = path.resolve().absolute()

        std_path = self.project.standardise_import_path(abs_path)
        std_path_str = str(std_path)

        tree = self.parse_file(abs_path)

        self.model.new_vertex(VertexType.file, std_path_str)
        self.model.data[std_path_str] = {}

        with self.working_file(abs_path):
            self.visit(tree)

        return self.model

    def visitImport_stmt(self, ctx: AtopileParser.Import_stmtContext):
        filepath_to_import = self.get_string(ctx.string())

        try:
            potentially_sub_project = Project.from_path(self.current_file)
        except FileNotFoundError:
            additional_search_paths = None
        else:
            additional_search_paths = [potentially_sub_project.root]

        try:
            abs_path, std_path = self.project.resolve_import(
                filepath_to_import, self.current_file, additional_search_paths
            )
        except FileNotFoundError as ex:
            raise AtoError(
                f"Couldn't find file: {ex.args[0]}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        import_filename = str(std_path)

        if std_path in self._file_stack:
            raise AtoError(
                f"Circular import detected: {std_path}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        if std_path not in self.model.src_files:
            # do the actual import, parsing etc...
            with self.working_file(abs_path):
                tree = self.parse_file(abs_path)
                self.model.new_vertex(VertexType.file, import_filename)
                self.model.data[import_filename] = {}
                super().visit(tree)

        # link the import to the current block
        to_import = ctx.name_or_attr().getText()
        try:
            graph_path, data_path = self.model.find_ref(to_import, import_filename)
        except KeyError as ex:
            raise AtoError(
                ex.args[0],
                self.current_file,
                ctx.start.line,
                ctx.start.column
            ) from ex
        if data_path:
            raise AtoError(
                f"Cannot import data path {data_path}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        self.model.new_edge(EdgeType.imported_to, graph_path, self.current_block)

        # the super().visit() in the new file import section should
        # handle all depth required. From here, we always want to go back up
        return None

    def visitBlockdef(self, ctx: AtopileParser.BlockdefContext):
        block_type_name = ctx.blocktype().getText()
        try:
            block_type = VertexType(block_type_name)
        except ValueError as ex:
            raise AtoError(
                f"Unknown block type {block_type_name}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        # name -> the naem of the block being defined
        name = ctx.name().getText()

        # make sure we're defining this block from the root of the file
        if (
            ModelVertexView.from_path(self.model, self.current_block).vertex_type
            != VertexType.file
        ):
            raise AtoError(
                f"Cannot define a block inside another block ({self.current_block}).",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        if ctx.FROM():
            # we're subclassing something
            # find what we're subclassing
            from_obj = ctx.name_or_attr()
            if not from_obj:
                raise AtoError(
                    "Subclass must specify a superclass, but none specified",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )
            try:
                superclass_path, data_path = self.model.find_ref(
                    from_obj.getText(), self.current_block
                )
            except KeyError as ex:
                raise AtoError(
                    ex.args[0],
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                ) from ex

            if data_path:
                raise AtoError(
                    "Cannot subclass data object",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )

            # we're allowed to make modules into components, but not visa-versa
            # otherwise the class-type must be the same fundemental type as the superclass
            superclass = ModelVertexView.from_path(self.model, superclass_path)
            allowed_subclass_types = [superclass.vertex_type]
            if superclass.vertex_type == VertexType.module:
                allowed_subclass_types += [VertexType.component]

            if block_type not in allowed_subclass_types:
                allowed_subclass_types_friendly = " or ".join(
                    e.value for e in allowed_subclass_types
                )
                raise AtoError(
                    f"Superclass is a {superclass.vertex_type.value}, the subclass is trying to be a {block_type.value}, but must be a {allowed_subclass_types_friendly}",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )

            # make the noise!
            block_path = self.model.subclass_block(
                block_type, superclass_path, name, self.current_block
            )
        else:
            # we're not subclassing anything
            block_path = self.model.new_vertex(
                block_type, name, part_of=self.current_block
            )

        self.model.data[block_path] = {}

        with self.working_block(block_path):
            return super().visitChildren(ctx)

    def visitPindef_stmt(self, ctx: AtopileParser.Pindef_stmtContext):
        if ctx.name() is not None:
            name = ctx.name().getText()
        elif ctx.totally_an_integer() is not None:
            name = ctx.totally_an_integer().getText()
            try:
                int(name)
            except ValueError as ex:
                raise AtoError(
                    "Pindef_stmt must have a name or integer",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                ) from ex

        else:
            raise AtoError(
                "Pindef_stmt must have a name or integer",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        pin_path = self.model.new_vertex(
            VertexType.pin, name, part_of=self.current_block
        )
        self.model.data[pin_path] = {}

        return super().visitPindef_stmt(ctx)

    def visitSignaldef_stmt(self, ctx: AtopileParser.Signaldef_stmtContext):
        name = ctx.name().getText()

        if ctx.PRIVATE():
            private = True
        else:
            private = False

        signal_path = self.model.new_vertex(
            VertexType.signal, name, part_of=self.current_block
        )
        self.model.data[signal_path] = {
            "private": private,
        }

        return super().visitSignaldef_stmt(ctx)

    def deref_totally_an_integer(
        self, ctx: AtopileParser.Totally_an_integerContext
    ) -> str:
        try:
            int(ctx.getText())
        except ValueError as ex:
            raise AtoError(
                "Numerical pin reference must be an integer, but seems you stuck something else in there somehow?",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex
        return ctx.getText()

    def deref_connectable(self, ctx: AtopileParser.ConnectableContext) -> str:
        if ctx.name_or_attr():
            ref = ctx.name_or_attr().getText()
        elif ctx.signaldef_stmt():
            ref = ctx.signaldef_stmt().name().getText()
        elif ctx.pindef_stmt():
            if ctx.pindef_stmt().name():
                ref = ctx.pindef_stmt().name().getText()
            elif ctx.pindef_stmt().totally_an_integer():
                # here we don't care about the result, we're just using the function to check it's an integer
                self.deref_totally_an_integer(ctx.pindef_stmt().totally_an_integer())
                ref = ctx.pindef_stmt().totally_an_integer().getText()
            else:
                raise AtoError(
                    "Cannot connect to this type of object",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )
        elif ctx.numerical_pin_ref():
            # same as above, we don't care about the result
            self.deref_totally_an_integer(ctx.numerical_pin_ref().totally_an_integer())
            ref = ctx.numerical_pin_ref().getText()
        else:
            raise AtoError(
                "Cannot connect to this type of object",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        try:
            cn_path, cn_data = self.model.find_ref(ref, self.current_block)
        except KeyError as ex:
            raise AtoError(
                f"Cannot connect to non-existent object {ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        if cn_data:
            raise AtoError(
                f"Cannot connect to data object {ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )
        return cn_path

    def visitConnect_stmt(self, ctx: AtopileParser.Connect_stmtContext):
        # visit the connectables now before attempting to make a connection
        result = self.visitChildren(ctx)
        connectables = ctx.connectable()

        if len(connectables) != 2:
            raise AtoError(
                "Connect statement must have two connectables",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        # figure out what we're trying to connect
        from_path = self.deref_connectable(ctx.connectable(0))
        to_path = self.deref_connectable(ctx.connectable(1))

        # check typing to the connectables
        from_mvv = ModelVertexView.from_path(self.model, from_path)
        to_mvv = ModelVertexView.from_path(self.model, to_path)

        basic_node_types = (VertexType.pin, VertexType.signal)
        if (
            to_mvv.vertex_type in basic_node_types
            and from_mvv.vertex_type in basic_node_types
        ):
            # simple case, we don't care, connect 'em on up
            joining_pairs = [
                (from_path, to_path)
            ]
        elif from_mvv.vertex_type == to_mvv.vertex_type == VertexType.interface and (
            to_mvv.i_am_an_instance_of(from_mvv.instance_of)
            or from_mvv.i_am_an_instance_of(to_mvv.instance_of)
        ):
            # match interfaces based on node name
            common_node_names = {
                mvv.ref for mvv in from_mvv.get_descendants(list(VertexType))
            } & {
                mvv.ref for mvv in to_mvv.get_descendants(list(VertexType))
            }

            from_path = from_mvv.path
            to_path = to_mvv.path

            joining_pairs = [
                (from_path + "." + ref, to_path + "." + ref) for ref in common_node_names
            ]

        else:
            raise AtoError(
                f"Cannot connect {from_mvv.vertex_type.value} to {to_mvv.vertex_type.value}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        # make the noise
        for i_from_path, i_to_path in joining_pairs:
            uid = generate_edge_uid(i_from_path, i_to_path, self.current_block)
            self.model.new_edge(EdgeType.connects_to, i_from_path, i_to_path, uid=uid)
            self.model.data[uid] = {
                "defining_block": self.current_block,
            }

        # children are already vistited
        return result

    def visitWith_stmt(self, ctx: AtopileParser.With_stmtContext):
        with_ref = ctx.name_or_attr().getText()
        with_path, _ = self.model.find_ref(with_ref, self.current_block)

        self.model.enable_option(with_path)

        return super().visitWith_stmt(ctx)

    def visitAssign_stmt(self, ctx: AtopileParser.Assign_stmtContext):
        assignee = ctx.name_or_attr().getText()
        assignable: AtopileParser.AssignableContext = ctx.assignable()

        if assignable.new_stmt():
            class_ref = assignable.new_stmt().name_or_attr().getText()
            try:
                class_path, _ = self.model.find_ref(class_ref, self.current_block)
            except KeyError as ex:
                raise AtoError(
                    ex.args[0],
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                ) from ex

            # NOTE: we're not using the assignee here because we actually want that error until this is fixed properly
            instance_name_obj = ctx.name_or_attr().name()
            if instance_name_obj is None:
                raise AtoError(
                    "Cannot assign new object to an attribute (eg. a.b.c), must be to a name (eg. c)",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )
            self.model.instantiate_block(
                class_path, instance_name_obj.getText(), self.current_block
            )
        else:
            if assignable.string():
                value = self.get_string(assignable.string())
            elif assignable.NUMBER():
                value = float(assignable.NUMBER().getText())
            elif assignable.boolean_():
                value = bool(assignable.boolean_().getText())
            else:
                raise AtoError(
                    "Only strings and numbers are supported",
                    self.current_file,
                    ctx.start.line,
                    ctx.start.column,
                )

            graph_path, existing_data_path, remaining_parts = self.model.find_ref(
                assignee, self.current_block, return_unfound=True
            )
            data_path = existing_data_path + remaining_parts
            data = self.model.data[graph_path]
            for p in data_path[:-1]:
                data = data.setdefault(p, {})

            data[data_path[-1]] = value

        return super().visitAssign_stmt(ctx)

    def get_string(self, ctx: AtopileParser.StringContext) -> str:
        return ctx.getText().strip("\"'")

    def visitRetype_stmt(self, ctx: AtopileParser.Retype_stmtContext):
        """
        This statement type will replace an existing block with a new one of a subclassed type

        Since there's no way to delete elements, we can be sure that the subclass is
        a superset of the superclass (confusing linguistically, makes sense logically)
        """
        # first, let's get all the data out of this replacement statement and validate it
        retype_ref = ctx.name_or_attr(0).getText()
        new_type_ref = ctx.name_or_attr(1).getText()

        try:
            retype_path, retype_data = self.model.find_ref(
                retype_ref, self.current_block
            )
        except KeyError as ex:
            raise AtoError(
                f"Cannot retype non-existent object {retype_ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        if retype_data:
            raise AtoError(
                f"Cannot retype data object {retype_ref}. Provide a path to the object you want to retype instead.",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        try:
            new_type_path, new_type_data = self.model.find_ref(
                new_type_ref, self.current_block
            )
        except KeyError as ex:
            raise AtoError(
                f"Cannot use new type of non-existant object {new_type_ref}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            ) from ex

        if new_type_data:
            raise AtoError(
                f"Cannot use data object as new type {new_type_ref}. Please provide a path to the class you want to use instead.",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        retype_mvv = ModelVertexView.from_path(self.model, retype_path)
        new_type_mvv = ModelVertexView.from_path(self.model, new_type_path)

        # check retype is an instance of a superclass of the new type (which is a class)
        if not retype_mvv.is_instance:
            raise AtoError(
                f"Can only retype instances of things, but {retype_ref} is a class",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )
        if not new_type_mvv.is_class:
            raise AtoError(
                f"Can only retype to a class, but {new_type_ref} is an instance",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )
        if retype_mvv.instance_of not in new_type_mvv.superclasses:
            raise AtoError(
                f"Cannot retype {retype_ref} to {new_type_ref}. {new_type_ref} must be a subclass of {retype_mvv.instance_of.path}",
                self.current_file,
                ctx.start.line,
                ctx.start.column,
            )

        # okay, now we can actually get on with the retyping
        # first, we're going to diff the changes between the original class and the updated class
        # then, we're going to diff the user has made to the standing instance, compared to the original class
        # we're then going to apply the diffs, preferencing changes the user has manually made
        class_diff = Delta.diff(retype_mvv.instance_of, new_type_mvv)
        instance_diff = Delta.diff(retype_mvv.instance_of, retype_mvv)

        combined_diff = Delta.combine_diff(class_diff, instance_diff)

        # remove the "part_of" edge from the diff
        # we know there's only one of these so we can break once we find it
        for k, v in combined_diff.edge.items():
            if k[0] == () and v == EdgeType.part_of:
                del combined_diff.edge[k]
                break

        # apply the diff to the instance
        combined_diff.apply_to(retype_mvv)

        # finally we need to change the "instance_of" link to point to the new class
        instance_of_eid = self.model.graph.es.find(
            _source=retype_mvv.index, type_eq=EdgeType.instance_of.name
        )
        self.model.graph.delete_edges(instance_of_eid)
        self.model.new_edge(EdgeType.instance_of, retype_path, new_type_path)

        return super().visitRetype_stmt(ctx)


class ParallelParser(AtopileParserVisitor):
    def __init__(
        self,
        bob: Builder,
        current_file: Path,
        futures_to_path: dict[concurrent.futures.Future, Path],
        executor: concurrent.futures.ThreadPoolExecutor,
        accounted_for_files: set[Path],
        accounted_for_files_lock: threading.Lock,
    ) -> None:
        self._bob = bob
        self._current_file = current_file
        self._futures_to_path = futures_to_path
        self._executor = executor
        self._accounted_for_files = accounted_for_files
        self._accounted_for_files_lock = accounted_for_files_lock

    def _parse(self, abs_path: Path):
        tree = self._bob.parse_file(abs_path)
        log.info(f"Finished parsing {str(abs_path)}")
        self.visit(tree)

    def visitImport_stmt(self, ctx: AtopileParser.Import_stmtContext):
        import_filename = self._bob.get_string(ctx.string())

        abs_path, _ = self._bob.project.resolve_import(
            import_filename, self._current_file
        )

        self._accounted_for_files_lock.acquire(timeout=10)
        try:
            if abs_path in self._accounted_for_files:
                return
            self._accounted_for_files.add(abs_path)
        finally:
            self._accounted_for_files_lock.release()

        new_parser = ParallelParser(
            self._bob,
            abs_path,
            self._futures_to_path,
            self._executor,
            self._accounted_for_files,
            self._accounted_for_files_lock,
        )
        self._futures_to_path[
            self._executor.submit(new_parser._parse, abs_path)
        ] = abs_path

    @staticmethod
    def pre_parse(bob: Builder, root_file: Path):
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            future_to_path: dict[concurrent.futures.Future, Path] = {}
            seed_parser = ParallelParser(
                bob,
                root_file,
                future_to_path,
                executor,
                set(),
                threading.Lock(),
            )
            future_to_path[executor.submit(seed_parser._parse, root_file)] = root_file

            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                log.info(f"Finished parsing {str(path)}")


def build_model(project: Project, config: BuildConfig) -> Model:
    log.info("Building model")
    skip_profiler = log.getEffectiveLevel() > logging.DEBUG

    with profile(profile_log=log, skip=skip_profiler):
        bob = Builder(project)
        try:
            with write_errors_to_log(Builder, log, ReraiseBehavior.RAISE_ATO_ERROR):
                model = bob.build(config.root_file)
        except AtoError:
            log.error("Stopping due to error.")
            sys.exit(1)

    return model

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

from attrs import define, field
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from atopile.model.accessors import ModelVertexView
from atopile.targets.netlist.nets import find_net_names, generate_net_name
from atopile.model.model import EdgeType, Model, VertexType
from atopile.model.utils import generate_uid_from_path
from atopile.targets.targets import Target, TargetCheckResult, TargetMuster

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

@define
class KicadField:
    name: str  # eg?
    value: str  # eg?

@define
class KicadPin:
    """
    eg. (pin (num "1") (name "") (type "passive"))
    """
    num: str
    name: str = ""
    type: str = ""

@define
class KicadLibpart:
    """
    eg.
    (libpart (lib "Device") (part "R")
      (description "Resistor")
      (docs "~")
      (footprints
        (fp "R_*"))
      (fields
        (field (name "Reference") "R")
        (field (name "Value") "R")
        (field (name "Datasheet") "~"))
      (pins
        (pin (num "1") (name "") (type "passive"))
        (pin (num "2") (name "") (type "passive"))))
    """
    lib: str
    part: str
    description: str
    docs: str
    footprints: List[str] = field(factory=list)
    fields: List[KicadField] = field(factory=list)
    pins: List[KicadPin] = field(factory=list)

@define
class KicadSheetpath:
    """
    eg. (sheetpath (names "/") (tstamps "/"))
    """
    names: str = "/" # module path, eg. toy.ato/Vdiv1
    tstamps: str = "/" # module UID, eg. b1d41e3b-ef4b-4472-9aa4-7860376ef0ce

@define
class KicadComponent:
    """
    eg.
    (comp (ref "R4")
      (value "R")
      (libsource (lib "Device") (part "R") (description "Resistor"))
      (property (name "Sheetname") (value ""))
      (property (name "Sheetfile") (value "example.kicad_sch"))
      (sheetpath (names "/") (tstamps "/"))
      (tstamps "9c26a741-12df-4e56-baa6-794e6b3aa7cd")))
    """
    ref: str  # eg. "R1" -- should be unique, we should assign these here I think
    value: str  # eg. "10k" -- seems to be an arbitary string
    libsource: KicadLibpart
    tstamp: str  # component UID, eg. b1d41e3b-ef4b-4472-9aa4-7860376ef0ce
    src_path: str
    footprint: Optional[str] = None # eg. "Resistor_SMD:R_0603_1608Metric"
    properties: List[KicadField] = field(factory=list)
    fields: List[KicadField] = field(factory=list)
    sheetpath: KicadSheetpath = field(factory=KicadSheetpath)

class KicadNode:
    """
    eg. (node (ref "R1") (pin "1") (pintype "passive"))
    """
    def __init__(self, component: KicadComponent, pin: KicadPin) -> None:
        self._component = component
        self._pin = pin

    @property
    def ref(self) -> str:
        return self._component.ref

    @property
    def pin(self) -> str:
        return self._pin.num

    @property
    def pintype(self) -> str:
        return self._pin.type

@define
class KicadNet:
    """
    eg.
    (net (code "1") (name "Net-(R1-Pad1)")
      (node (ref "R1") (pin "1") (pintype "passive"))
      (node (ref "R2") (pin "1") (pintype "passive")))
    """
    code: str  # TODO: do these have to be numbers, or can they be more UIDs?
    name: str
    nodes: List[KicadNode] = field(factory=list)

class KicadLibraries:
    """
    eg.
    (libraries
    (library (logical "Device")
      (uri "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols//Device.kicad_sym")))
    """
    def __init__(self):
        # don't believe these are mandatory and I don't think they're useful in the context of atopile
        raise NotImplementedError

@define
class KicadNetlist:
    version: str = "E"  # What does this mean?
    source: str = "unknown"  # eg. "/Users/mattwildoer/Projects/SizzleSack/schematic/sandbox.py" TODO: point this at the sourcefile
    date: str = ""  # NOTE: we don't want a data in here because it'll make a diff in our outputs -- although perhaps it's a useful field for a hash here
    tool: str = "atopile"  # TODO: add version in here too

    components: List[KicadComponent] = field(factory=list)
    libparts: List[KicadLibpart] = field(factory=list)
    nets: List[KicadNet] = field(factory=list)
    """
    (net (code "3") (name "Net-(R2-Pad2)")
      (node (ref "R2") (pin "2") (pintype "passive"))
      (node (ref "R3") (pin "1") (pintype "passive"))
      (node (ref "R4") (pin "1") (pintype "passive")))
    """

    def to_file(self, path: Path) -> None:
        # Create a Jinja2 environment
        # this_dir = Path(__file__).parent
        this_dir = Path(__file__).parent
        env = Environment(loader=FileSystemLoader(this_dir), undefined=StrictUndefined)

        # Create the complete netlist
        template = env.get_template("kicad6.j2")
        netlist_str = template.render(nl=self)

        with path.open("w") as f:
            f.write(netlist_str)

    @classmethod
    def from_model(
        cls,
        model: Model,
        root_node: str,
        designators: Dict[str, str],
        components_to_lib_map: dict[str, str],
        target: "Kicad6NetlistTarget",
    ) -> "KicadNetlist":
        """
        :param model: to generate the netlist from
        :param main: path in the graph to compile from
        """
        netlist = cls()

        # Extract the components under "main"
        NON_FIELD_DATA = ["value", "footprint", "designator_prefix"]

        # Extract the components under "main"
        # TODO: move at least large chunks of this elsewhere. It's too entangled with the guts of the Model class
        part_of_view = model.get_graph_view([EdgeType.part_of])
        instance_of_view = model.get_graph_view([EdgeType.instance_of])
        main_vertex = model.graph.vs.find(path_eq=root_node)
        vidxs_within_main = part_of_view.subcomponent(main_vertex.index, mode="in")

        component_vs = model.graph.vs[vidxs_within_main].select(type_eq=VertexType.component.name)
        root_mvv = ModelVertexView.from_path(model, root_node)
        component_mvvs = {component_vs["path"]: ModelVertexView(model, component_vs.index) for component_vs in component_vs}

        component_class_vidxs: Dict[str, int] = {}  # by component path
        for component_v in component_vs:
            component_class_vidx = instance_of_view.neighbors(component_v.index, mode="out")
            if len(component_class_vidx) < 1:
                component_class_vidxs[component_v["path"]] = component_v.index
            else:
                component_class_vidxs[component_v["path"]] = component_class_vidx[0]

        unique_component_class_vidxs = set(component_class_vidxs.values())

        # Create all the pins under main
        pins_by_path: Dict[str, KicadPin] = {}  # by component class's pin path
        pins_by_ref_by_component: Dict[str, Dict[str, KicadPin]] = {}  # by component class's pin path
        for component_class_idx in unique_component_class_vidxs:
            component_class_v = model.graph.vs[component_class_idx]
            component_class_path = component_class_v["path"]
            vidxs_within_component_class = part_of_view.subcomponent(component_class_idx, mode="in")
            pin_vs = model.graph.vs[vidxs_within_component_class].select(type_eq=VertexType.pin.name)

            for pin_v in pin_vs:
                pin_ref = pin_v["ref"].lstrip("p")
                pin = KicadPin(
                    num=pin_ref,
                    name=pin_ref,
                    type="",   # TODO:
                )

                pins_by_path[pin_v["path"]] = pin
                pins_by_ref_by_component.setdefault(component_class_path, {})[pin_v["ref"]] = pin

        # Create the libparts (~component_classes)
        libparts: Dict[str, KicadLibpart] = {}  # by component class path

        for component_class_idx in unique_component_class_vidxs:
            component_class_v = model.graph.vs[component_class_idx]
            component_class_path = component_class_v["path"]
            vidxs_within_component_class = part_of_view.subcomponent(component_class_v.index, mode="in")

            # Create the pins
            pin_vs_within_component_class = model.graph.vs[vidxs_within_component_class].select(type_eq=VertexType.pin.name)
            pin_paths_within_component_class = pin_vs_within_component_class["path"]
            component_class_pins = [pins_by_path[p] for p in pin_paths_within_component_class]

            fields = [KicadField(k, v) for k, v in model.data.get(component_class_path, {}).items() if k not in NON_FIELD_DATA]

            # Create the libpart
            libpart = KicadLibpart(
                lib=component_class_path,  # FIXME: this may require sanitisation (eg. no slashes, for Kicad)
                part=component_class_v["ref"],
                description=component_class_v["ref"],  # recycle ref here. TODO: should we consdier python-like doc-strings?
                fields=fields,
                pins=component_class_pins,
                # TODO: something better for these:
                docs="~",
                footprints=["*"],
            )

            libparts[component_class_path] = libpart

        # Create the component instances
        components: Dict[str, KicadComponent] = {}  # by component path
        nodes: Dict[str, KicadNode] = {}  # by component pin path
        for component_v in component_vs:
            # there should always be at least one parent, even if only the file
            component_mvv = ModelVertexView(model, component_v.index)
            component_parent_mvv = component_mvv.parent

            component_path = component_v["path"]
            component_class_idx = component_class_vidxs[component_path]
            component_class_v = model.graph.vs[component_class_idx]
            component_class_path = component_class_v["path"]

            component_data = component_mvv.get_all_data()
            if component_data is not None:
                fields = [KicadField(k, v) for k, v in component_data.items() if k not in NON_FIELD_DATA]

            sheetpath = KicadSheetpath(
                names=component_parent_mvv.path,
                tstamps=generate_uid_from_path(component_parent_mvv.path),
            )

            # figure out the designators
            designator = designators[root_mvv.relative_path(component_mvvs[component_path])]
            try:
                footprint = component_data["footprint"]
            except KeyError:
                log.error("Component %s has no footprint", component_path)
                target.elevate_check_result(TargetCheckResult.UNSOLVABLE)
                continue

            # if there is a 'lib:' prefix, strip it
            #TODO: this is a bit of a hack, we should clean up the libs and delete this
            footprint_path = ""
            if footprint.startswith("lib:"):
                footprint = footprint[4:]
            if ":" in footprint:
                footprint_path = footprint
            else:
                try:
                    footprint_lib_name = components_to_lib_map[component_path]
                except KeyError:
                    log.error("Component %s has no lib", component_path)
                    target.elevate_check_result(TargetCheckResult.UNSOLVABLE)
                    continue
                footprint_path = f"{footprint_lib_name}:{footprint}"

            # make the component of your dreams
            component = KicadComponent(
                ref=designator,
                value=component_data.get("value", ""),
                footprint=footprint_path,
                libsource=libparts[component_class_path],
                tstamp=generate_uid_from_path(component_path),
                fields=fields,
                sheetpath=sheetpath,
                src_path=component_path,
            )

            components[component_path] = component

            # Generate the component's nodes
            # FIXME: all the components are referencing back to their components class's pins
            pins_by_ref = pins_by_ref_by_component[component_class_path]
            for ref, pin in pins_by_ref.items():
                # FIXME: this manual path generation is what got us into strife in the first place... don't do it
                nodes[f"{component_path}.{ref}"] = KicadNode(component=component, pin=pin)

        if target.check_result == TargetCheckResult.UNSOLVABLE:
            raise ResourceWarning("Not generating netlist because of unsolvable errors")

        # Create the nets
        electrical_graph = model.get_graph_view([EdgeType.connects_to])
        electrical_graph_within_main = electrical_graph.subgraph(vidxs_within_main)
        clusters = electrical_graph_within_main.connected_components(mode="weak")
        nets = []

        # TODO: slapping this on the side to unblock Narayan's layout
        # This deserves rebuilding
        nets_by_name = find_net_names(model)

        for i, cluster in enumerate(clusters):
            log.info(f"Processing cluster {i+1}/{len(clusters)}")
            cluster_vs = electrical_graph_within_main.vs[cluster]
            cluster_paths = cluster_vs["path"]

            # this works naturally to filter out signals, because only pins are present in the nodes dict
            nodes_in_cluster = [nodes[path] for path in cluster_paths if path in nodes]

            # find which net this cluster matches with
            rep_mvv = ModelVertexView.from_path(model, cluster_paths[0])
            for net_name, net_mvvs in nets_by_name.items():
                if rep_mvv in net_mvvs:
                    break
            else:
                net_name = generate_net_name([ModelVertexView.from_path(model, p) for p in cluster_paths])
                log.warning(f"Couldn't find net properly, but using name: {net_name}, which is hopefully good enough")

            # the cluster only represents a net if it contains eletrical pins
            if nodes_in_cluster:
                net = KicadNet(
                    code=str(len(nets) + 1), # code has to start at 1 and increment
                    name=net_name,
                    nodes=nodes_in_cluster,
                )

                nets.append(net)

        netlist = KicadNetlist(
            source=root_node,
            date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            components=list(components.values()),
            libparts=list(libparts.values()),
            nets=nets,
        )

        return netlist

class Kicad6NetlistTarget(Target):
    name = "netlist-kicad6"
    def __init__(self, muster: TargetMuster) -> None:
        self._netlist: Optional[KicadNetlist] = None
        self._designator_target = muster.ensure_target("designators")
        self._kicad_lib_paths_target = muster.ensure_target("kicad-lib-paths")
        super().__init__(muster)

    def generate(self) -> KicadNetlist:
        if self._netlist is None:
            self._kicad_lib_paths_target.generate()
            self._netlist = KicadNetlist.from_model(
                self.model,
                root_node=self.build_config.root_node,
                designators=self._designator_target.generate(),
                components_to_lib_map=self._kicad_lib_paths_target.component_path_to_lib_name,
                target=self,
            )
        return self._netlist

    def check(self) -> TargetCheckResult:
        return self._designator_target.check()

    @property
    def check_has_been_run(self) -> bool:
        return self._designator_target.check_has_been_run

    def build(self) -> None:
        netlist = self.generate()
        output_file = self.build_config.build_path / self.build_config.root_file.with_suffix(".net").name
        netlist.to_file(output_file)

    def resolve(self, *args, clean=None, **kwargs) -> None:
        log.info(f"No direct resolve action for {self.name}")

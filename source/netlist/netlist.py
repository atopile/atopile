import datetime
import time
import version
import pprint

from sexp import sexp

# Generators ------------------------------------------------------------------
def _gen_node(ref, pin):
    return {"node": {
        "ref": ref,
        "pin": pin,
    }}

def _gen_net(code, name, nodes):
    return {"net": {
        "code": code,
        "name": name,
        "nodes": sexp.multi_key_dict(*nodes),
    }}

def _gen_library(logical, uri):
    return {"library": {
        "logical": logical,
        "uri": uri,
    }}
    
def _gen_footprint(fp):
    return {"fp": fp}

def _gen_field(name, value):
    return ("field", {"name": name}, value)

def _gen_pin(num, name, type):
    return {"pin": {
        "num": num,
        "name": name,
        "type": type,
    }}

def _gen_libpart(lib, part, description, docs, footprints, fields, pins):
    return {"libpart": {
        "lib": lib,
        "part": part,
        "description": description,
        "docs": docs,
        "footprints": sexp.multi_key_dict(*footprints),
        "fields": sexp.multi_key_dict(*fields),
        "pins": sexp.multi_key_dict(*pins),
    }}

def _gen_comp(
        value, footprint, datasheet, fields, 
        libsource_lib, libsource_part, libsource_description,
        sheetpath_names, sheetpath_tstamps, 
        tstamp
    ):
    if fields is None:
        fields = []
    base = {"comp": {
        "value": value,
        "footprint": footprint,
        "datasheet": datasheet,
        "fields": sexp.multi_key_dict(*fields),
        "libsource": {
            "lib": libsource_lib,
            "part": libsource_part,
            "description": libsource_description,
        },
        "sheetpath": {
            "names": sheetpath_names,
            "tstamps": sheetpath_tstamps
        },
        "tstamp": tstamp
    }}

    if fields == []:
        del base["comp"]["fields"]
    
    if footprint is None:
        del base["comp"]["footprint"]

    return base

def _gen_comment(number, value):
    return {"comment": {
                "number": number,
                "value": value,
        }}

def _gen_netlist(version, source, date, tool, 
        sheet_number, sheet_name, sheet_tstamps,
        title_block_title, title_block_company, title_block_rev, title_block_date, title_block_source, title_block_comments,
        components, libparts, libraries, nets
    ):
    return {"export": {
                "version": version,
                "design": {
                    "source": source,
                    "date": date,
                    "tool": tool,
                    "sheet": {
                        "number": sheet_number,
                        "name" : sheet_name,
                        "tstamps": sheet_tstamps,
                        "title_block": sexp.multi_key_dict(
                            ("title",title_block_title),
                            ("company",title_block_company),
                            ("rev",title_block_rev),
                            ("date",title_block_date),
                            ("source", title_block_source),
                            _sublist(_gen_comment, 
                                [{"number": k+1, "value": v} for k,v in 
                                    enumerate(title_block_comments)
                                ]
                            )
                            
                        )
                    }
                },
                "components":   _list(_gen_comp,    components),
                "libparts":     _list(_gen_libpart, libparts),
                "libraries":    _list(_gen_library, libraries),
                "nets":         _list(_gen_net,     nets),
            }}


# Compositions ----------------------------------------------------------------
def _list(generator_function, obj_list):
    return sexp.multi_key_dict(
        *_sublist(generator_function, obj_list)
    )

def _sublist(generator_function, obj_list):
    #return tuple(map(lambda x: generator_function(**x), obj_list))
    return tuple(obj_list)
    
# Helper ----------------------------------------------------------------------
def _defaulted_netlist(source,
        components,libparts,libraries,nets):
    #date = datetime.datetime.now().strftime("%a %d %b %Y %H:%M:%S %Z")
    date = datetime.datetime.now().strftime("%c %z")

    return _gen_netlist(
        version="D",
        source=source,
        date=date,
        tool="faebryk {}".format(version.version()),
        sheet_number="1",
        sheet_name="/",
        sheet_tstamps=date,
        title_block_title="<Title>",
        title_block_company="<Company>",
        title_block_rev="<Rev>",
        title_block_date=date,
        title_block_source="<Source>",
        title_block_comments=[
            "<Comment 1>", 
            "<Comment 2>", 
            "<Comment 3>", 
            "<Comment 4>",
        ],
        components=components,
        libparts=libparts,
        libraries=libraries,
        nets=nets,
    )


# Test stuff ------------------------------------------------------------------


def make_test_netlist():
    timestamp = "{:X}".format(int(time.time()))

    resistor_comp = _gen_comp(
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        datasheet="~",
        fields=None,
        libsource_lib="Device",
        libsource_part="R",
        libsource_description="Resistor",
        sheetpath_names="/",
        sheetpath_tstamps="/",
        tstamp=timestamp,
    )

    resistor_part = _gen_libpart(
        lib="Device",
        part="R",
        description="Resistor",
        docs="~",
        footprints=[_gen_footprint("R_*")],
        fields=[
            _gen_field("Reference", "R"),
            _gen_field("Value", "R")
        ],
        pins=[
            _gen_pin(num=1, name="~", type="passive"),
            _gen_pin(num=2, name="~", type="passive")
        ],
    )

    device_library = _gen_library(
        logical="Device",
        uri='C:\\Program Files\\KiCad\\share\\kicad\\library/Device.lib'
    )
    
    device_nets = [
        _gen_net(
            code=1,
            name="+3V3",
            nodes=[
                _gen_node(
                    ref="R101",
                    pin="pin 1"
                )
            ],
        ),
        _gen_net(
            code=2,
            name="GND",
            nodes=[
                _gen_node(
                    ref="R101",
                    pin="pin 2"
                )
            ],
        ),
    ]
    
    netlist = _defaulted_netlist(
        source="N/A Source",
        components=[resistor_comp],
        libparts=[resistor_part],
        libraries=[device_library],
        nets=[*device_nets],
    )

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(netlist)

    sexpnet = sexp.gensexp(netlist)
    print(sexpnet)
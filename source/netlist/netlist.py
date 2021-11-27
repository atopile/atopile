import datetime
import time
import version
import pprint
import itertools

from sexp import sexp

# Generators ------------------------------------------------------------------
def _gen_node(ref, pin):
    return {"node": {
        "ref": ref,
        "pin": pin,
    }}

def _gen_net(code, name, nodes):
    return {"net": sexp.multi_key_dict(
        ("code", code),
        ("name", name),
        *nodes,
    )}

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
        ref, value, footprint, datasheet, fields,
        libsource_lib, libsource_part, libsource_description,
        sheetpath_names, sheetpath_tstamps,
        tstamp
    ):
    return {"comp": {
        "ref": ref,
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

    return _clean_none_and_empty({"export": {
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
            }})




# Compositions ----------------------------------------------------------------
def _list(generator_function, obj_list):
    return sexp.multi_key_dict(
        *_sublist(generator_function, obj_list)
    )

def _sublist(generator_function, obj_list):
    #return tuple(map(lambda x: generator_function(**x), obj_list))
    return [y for x in obj_list for y in x.items()]

def _clean_none_and_empty(obj,rd=0):
    #print("\t"*rd+"Clean:", type(obj), obj)
    new_obj = obj
    if obj is None:
        return None
    if type(obj) is dict:
        new_obj = obj.copy() #shallow
        for k,v in obj.items():
            v_ = _clean_none_and_empty(v,rd+1)
            if v_ is None:
                del new_obj[k]
                continue
            new_obj[k] = v_
    elif type(obj) is sexp.multi_key_dict:
        new_obj.update(
            tuple_list=_clean_none_and_empty(obj.tuple_list,rd+1),
            dict_ = _clean_none_and_empty(obj.dict_,rd+1)
        )
    elif type(obj) is list:
        new_obj = list(filter(lambda x: x is not None, map(_clean_none_and_empty, obj)))
    elif type(obj) is tuple:
        new_obj = tuple(filter(lambda x: x is not None, map(_clean_none_and_empty, obj)))
        if len(new_obj) == 1:
            new_obj = ()
    else:
        return new_obj
    if len(new_obj) == 0:
        new_obj = None

    #print("\t"*rd+"Cleaned:", new_obj)
    return new_obj


# Helper ----------------------------------------------------------------------
def _defaulted_netlist(components,nets):
    #date = datetime.datetime.now().strftime("%a %d %b %Y %H:%M:%S %Z")
    #date = datetime.datetime.now().strftime("%c %z")

    return _gen_netlist(
        version="D",
        source=None,
        date=None,
        tool=None,#"faebryk {}".format(version.version()),
        sheet_number=None,
        sheet_name=None,
        sheet_tstamps=None,
        title_block_title=None,
        title_block_company=None,
        title_block_rev=None,
        title_block_date=None,
        title_block_source=None,
        title_block_comments=[],
        components=components,
        libparts=[],
        libraries=[],
        nets=nets,
    )

def _defaulted_comp(ref, value, footprint, tstamp):
    return _gen_comp(
        ref=ref,
        value=value,
        footprint=footprint,
        datasheet=None,
        fields=[],
        libsource_lib=None,
        libsource_part=None,
        libsource_description=None,
        sheetpath_names=None,
        sheetpath_tstamps=None,
        tstamp=tstamp,
    )



# Test stuff ------------------------------------------------------------------


def make_test_netlist():

    # Footprint pins are just referenced by number through netlist of symbol

    # We only need
    #   - components
    #       - ref
    #       - value (for silk)
    #       - footprint
    #       - tstamp (uuid gen)
    #   - nets
    #       - code (uuid gen)
    #       - name
    #       - nodes
    #           - ref (comp)
    #           - pin (of footprint)

    # Careful comps need distinct timestamps
    tstamp = itertools.count(1)

    resistor_comp = _defaulted_comp(
        ref="R1",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
    )
    resistor_comp2 = _defaulted_comp(
        ref="R2",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
    )

    device_nets = [
        _gen_net(
            code=1,
            name="GND",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin=2,
                ),
                _gen_node(
                    ref="R2",
                    pin=2,
                ),
            ],
        ),
        _gen_net(
            code=2,
            name="+3V3",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin=1,
                ),
                _gen_node(
                    ref="R2",
                    pin=1,
                ),
            ],
        ),
    ]

    netlist = _defaulted_netlist(
        components=[resistor_comp, resistor_comp2],
        nets=[*device_nets],
    )

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(netlist)

    sexpnet = sexp.gensexp(netlist)
    print(sexpnet)
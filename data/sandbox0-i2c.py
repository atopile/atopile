from atopile.model import Component, Net, Feature, Connection
from copy import deepcopy

def get_by_name(list, name):
    for item in list:
        if item.name == name:
            return item
    return None

ESP32 = Component(
    source="sandbox0-i2c.py",
    locn_start=0,
    locn_end=1,
    name="ESP32",
    features=[
        Feature(
            name="i2c",
            nets=[
                Net(
                    name="sda",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                ),
                Net(
                    name="scl",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                ),
                Net(
                    name="gnd",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                )
            ]
        )
    ],
    nets=[
        Net(
            name="vcc",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
        Net(
            name="gnd",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
    ]
)

BME280 = Component(
    source="sandbox0-i2c.py",
    locn_start=0,
    locn_end=1,
    name="BME280",
    features=[
        Feature(
            name="i2c",
            nets=[
                Net(
                    name="sda",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                ),
                Net(
                    name="scl",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                ),
                Net(
                    name="gnd",
                    locn_start=0,
                    locn_end=1,
                    source="sandbox0-i2c.py",
                )
            ]
        )
    ],
    nets=[
        Net(
            name="vcc",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
        Net(
            name="gnd",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
    ]
)

PSU = Component(
    source="sandbox0-i2c.py",
    locn_start=0,
    locn_end=1,
    name="BME280",
    nets=[
        Net(
            name="vcc",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
        Net(
            name="gnd",
            locn_start=0,
            locn_end=1,
            source="sandbox0-i2c.py",
        ),
    ]
)

circuit_components=[
    Component(
        source="sandbox0-i2c.py",
        locn_start=0,
        locn_end=1,
        name="U1",
        inherits_from=[ESP32],
        nets=deepcopy(ESP32.nets),
        features=deepcopy(ESP32.features),
    ),
    Component(
        source="sandbox0-i2c.py",
        locn_start=0,
        locn_end=1,
        name="U2",
        inherits_from=[BME280],
        nets=deepcopy(BME280.nets),
        features=deepcopy(BME280.features),
    ),
    Component(
        source="sandbox0-i2c.py",
        locn_start=0,
        locn_end=1,
        name="U3",
        inherits_from=[PSU],
        nets=deepcopy(PSU.nets),
        features=deepcopy(PSU.features),
    ),
]

Component(
    source="sandbox0-i2c.py",
    locn_start=0,
    locn_end=1,
    name="sandbox0-i2c",
    components=circuit_components,
    connections=[
        # power connections
        Connection([
            get_by_name(get_by_name(circuit_components, "U1").nets, "vcc"),
            get_by_name(get_by_name(circuit_components, "U3").nets, "vcc"),
        ]),
        Connection([
            get_by_name(get_by_name(circuit_components, "U1").nets, "gnd"),
            get_by_name(get_by_name(circuit_components, "U3").nets, "gnd"),
        ]),
        Connection([
            get_by_name(get_by_name(circuit_components, "U2").nets, "vcc"),
            get_by_name(get_by_name(circuit_components, "U3").nets, "vcc"),
        ]),
        Connection([
            get_by_name(get_by_name(circuit_components, "U2").nets, "gnd"),
            get_by_name(get_by_name(circuit_components, "U3").nets, "gnd"),
        ]),

        # i2c connections
        Connection([
            get_by_name(get_by_name(circuit_components, "U1").features, "i2c"),
            get_by_name(get_by_name(circuit_components, "U2").features, "i2c"),
        ]),
    ]
)

# notes:
# - we should come up with a better name for "nets" in this context, because they are really referring to something more like a "virtual pin"
# - we haven't included a package in this example, which means we don't have all the information needed to generate a netlist

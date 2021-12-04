from netlist.kicad_netlist import from_faebryk_t2_netlist, make_test_netlist_manu

# 0. netlist = graph

# t1 is basically a reduced version of the grap
# t1_netlist = [ 
#     (name, value, properties, 
#       neighbors=[(&vertex, spin, dpin)])],
# ]

# t2 is transposed to list nets instead of vertices
# t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]


#def make_t2_netlist_from_t1():



# Test stuff ------------------------------------------------------------------

def make_test_netlist_t2():
    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = {
        "name": "R1",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    }

    resistor2 = {
        "name": "R2",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    }

    netlist = [
        {
            "properties": {
                "name": "GND",
            },
            "vertices": [
                {
                    "comp": resistor1,
                    "pin": 2
                },
                {
                    "comp": resistor2,
                    "pin": 2
                },
            ],
        },
        {
            "properties": {
                "name": "+3V3",
            },
            "vertices": [
                {
                    "comp": resistor1,
                    "pin": 1
                },
                {
                    "comp": resistor2,
                    "pin": 1
                },
            ],
        },
    ]
    print("T2 netlist:", netlist)

    kicad_net = from_faebryk_t2_netlist(netlist)
    kicad_net_manu = make_test_netlist_manu()

    if kicad_net != kicad_net_manu:
        print("T2 != Manu")
        print(kicad_net_manu)
    print(kicad_net)

def make_test_netlist():
    return make_test_netlist_t2()
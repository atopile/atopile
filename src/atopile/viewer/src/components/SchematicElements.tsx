//@ts-nocheck
import React, { useState, useEffect} from 'react';
import {Handle, useUpdateNodeInternals, Position} from 'reactflow';


// Utility to determine new position after rotation
function rotatePosition(initialPosition, degrees) {
    const rotations = {
        [Position.Top]: Position.Right,
        [Position.Right]: Position.Bottom,
        [Position.Bottom]: Position.Left,
        [Position.Left]: Position.Top
    };

    const steps = (degrees / 90) % 4;
    let newPosition = initialPosition;
    for (let i = 0; i < steps; i++) {
        newPosition = rotations[newPosition];
    }
    return newPosition;
  }

// Utility to apply mirror transformation along the X-axis
function mirrorPosition(position, mirror) {
    if (!mirror) return position;
    const mirrors = {
        [Position.Left]: Position.Right,
        [Position.Right]: Position.Left,
        [Position.Top]: Position.Top,
        [Position.Bottom]: Position.Bottom
    };

    return mirrors[position] || position;
  }

const MultiPinHandle = ({ ports, rotationDegrees = 0, mirrorX = false}) => {
    //TODO: remove this
    const portsArray = Array.isArray(ports) ? ports : Object.values(ports);

    if (!portsArray.length) {
        console.error('Ports data is invalid or empty:', portsArray);
        return null;
    }

    // Function to calculate the final position for each port
    const calculateRotation = (initialPosition) => {
        let position = mirrorPosition(initialPosition, mirrorX);
        position = rotatePosition(position, rotationDegrees); // Default to 'left' if initialPosition is undefined
        return position;
    };

    const calculateOffset = (port, mirrorX, rotationDegrees) => {
        // Adjust rotation based on mirrorX condition
        const effectiveRotation = mirrorX ? rotationDegrees + 180 : rotationDegrees;

        // Calculate the effective offset direction and value
        const direction = port.offset_dir[effectiveRotation % 360];
        const offsetValue = port.offset[effectiveRotation % 360];

        // Create the style object dynamically
        const style = { [direction]: `${offsetValue}px` };

        return style;
    };
    return (
        <>
            {portsArray.map((port) => (
                <React.Fragment key={port.net_id}>
                    <Handle
                        type="source"
                        id={port.id}
                        position={(calculateRotation(port.initialPosition))}
                        style={calculateOffset(port, mirrorX, rotationDegrees) }
                    />
                    <Handle
                        type="target"
                        id={port.id}
                        position={(calculateRotation(port.initialPosition))}
                        style={calculateOffset(port, mirrorX, rotationDegrees)}
                    />
                </React.Fragment>
            ))}
        </>
    );
};


// Common function to handle and render electronic components
export const SchematicComponent = ({ id, data }) => {
    const [rotation, setRotation] = useState(0);
    const [mirror_x, setMirror] = useState(false);
    const updateNodeInternals = useUpdateNodeInternals();

    useEffect(() => {
        setRotation(data.rotation);
        //TODO: add mirroring for more complex components
        //setMirror(data.mirror);
        updateNodeInternals(id);
    }, [data]);

    const transform = `rotate(${data.rotation}deg) ${data.mirror_x ? 'scaleX(-1)' : ''}`;

    // Get the data for each component type
    const component_metadata = getComponentMetaData(data.std_lib_id);
    let populated_ports = component_metadata.ports;

    let index = 0;
    for (const [key, value] of Object.entries(populated_ports)) {
        if (populated_ports[key] === undefined || data.ports[index] === undefined) {
            throw new Error(`Port ${key} not found in component metadata. Did you update your generics library?`);
        }
        populated_ports[key].id = data.ports[index].net_id;
        populated_ports[key].name = data.ports[index].name;
        index++;
    }

    return (
        <>
            <MultiPinHandle ports={populated_ports} rotationDegrees={data.rotation} mirrorX={data.mirror_x} />
            <div style={{ transform, width: '50px', height: '50px' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150" strokeWidth="5" dangerouslySetInnerHTML={{ __html: component_metadata.svg }} >
                </svg>
                <div style={{position: "absolute", top: "0", left: "0", fontSize: "7px"}}>{data.name}</div>
            </div>
        </>
    );
};

// Common function to handle and render electronic signal
export const SchematicSignal = ({ id, data }) => {
    const [rotation, setRotation] = useState(0);
    const [mirror, setMirror] = useState(false);
    const updateNodeInternals = useUpdateNodeInternals();

    useEffect(() => {
        updateNodeInternals(id);
    }, [data]);

    // Get the data for each component type
    const component_metadata = getComponentMetaData(data.std_lib_id);
    let populated_ports = component_metadata.ports;

    let index = 0;
    for (const [key, value] of Object.entries(populated_ports)) {
        populated_ports[key].id = data.address;
        populated_ports[key].name = data.name;
        index++;
    }

    return (
        <>
            <MultiPinHandle ports={populated_ports} rotationDegrees={0} mirrorX={false} position={position}/>
            <div style={{ width: '50px', height: '50px' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150" strokeWidth="5" dangerouslySetInnerHTML={{ __html: component_metadata.svg }} >
                </svg>
                <div style={{fontSize: "7px"}}>{data.name}</div>
            </div>
        </>
    );
};

// Common function to handle and render electronic pins scattered around the place
export const SchematicScatter = ({ id, data }) => {
    const [mirror, setMirror] = useState(false);
    const updateNodeInternals = useUpdateNodeInternals();

    useEffect(() => {
        setMirror(data.mirror);
        updateNodeInternals(id);
    }, [data]);

    return (
        <>
            <Handle
                type="source"
                id={id}
                position={mirror?Position.Right:Position.Left}
            />
            <div style={{border: "2px solid black", padding: "2px", borderRadius: "5px"}}>
                {data.name}
            </div>
            <Handle
                type="target"
                id={id}
                position={mirror?Position.Right:Position.Left}
            />
        </>
    );
};

function getComponentMetaData(component) {
    //TODO: move the std lib back into the compiler?
    // components courtesy of: https://github.com/chris-pikul/electronic-symbols

    //TODO: we will have to break this up into multiple different files. Keeping this here for the second.
    const component_metadata = {
        "Resistor": {
            "ports": {
                "p1": {
                    initialPosition: Position.Left,
                    offset: 35,
                    offset_dir: Position.Top
                },
                "p2": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg": `<path fill="none" stroke="#000" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>`
        },
        "Inductor": {
            "ports": {
                "p1": {
                    initialPosition: Position.Left,
                    offset: 35,
                    offset_dir: Position.Top
                },
                "p2": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg": `<path fill="none" stroke="#000" stroke-linejoin="round" stroke-width="5" d="M0 75.13h12.5s0-18.82 15.63-18.82S43.75 75 43.75 75s0-18.75 15.63-18.75S75 75 75 75s0-18.75 15.63-18.75S106.25 75 106.25 75s0-18.75 15.63-18.75S137.5 75 137.5 75H150"/>`
        },
        "ZenerDiode": {
            "ports": {
                "anode": {
                    initialPosition: Position.Left,
                    offset: 35,
                    offset_dir: Position.Top
                },
                "cathode": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg":  `<g fill="none" stroke="#000" strokeMiterlimit="10">
                        <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
                        <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
                    </g>`
        },
        "SchottkyDiode": {
            "ports": {
                "anode": {
                    initialPosition: Position.Left,
                    offset: 35,
                    offset_dir: Position.Top
                },
                "cathode": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg":  `<g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
                        <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
                        <path d="M87.5 97v12.5H100v-69h12.5V53"/>
                    </g>`
        },
        "Diode": {
            "ports": {
                "anode": {
                    initialPosition: Position.Left,
                    offset: 25,
                    offset_dir: Position.Top
                },
                "cathode": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg": `<path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50"/>`
        },
        "LED": {
            "ports": {
                "anode": {
                    initialPosition: Position.Left,
                    offset: 25,
                    offset_dir: Position.Top
                },
                "cathode": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg": `<path fill="red" stroke="#000" strokeMiterlimit="10" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
                    <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
                    <path fill="none" stroke="#000" strokeMiterlimit="10" d="m118.75 50 18.75-18.75"/>
                    <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>`
        },
        "Capacitor": {
            "ports": {
                "p1": {
                    initialPosition: Position.Left,
                    offset: 35,
                    offset_dir: Position.Top
                },
                "p2": {
                    initialPosition: Position.Right,
                    offset: 25,
                    offset_dir: Position.Top
                }
            },
            "svg": `<path fill="none" stroke="#000" strokeMiterlimit="10" d="M0 74.97h65.5m84.5.28H84.5m0-31.25v62m-19-62v62"/>`

        },
        "NFET": {
            "ports": {
                "gate": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "drain": {
                    initialPosition: Position.Bottom,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "source": {
                    initialPosition: Position.Top,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                }
            },
            "svg": `<g fill="none" stroke="#000" strokeMiterlimit="10">
                        <circle cx="75" cy="75" r="50"/>
                        <path d="M0 75h50m12.5-31.25v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
                    </g>`
        },
        "PFET": {
            "ports": {
                "gate": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "source": {
                    initialPosition: Position.Top,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "drain": {
                    initialPosition: Position.Bottom,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
            },
            "svg": `<g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
                        <circle cx="75" cy="75" r="50"/>
                        <path d="M0 75h31.25M62.5 43.75v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
                        <circle cx="37.5" cy="75" r="6.25"/>
                    </g>`
        },
        "PNP": {
            "ports": {
                "gate": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "drain": {
                    initialPosition: Position.Bottom,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "source": {
                    initialPosition: Position.Top,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                }
            },
            "svg": `<circle cx="75" cy="75" r="50" fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5"/>
                    <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="M0 75h50m0 31.25v-62.5M100 150v-40.5l-50-22M99.84 0v31.25L62.22 53.94"/>
                    <path d="M60.23 46.41 53 59.5l14.95-.28-7.72-12.81z"/>`
        },
        "NPN": {
            "ports": {
                "gate": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "drain": {
                    initialPosition: Position.Bottom,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "source": {
                    initialPosition: Position.Top,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                }
            },
            "svg": `<circle cx="75" cy="75" r="50" fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5"/>
                    <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="M100 150v-31.25M0 75h50m0-31.25v62.5M100 0v40.5l-50 22m0 25 37.52 22.47"/>
                    <path d="m81.8 115.26 14.95.24-7.27-13.07-7.68 12.83z"/>`
        },
        "Opamp": {
            "ports": {
                "power.vcc": {
                    initialPosition: Position.Top,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "power.gnd": {
                    initialPosition: Position.Bottom,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Left,
                        90: Position.Top,
                        180: Position.Left,
                        270: Position.Top
                    }
                },
                "inverting": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 33,
                        90: 17,
                        180: 17,
                        270: 33
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "non_inverting": {
                    initialPosition: Position.Left,
                    offset: {
                        0: 17,
                        90: 33,
                        180: 33,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                },
                "output": {
                    initialPosition: Position.Right,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.Top,
                        90: Position.Left,
                        180: Position.Top,
                        270: Position.Left
                    }
                }
            },
            "svg": `<path fill="none" stroke="#000" strokeMiterlimit="10" d="M25 25v100l100-50L25 25zm0 25H0m125 25h25M0 100h25m9.5-47H53m-9.25-9.25v18.5M34.5 97H53M74.69 0v50m.37 100v-50"/>`
        },
        "Power.vcc": {
            "ports": {
                "Power.vcc": {
                    initialPosition: Position.Bottom,
                    offset: 35,
                    offset_dir: Position.Left
                }
            },
            "svg": `<g transform="rotate(180 75 75)">
                    <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="M75 0v62.5m-50 0h100L75 125 25 62.5z"/>
                    </g>`
        },
        "Power.gnd": {
            "ports": {
                "Power.gnd": {
                    initialPosition: Position.Top,
                    offset: 35,
                    offset_dir: Position.Left
                }
            },
            "svg": `<path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="M75 0v75m-50 0h100m-56.25 50h12.5M50 100h50"/>`
        }
    };

    return component_metadata[component];
}
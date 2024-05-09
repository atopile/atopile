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
export const SchematicElectronicComponent = ({ id, data }) => {
    const [rotation, setRotation] = useState(0);
    const [mirror, setMirror] = useState(false);
    const [position, setCompPosition] = useState({ x: 0, y: 0 });
    const updateNodeInternals = useUpdateNodeInternals();

    useEffect(() => {
        setRotation(data.rotation);
        setMirror(data.mirror);
        setCompPosition(data.position);
        updateNodeInternals(id);
    }, [data]);

    const transform = `rotate(${rotation}deg) ${mirror ? 'scaleX(-1)' : ''}`;

    // Get the data for each component type
    const component_metadata = getComponentMetaData(data.std_lib_id);
    let populated_ports = component_metadata.ports;

    let index = 0;
    for (const [key, value] of Object.entries(populated_ports)) {
        populated_ports[key].id = data.ports[index].net_id;
        populated_ports[key].name = data.ports[index].name;
        index++;
    }

    return (
        <>
            <MultiPinHandle ports={populated_ports} rotationDegrees={rotation} mirrorX={mirror} position={position}/>
            <div style={{ transform, width: '50px', height: '50px' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150" strokeWidth="5" dangerouslySetInnerHTML={{ __html: component_metadata.svg }} >
                </svg>
            </div>
        </>
    );
};


function getComponentMetaData(component) {
    //TODO: move the std lib back into the compiler????
    // components courtesy of: https://github.com/chris-pikul/electronic-symbols
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
        }
    };

    return component_metadata[component];
}
// @ts-nocheck
import React, { useState, useEffect, useCallback } from 'react';
import {Handle, useUpdateNodeInternals} from 'reactflow';



export async function loadSchematicJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/schematic-data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

// Enums for positions to maintain clarity
const Position = {
    TOP: 'top',
    BOTTOM: 'bottom',
    LEFT: 'left',
    RIGHT: 'right'
  };

// Utility to determine new position after rotation
function rotatePosition(initialPosition, degrees) {
    const rotations = {
      [Position.TOP]: Position.RIGHT,
      [Position.RIGHT]: Position.BOTTOM,
      [Position.BOTTOM]: Position.LEFT,
      [Position.LEFT]: Position.TOP
    };

    const steps = (degrees / 90) % 4;
    let newPosition = initialPosition;
    for (let i = 0; i < steps; i++) {
      newPosition = rotations[newPosition];
    }
    return newPosition;
  }

  // Utility to apply mirror transformation along the X-axis
  function mirrorPositionX(position, mirror) {
    if (!mirror) return position;
    const mirrors = {
      [Position.LEFT]: Position.RIGHT,
      [Position.RIGHT]: Position.LEFT,
      [Position.TOP]: Position.TOP,
      [Position.BOTTOM]: Position.BOTTOM
    };

    return mirrors[position] || position;
  }

  const MultiPinHandle = ({ ports, rotationDegrees = 0, mirrorX = false}) => {
    // Convert ports object to an array if it's not already an array
    const portsArray = Array.isArray(ports) ? ports : Object.values(ports);

    if (!portsArray.length) {
        console.error('Ports data is invalid or empty:', portsArray);
        return null; // Return null if ports data is not valid
    }

    // Function to calculate the final position for each port
    const calculateRotation = (initialPosition) => {
        let position = mirrorPositionX(initialPosition, mirrorX);
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
const RenderElectronicComponent = (data, svgContent) => {
    const [rotation, setRotation] = useState(0);
    const [mirror, setMirror] = useState(false);
    const [position, setCompPosition] = useState({ x: 0, y: 0 });


    useEffect(() => {
        setRotation(data.rotation);
        setMirror(data.mirror);
        setCompPosition(data.position);
    }, [data]); // Only re-run if `data` changes


    if (!data || !data.ports) {
        console.error('Invalid data or ports are undefined');
        return null;  // Early return if data or ports are not available
    }

    const transform = `rotate(${rotation}deg) ${mirror ? 'scaleX(-1)' : ''}`;

    // Convert ports object to an array if it's not already an array
    const portsArray = Array.isArray(data.ports) ? data.ports : Object.values(data.ports);

    // Check if ports array is valid and has entries
    if (!portsArray.length) {
        console.error('Ports data is invalid or empty:', portsArray);
        return null; // Return null if ports data is not valid
    }

    return (
      <>
        <MultiPinHandle ports={portsArray} rotationDegrees={rotation} mirrorX={mirror} position={position}/>
        <div style={{ transform, width: '50px', height: '50px' }}>
          {svgContent}
        </div>
      </>
    );
  };


  export const Resistor = ({ data }) => {
    // Adjust the ports data to include static mapping of anode and cathode
    const adjustedPorts = [
        {
            id: data.ports[0].net_id,
            initialPosition: Position.LEFT,
            name: data.ports[0].name,
            offset: 35,
            offset_dir: Position.TOP
        },
        {
            id: data.ports[1].net_id,
            initialPosition: Position.RIGHT,
            name: data.ports[1].name,
            offset: 25,
            offset_dir: Position.TOP
        }
        ];

    const svgContent = (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150" strokeWidth="5">
            <path fill="none" stroke="#000" strokeWidth="5" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>
        </svg>
    );

    return RenderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
  };


  export const LED = ({ data }) => {
    // Adjust the ports data to include static mapping of anode and cathode
    const adjustedPorts = [
      {
        id: data.ports[0].net_id,
        initialPosition: Position.LEFT,
        offset_dir: Position.TOP,
        offset: 25,
        name: data.ports[0].name
      },
      {
        id: data.ports[1].net_id,
        initialPosition: Position.RIGHT,
        offset_dir: Position.TOP,
        offset: 25,
        name: data.ports[1].name
      }
    ];

    const svgContent = (
      <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
        <path fill="red" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
        <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
        <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
        <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
      </svg>
    );

    return RenderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
  };


  export const NFET = ({ data }) => {
    // Ensure ports is an array
    const portsArray = Array.isArray(data.ports) ? data.ports : Object.values(data.ports);

    // Map ports to their new properties based on name
    const adjustedPorts = portsArray.map(port => {
        switch (port.name) {
            case 'gate':
                return {
                    ...port,
                    id: data.ports[1].net_id,
                    initialPosition: Position.LEFT,
                    offset: {
                        0: 25,
                        90: 25,
                        180: 25,
                        270: 25
                    },
                    offset_dir: {
                        0: Position.TOP,
                        90: Position.LEFT,
                        180: Position.TOP,
                        270: Position.LEFT
                    }
                };
            case 'drain':
                return {
                    ...port,
                    id: data.ports[2].net_id,
                    initialPosition: Position.BOTTOM,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.LEFT,
                        90: Position.TOP,
                        180: Position.LEFT,
                        270: Position.TOP
                    }
                };
            case 'source':
                return {
                    ...port,
                    id: data.ports[0].net_id,
                    initialPosition: Position.TOP,
                    offset: {
                        0: 33,
                        90: 33,
                        180: 17,
                        270: 17
                    },
                    offset_dir: {
                        0: Position.LEFT,
                        90: Position.TOP,
                        180: Position.LEFT,
                        270: Position.TOP
                    }
                };
            default:
                throw new Error("Unsupported port configuration");
        }
    });

    const svgContent = (
        <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
            <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                <circle cx="75" cy="75" r="50"/>
                <path d="M0 75h50m12.5-31.25v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
            </g>
        </svg>
    );

    return RenderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
};

// @ts-nocheck
import React from 'react';
import {Handle} from 'reactflow';

// import 
import './edge_style.css';


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

    console.log('Converted ports array:', portsArray);

    if (!portsArray.length) {
        console.error('Ports data is invalid or empty:', portsArray);
        return null; // Return null if ports data is not valid
    }

    // Function to calculate the final position for each port
    const calculateFinalPosition = (initialPosition) => {
        let position = mirrorPositionX(initialPosition, mirrorX);
        position = rotatePosition(position, rotationDegrees); // Default to 'left' if initialPosition is undefined
        return position;
    };

    return (
        <>
            {portsArray.map((port) => (
                <React.Fragment key={port.net_id}>
                    <Handle
                        type="source"
                        id={port.id}
                        position={calculateFinalPosition(port.initialPosition)}
                        style={{ [calculateFinalPosition(port.offset_dir)]: `${port.offset}px` }}
                    />
                    <Handle
                        type="target"
                        id={port.id}
                        position={calculateFinalPosition(port.initialPosition)}
                        style={{ [calculateFinalPosition(port.offset_dir)]: `${port.offset}px` }}
                    />
                </React.Fragment>
            ))}
        </>
    );
};


// Common function to handle and render electronic components
const renderElectronicComponent = (data, svgContent) => {
    if (!data || !data.ports) {
      console.error('Invalid data or ports are undefined');
      return null;  // Early return if data or ports are not available
    }

    const { rotation, mirror, ports } = data;
    const transform = `rotate(${rotation}deg) ${mirror ? 'scaleX(-1)' : ''}`;

    console.log(transform)
    // Convert ports object to an array if it's not already an array
    const portsArray = Array.isArray(ports) ? ports : Object.values(ports);

    // Check if ports array is valid and has entries
    if (!portsArray.length) {
        console.error('Ports data is invalid or empty:', portsArray);
        return null; // Return null if ports data is not valid
    }

    return (
      <>
        <MultiPinHandle ports={portsArray} rotationDegrees={rotation} mirrorX={mirror}/>
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
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 140">
        <path fill="none" stroke="#000" strokeWidth="5" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>
      </svg>
    );

    return renderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
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

    return renderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
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
                    initialPosition: Position.TOP,
                    offset_dir: Position.LEFT,
                    offset: 33
                };
            case 'drain':
                return {
                    ...port,
                    id: data.ports[2].net_id,
                    initialPosition: Position.BOTTOM,
                    offset_dir: Position.LEFT,
                    offset: 33
                };
            case 'source':
                return {
                    ...port,
                    id: data.ports[0].net_id,
                    initialPosition: Position.LEFT,
                    offset_dir: Position.TOP,
                    offset: 26
                };
            default:
                throw new Error("Unsupported port configuration");
        }
    });

    const svgContent = (
        <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
            <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                <circle cx="75" cy="75" r="50"/>
                <path d="M0 75h50m12.5-31.25v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
            </g>
        </svg>
    );

    return renderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
};


// const NameAndValue = ({name, value}) => {
//     return (
//         <div>
//             <div>{name}</div>
//             <div>{value}</div>
//         </div>
//     )
// }


// export const Resistor = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>;
//                 </svg>
//             </div>
//         </>
//     )
// };

// export const Capacitor = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M0 74.97h65.5m84.5.28H84.5m0-31.25v62m-19-62v62"/>
//                 </svg>
//             </div>
//         </>
//     )
// };

// export const LED = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <path fill="red" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
//                     <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
//                     <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
//                 </svg>
//             </div>
//         </>
//     )
// };
// export const NFET = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <ThreePinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} port_3={data.component_data.ports[2].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
//                         <circle cx="75" cy="75" r="50"/>
//                         <path d="M0 75h50m12.5-31.25v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
//                     </g>
//                 </svg>
//             </div>
//         </>
//     )
// };
// export const PFET = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <div>
//             <ThreePinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} port_3={data.component_data.ports[2].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
//                         <circle cx="75" cy="75" r="50"/>
//                         <path d="M0 75h31.25M62.5 43.75v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
//                         <circle cx="37.5" cy="75" r="6.25"/>
//                     </g>
//                 </svg>
//             </div>
//         </div>
//     )
// };
// export const Diode = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <div>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50"/>
//                 </svg>
//             </div>
//         </div>
//     )
// };
// export const ZenerDiode = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <div>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
//                         <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
//                         <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
//                     </g>
//                 </svg>
//             </div>
//         </div>
//     )
// };
// export const SchottkyDiode = ( { data }: {data: NodeProps} ) => {
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <div>
//             <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
//             <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 140">
//                     <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
//                         <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
//                         <path d="M87.5 97v12.5H100v-69h12.5V53"/>
//                     </g>
//                 </svg>
//             </div>
//         </div>
//     )
// };

// export const Ground = ( { data }: {data: NodeProps} ) => {
//     const port_ids = Object.keys(data.ports);
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <Handle
//                 type="source"
//                 position={RotationEnum.Top}
//             />
//             <Handle
//                 type="target"
//                 position={RotationEnum.Top}
//             />
//             <div>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M75 0v75m-50 0h100m-56.25 50h12.5M50 100h50"/>
//                 </svg>
//             </div>
//         </>
//     )
// };

// export const Vcc = ( { data }: {data: NodeProps} ) => {
//     const port_ids = Object.keys(data.ports);
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <Handle
//                 type="source"
//                 position={RotationEnum.Bottom}
//             />
//             <Handle
//                 type="target"
//                 position={RotationEnum.Bottom}
//             />
//             <div>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" transform="rotate(180,75,75)" d="M75 0v62.5m-50 0h100L75 125 25 62.5z"/>
//                 </svg>
//             </div>
//         </>
//     )
// };

// export const OpAmp = ( { data }: {data: NodeProps} ) => {
//     const port_ids = Object.keys(data.ports);
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <>
//             <Handle
//                 type="source"
//                 id={data.ports[1]['net_id']}
//                 position={RotationEnum.Left}
//                 style={{ top: `35px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[1]['net_id']}
//                 position={RotationEnum.Left}
//                 style={{ top: `35px`}}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[0]['net_id']}
//                 position={RotationEnum.Left}
//                 style={{ top: `65px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[0]['net_id']}
//                 position={RotationEnum.Left}
//                 style={{ top: `65px`}}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[2]['net_id']}
//                 position={RotationEnum.Right}
//                 style={{ top: `50px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[2]['net_id']}
//                 position={RotationEnum.Right}
//                 style={{ top: `50px`}}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[3]['net_id']}
//                 position={RotationEnum.Top}
//                 style={{ left: `50px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[3]['net_id']}
//                 position={RotationEnum.Top}
//                 style={{ left: `50px`}}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[4]['net_id']}
//                 position={RotationEnum.Bottom}
//                 style={{ left: `50px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[4]['net_id']}
//                 position={RotationEnum.Bottom}
//                 style={{ left: `50px`}}
//             />
//             <div>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 150 150" transform="scale(1,-1)">
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5" d="M25 25v100l100-50L25 25zm0 25H0m125 25h25M0 100h25m9.5-47H53m-9.25-9.25v18.5M34.5 97H53M74.69 0v50m.37 100v-50"/>
//                 </svg>
//             </div>
//         </>
//     )
// };


// export const NPN = ( { data }: {data: NodeProps} ) => {
//     const port_ids = Object.keys(data.ports);
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     return (
//         <div style={{transform: 'rotate(90deg)'}}>
//             <Handle
//                 type="source"
//                 id={data.ports[0]['net_id']}
//                 position={RotationEnum.Top}
//                 style={{ left: `33px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[0]['net_id']}
//                 position={RotationEnum.Top}
//                 style={{ left: `33px`}}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[1]['net_id']}
//                 position={RotationEnum.Right}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[1]['net_id']}
//                 position={RotationEnum.Right}
//             />
//             <Handle
//                 type="source"
//                 id={data.ports[2]['net_id']}
//                 position={RotationEnum.Bottom}
//                 style={{ left: `33px`}}
//             />
//             <Handle
//                 type="target"
//                 id={data.ports[2]['net_id']}
//                 position={RotationEnum.Bottom}
//                 style={{ left: `33px`}}
//             />
//             <div>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 150 150" transform="scale(-1,1)">
//                     <circle cx="75" cy="75" r="50" fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5"/>
//                     <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5" d="M100 150v-31.25M0 75h50m0-31.25v62.5M100 0v40.5l-50 22m0 25 37.52 22.47"/>
//                     <path d="m81.8 115.26 14.95.24-7.27-13.07-7.68 12.83z"/>
//                 </svg>
//             </div>
//         </div>
//     )
// };

// export const Bug = ({ data }: {data: NodeProps}) => {

//     const LeftPins = Object.entries(data.ports).map(([key, value], index) => {
//         console.log("key")
//         console.log(key)
//         return (<React.Fragment key={key}>
//                 <Handle
//                     type="source"
//                     id={key}
//                     position={RotationEnum.Left}
//                     style={{ top: `${10 + index * 15}px`}}
//                 />
//                 <Handle
//                     type="target"
//                     id={key}
//                     position={RotationEnum.Left}
//                     style={{ top: `${10 + index * 15}px`}}
//                 />
//                 <div style={{height: '15px', top: `${10 + index * 15}px`, fontSize: '8px'}}>
//                     {value}
//                 </div>
//             </React.Fragment>)
//     });

//     return (
//         <>
//             <div style={{display: 'flex', alignItems: 'center', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: '#FFF' }}>
//                 <div style={{display: 'flex', flexDirection: 'column', paddingRight: '10px'}}>
//                     {LeftPins}
//                 </div>
//                 <div style={{display: 'flex', flexDirection: 'column'}}>
//                     <div style={{textAlign: 'center'}}>
//                         <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
//                         <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.name}</div>
//                     </div>
//                 </div>
//             </div>
//         </>
//     )
// };
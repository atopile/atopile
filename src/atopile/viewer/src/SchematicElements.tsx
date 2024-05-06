// @ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { Handle, Position, NodeProps, NodeToolbar } from 'reactflow';

export async function loadSchematicJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/schematic-data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

const TwoPinHandle = ({port_1, port_2, orientation}) => {
    // Determine the orientation based on the provided prop or a default value
    const currentOrientation = orientation || "horizontal";

    return (
        <>
            {/* Handles for port_1 */}
            <Handle
                type="source"
                id={port_1}
                position={currentOrientation === "horizontal" ? Position.Left : Position.Top}
            />
            <Handle
                type="target"
                id={port_1}
                position={currentOrientation === "horizontal" ? Position.Left : Position.Top}
            />

            {/* Handles for port_2 */}
            <Handle
                type="source"
                id={port_2}
                position={currentOrientation === "horizontal" ? Position.Right : Position.Bottom}
            />
            <Handle
                type="target"
                id={port_2}
                position={currentOrientation === "horizontal" ? Position.Right : Position.Bottom}
            />
        </>
    )
};

const NameAndValue = ({name, value}) => {
    return (
        <div>
            <div>{name}</div>
            <div>{value}</div>
        </div>
    )
}

export const Resistor = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>;
                </svg>
            </div>
        </>
    )
};

export const Capacitor = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M0 74.97h65.5m84.5.28H84.5m0-31.25v62m-19-62v62"/>
                </svg>
            </div>
        </>
    )
};

export const LED = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
                    <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
                    <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
                </svg>
            </div>
        </>
    )
};
export const NFET = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                        <circle cx="75" cy="75" r="50"/>
                        <path d="M0 75h50m12.5-31.25v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
                    </g>
                </svg>
            </div>
        </>
    )
};
export const PFET = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                        <circle cx="75" cy="75" r="50"/>
                        <path d="M0 75h31.25M62.5 43.75v62.5M99.66 0v56.25H62.5M99.66 150V93.75H62.5M50 50v50"/>
                        <circle cx="37.5" cy="75" r="6.25"/>
                    </g>
                </svg>
            </div>
        </div>
    )
};
export const Diode = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50"/>
                </svg>
            </div>
        </div>
    )
};
export const ZenerDiode = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                        <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
                        <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
                    </g>
                </svg>
            </div>
        </div>
    )
};
export const SchottkyDiode = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div>
            <TwoPinHandle port_1={data.component_data.ports[0].net_id} port_2={data.component_data.ports[1].net_id} orientation={data.orientation}/>
            <div style={{ transform: data.orientation === "horizontal" ? "none" : `rotate(90deg)`, }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <g fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5">
                        <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
                        <path d="M87.5 97v12.5H100v-69h12.5V53"/>
                    </g>
                </svg>
            </div>
        </div>
    )
};

export const Ground = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <Handle
                type="source"
                position={Position.Top}
            />
            <Handle
                type="target"
                position={Position.Top}
            />
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="M75 0v75m-50 0h100m-56.25 50h12.5M50 100h50"/>
                </svg>
            </div>
        </>
    )
};

export const Vcc = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <Handle
                type="source"
                position={Position.Bottom}
            />
            <Handle
                type="target"
                position={Position.Bottom}
            />
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" transform="rotate(180,75,75)" d="M75 0v62.5m-50 0h100L75 125 25 62.5z"/>
                </svg>
            </div>
        </>
    )
};


export const Signal = ( { data }: {data: NodeProps} ) => {
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div style={{width: '100px', height: '100px'}}>
            <Handle
                type="source"
                position={Position.Bottom}
            />
            <Handle
                type="target"
                position={Position.Bottom}
            />
        </div>
    )
};

export const OpAmp = ( { data }: {data: NodeProps} ) => {
    const port_ids = Object.keys(data.ports);
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <>
            <Handle
                type="source"
                id={data.ports[1]['net_id']}
                position={Position.Left}
                style={{ top: `35px`}}
            />
            <Handle
                type="target"
                id={data.ports[1]['net_id']}
                position={Position.Left}
                style={{ top: `35px`}}
            />
            <Handle
                type="source"
                id={data.ports[0]['net_id']}
                position={Position.Left}
                style={{ top: `65px`}}
            />
            <Handle
                type="target"
                id={data.ports[0]['net_id']}
                position={Position.Left}
                style={{ top: `65px`}}
            />
            <Handle
                type="source"
                id={data.ports[2]['net_id']}
                position={Position.Right}
                style={{ top: `50px`}}
            />
            <Handle
                type="target"
                id={data.ports[2]['net_id']}
                position={Position.Right}
                style={{ top: `50px`}}
            />
            <Handle
                type="source"
                id={data.ports[3]['net_id']}
                position={Position.Top}
                style={{ left: `50px`}}
            />
            <Handle
                type="target"
                id={data.ports[3]['net_id']}
                position={Position.Top}
                style={{ left: `50px`}}
            />
            <Handle
                type="source"
                id={data.ports[4]['net_id']}
                position={Position.Bottom}
                style={{ left: `50px`}}
            />
            <Handle
                type="target"
                id={data.ports[4]['net_id']}
                position={Position.Bottom}
                style={{ left: `50px`}}
            />
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 150 150" transform="scale(1,-1)">
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5" d="M25 25v100l100-50L25 25zm0 25H0m125 25h25M0 100h25m9.5-47H53m-9.25-9.25v18.5M34.5 97H53M74.69 0v50m.37 100v-50"/>
                </svg>
            </div>
        </>
    )
};


export const NPN = ( { data }: {data: NodeProps} ) => {
    const port_ids = Object.keys(data.ports);
    // From: https://github.com/chris-pikul/electronic-symbols/tree/main
    return (
        <div style={{transform: 'rotate(90deg)'}}>
            <Handle
                type="source"
                id={data.ports[0]['net_id']}
                position={Position.Top}
                style={{ left: `33px`}}
            />
            <Handle
                type="target"
                id={data.ports[0]['net_id']}
                position={Position.Top}
                style={{ left: `33px`}}
            />
            <Handle
                type="source"
                id={data.ports[1]['net_id']}
                position={Position.Right}
            />
            <Handle
                type="target"
                id={data.ports[1]['net_id']}
                position={Position.Right}
            />
            <Handle
                type="source"
                id={data.ports[2]['net_id']}
                position={Position.Bottom}
                style={{ left: `33px`}}
            />
            <Handle
                type="target"
                id={data.ports[2]['net_id']}
                position={Position.Bottom}
                style={{ left: `33px`}}
            />
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 150 150" transform="scale(-1,1)">
                    <circle cx="75" cy="75" r="50" fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5"/>
                    <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="2.5" d="M100 150v-31.25M0 75h50m0-31.25v62.5M100 0v40.5l-50 22m0 25 37.52 22.47"/>
                    <path d="m81.8 115.26 14.95.24-7.27-13.07-7.68 12.83z"/>
                </svg>
            </div>
        </div>
    )
};

export const Bug = ({ data }: {data: NodeProps}) => {

    const LeftPins = Object.entries(data.ports).map(([key, value], index) => {
        console.log("key")
        console.log(key)
        return (<React.Fragment key={key}>
                <Handle
                    type="source"
                    id={key}
                    position={Position.Left}
                    style={{ top: `${10 + index * 15}px`}}
                />
                <Handle
                    type="target"
                    id={key}
                    position={Position.Left}
                    style={{ top: `${10 + index * 15}px`}}
                />
                <div style={{height: '15px', top: `${10 + index * 15}px`, fontSize: '8px'}}>
                    {value}
                </div>
            </React.Fragment>)
    });

    return (
        <>
            <div style={{display: 'flex', alignItems: 'center', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: '#FFF' }}>
                <div style={{display: 'flex', flexDirection: 'column', paddingRight: '10px'}}>
                    {LeftPins}
                </div>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                    <div style={{textAlign: 'center'}}>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.name}</div>
                    </div>
                </div>
            </div>
        </>
    )
};
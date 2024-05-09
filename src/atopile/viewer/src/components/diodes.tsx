//@ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import { SchematicElectronicComponent } from './SchematicElements';
import { Handle, useUpdateNodeInternals, Position } from 'reactflow';


const DiodeComponent = ({ id, data, svgContent}) => {
    const [rotation, setRotation] = useState(0);
    const [mirror, setMirror] = useState(false);
    const [position, setCompPosition] = useState({ x: 0, y: 0 });
    const updateNodeInternals = useUpdateNodeInternals();
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

    return RenderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
    };


// LED
const LEDSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
        <path fill="blue" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
        <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
        <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
        <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
    </svg>
);

export const LED = ({ data }) => {
    return <DiodeComponent data={data} svgContent={LEDSvg} />;
};

// Shottky Diode
const ShottkyDiodeSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
        <g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
            <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
            <path d="M87.5 97v12.5H100v-69h12.5V53"/>
        </g>
    </svg>
);

export const ZenerDiode = ({ id, data }) => {
    const [rotation, setRotation] = useState(0);
    const [mirror, setMirror] = useState(false);
    const [position, setCompPosition] = useState({ x: 0, y: 0 });
    const updateNodeInternals = useUpdateNodeInternals();
    // const adjustedPorts = [
    //     {
    //         id: data.ports[0].net_id,
    //         initialPosition: Position.LEFT,
    //         name: data.ports[0].name,
    //         offset: 35,
    //         offset_dir: Position.TOP
    //     },
    //     {
    //         id: data.ports[1].net_id,
    //         initialPosition: Position.RIGHT,
    //         name: data.ports[1].name,
    //         offset: 25,
    //         offset_dir: Position.TOP
    //     }
    //     ];

    // return RenderElectronicComponent({ ...data, ports: adjustedPorts }, svgContent);
    useEffect(() => {
        setRotation(data.rotation);
        setMirror(data.mirror);
        setCompPosition(data.position);
        updateNodeInternals(id);
    }, [data]); // Only re-run if `data` changes

    function handleRotation() {
        setRotation(rotation + 1);
        console.log(rotation);
        console.log(id);
        updateNodeInternals(id);
    }
    return (
        <>
          <Handle
              type="source"
              id={data.ports[0].net_id}
              position={"top"}
              style={{ left: `${rotation}px`} }
          />
          <Handle
              type="target"
              id={data.ports[0].net_id}
              position={"top"}
              style={{ left: `${rotation}px`} }
          />
          <div style={{ width: '50px', height: '50px' }}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
             <g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
                 <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
                 <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
             </g>
         </svg>
          </div>
          <button onClick={handleRotation}>Rotate</button>
        </>
      );
    };

// Zenner Diode
// const ZenerDiodeSvg = (
//     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
//         <g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
//             <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
//             <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
//         </g>
//     </svg>
// );

// export const ZenerDiode = ({ data }) => {
//     return <DiodeComponent data={data} svgContent={ZenerDiodeSvg} />;
// }

// Diode
const DiodeSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
        <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50"/>
    </svg>
);

export const Diode = ({ data }) => {
    return <DiodeComponent data={data} svgContent={DiodeSvg} />;
}

// @ts-nocheck
import { Position, RenderElectronicComponent } from './SchematicElements';


const DiodeComponent = ({ data, svgContent }) => {
    // Adjust the ports data to include static mapping of anode and cathode
    const portsArray = Array.isArray(data.ports) ? data.ports : Object.values(data.ports);
    const adjustedPorts = portsArray.map(port => {
        switch (port.name) {
            case 'anode':
                return {
                    ...port,
                    id: data.ports[0].net_id,
                    initialPosition: Position.LEFT,
                    offset: 25,
                    offset_dir: Position.TOP
                };
            case 'cathode':
                return {
                    ...port,
                    id: data.ports[1].net_id,
                    initialPosition: Position.RIGHT,
                    offset: 25,
                    offset_dir: Position.TOP
                };
            default:
                throw new Error("Unsupported port configuration");
        }
    });

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

export const ShottkyDiode = ({ data }) => {
    return <DiodeComponent data={data} svgContent={ShottkyDiodeSvg} />;
}

// Zenner Diode
const ZenerDiodeSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
        <g fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5">
            <path d="m100 75-50 31.25v-62.5L100 75zm-50 0H0m100 0h50"/>
            <path d="M112.5 109.5 100 100V50l-12.5-9.5"/>
        </g>
    </svg>
);

export const ZenerDiode = ({ data }) => {
    return <DiodeComponent data={data} svgContent={ZenerDiodeSvg} />;
}

// Diode
const DiodeSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 150 150">
        <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50"/>
    </svg>
);

export const Diode = ({ data }) => {
    return <DiodeComponent data={data} svgContent={DiodeSvg} />;
}




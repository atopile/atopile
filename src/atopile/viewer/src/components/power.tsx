//@ts-nocheck
import {RenderElectronicComponent } from './SchematicElements';


const PowerComponent = ({ data, svgContent }) => {
    // Adjust the ports data to include static mapping of anode and cathode

    return RenderElectronicComponent(data, svgContent);
    };


// VCC
const VCCSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
        <path fill="blue" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
        <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
        <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
        <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
    </svg>
);

export const VCC = ({ data }) => {
    return <PowerComponent data={data} svgContent={VCCSvg} />;
};

// GND
const GNDSvg = (
    <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
        <path fill="blue" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m100 75-50 31.25v-62.5L100 75zm0-34.25v68.5M50 75H0m100 0h50m-50-43.75 18.75-18.75"/>
        <path d="m122.49 19.34 3.87-14.45-14.45 3.87 10.58 10.58z"/>
        <path fill="none" stroke="#000" strokeMiterlimit="10" strokeWidth="5" d="m118.75 50 18.75-18.75"/>
        <path d="m141.24 38.09 3.87-14.45-14.45 3.87 10.58 10.58z"/>
    </svg>
);

export const GND = ({ data }) => {
    return <PowerComponent data={data} svgContent={GNDSvg} />;
};
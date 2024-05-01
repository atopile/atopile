// @ts-nocheck
import { useCallback, useEffect, useLayoutEffect, useState } from 'react';

import { Schematic } from "@tscircuit/schematic-viewer"

export async function loadSchematicJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/schematic-data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

export const SchematicElements = ({ data }) => {
    const renderComponent = (component) => {
        const x = Math.random() * 4;
        const y = Math.random() * 4;
        switch (component.instance_of) {
            case 'Resistor':
                return <resistor name={component.name} x={x} y={y} />;
            case 'Capacitor':
                return <capacitor name={component.name} x={x} y={y} />;
            case 'Inductor':
                return <resistor name={component.name} x={x} y={y} />;
            default:
                return
        }
    };

    // Convert the dictionary values to an array and map over it
    const componentsArray = Object.values(data);

    return (
        <Schematic style={{ minHeight: '30%' }}>
            {componentsArray.map(component => renderComponent(component))}
        </Schematic>
    )
};
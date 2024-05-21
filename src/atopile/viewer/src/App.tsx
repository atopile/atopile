// @ts-nocheck
import { BrowserRouter, Route, Routes, useNavigate, useLocation } from "react-router-dom";
import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Panel,
} from 'reactflow';

import AtopileSchematicApp from './SchematicApp.tsx';
import AtopileBlockDiagramApp from './BlockDiagramApp.tsx';

import { useURLBlockID } from './utils.tsx';

const App = () => {
    const [parentBlockId, setParentBlockId] = useState('none');
    const [reLayout, setReLayout] = useState(false);
    const [schematicModeEnabled, setSchematicModeEnabled] = useState(false);

    const navigate = useNavigate();

    const { block_id } = useURLBlockID();

    function handleReturnClick() {
        if (parentBlockId === 'none' || parentBlockId === 'null') {
            console.log('no parent block id');
            return;
        }
        // return click only works in block diagram mode
        navigate(`/?block_id=${parentBlockId}`);
    }

    function handleLoad(view_mode: string, parent_block_id: string = parentBlockId) {
        setParentBlockId(parent_block_id);
        setReLayout(true);
        setSchematicModeEnabled(view_mode === 'schematic');
    }

    function handleReLayout() {
        setReLayout(true);
    }

    function reLayoutCleared() {
        setReLayout(false);
    }

    function handleModeSwitch() {
        if (schematicModeEnabled) {
            navigate(`/?block_id=${block_id}`);
        } else {
            navigate(`/schematic?block_id=${block_id}`);
        }
    }

    async function savePos(addr, pos, rotation, mirror_x, mirror_y) {
        const mode = schematicModeEnabled ? 'schematic' : 'block-diagram';
        const url = `http://127.0.0.1:8080/${mode}/${addr}/pose`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                "position": pos,
                "rotation": rotation,
                "mirror_x": mirror_x,
                "mirror_y": mirror_y
              })
          });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }


    return (
        <>
            <ReactFlowProvider>
                    <Routes>
                        <Route path="/" element={<AtopileBlockDiagramApp savePos={savePos} handleLoad={handleLoad} reLayout={reLayout} reLayoutCleared={reLayoutCleared} />} />
                        <Route path="/schematic" element={<AtopileSchematicApp savePos={savePos} handleLoad={handleLoad} />} />
                    </Routes>
                <Panel position="top-left">
                    <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                        <div style={{textAlign: 'center'}}> Model inspection pane</div>
                        <div><i>Inspecting:</i> <b>{block_id}</b></div>
                        <div><i>Parent:</i> {parentBlockId}</div>
                        <div>Mode: {schematicModeEnabled ? 'schematic' : 'block diagram'}</div>
                        <button style={{margin: '5px'}} onClick={() => handleReturnClick()} disabled={schematicModeEnabled} >return</button>
                        <button style={{margin: '5px'}} onClick={() => handleReLayout()} disabled={schematicModeEnabled} >re-layout</button>
                        <button style={{margin: '5px'}} onClick={() => handleModeSwitch()}>{schematicModeEnabled ? 'block diagram' : 'schematic'}</button>
                    </div>
                </Panel>
            </ReactFlowProvider>
        </>
    );
}

export default App;

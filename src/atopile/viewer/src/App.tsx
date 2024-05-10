// @ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Panel,
} from 'reactflow';

import AtopileSchematicApp from './SchematicApp.tsx';
import AtopileBlockDiagramApp from './BlockDiagramApp.tsx';


let activeApp;

const App = () => {
    const [viewBlockId, setViewBlockId] = useState('root');
    const [parentBlockId, setParentBlockId] = useState('none');
    const [reLayout, setReLayout] = useState(false);
    const [reload, setReload] = useState(false);
    const [schematicModeEnabled, setSchematicModeEnabled] = useState(false);

    function handleReturnClick() {
        if (parentBlockId === 'none' || parentBlockId === 'null') {
            console.log('no parent block id');
            return;
        }
        setViewBlockId(parentBlockId);
    }

    function handleExploreClick(block_id: string) {
        setViewBlockId(block_id);
    }

    function handleBlockLoad(parent_block_id: string) {
        setParentBlockId(parent_block_id);
        setReLayout(true);
    }

    function handleReLayout() {
        setReLayout(true);
    }

    function reLayoutCleared() {
        setReLayout(false);
    }

    function handleModeSwitch() {
        setSchematicModeEnabled(!schematicModeEnabled);
    }

    function handleSavePos() {
        console.log('save pos');
        savePos("/Users/timot/Dev/atopile/community-projects/viewer-test/elec/src/viewer-test.ato:ViewerTest::amp")
    }

    async function savePos(addr, pos, angle) {
        const mode = schematicModeEnabled ? 'schematic' : 'block-diagram';
        const url = `http://127.0.0.1:8080/${mode}/${addr}/pose`;
        const response = await fetch(url, {
            method: 'POST', // Set the method to POST
            headers: {
              'Content-Type': 'application/json' // Set the content type header for sending JSON
            },
            body: JSON.stringify({
                "angle": angle,
                "x": pos.x,
                "y": pos.y
              })
          });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    activeApp = schematicModeEnabled ?
        <AtopileSchematicApp
            viewBlockId={viewBlockId}
            savePos={savePos}
            reload={reload}
        />
        :
        <AtopileBlockDiagramApp
            viewBlockId={viewBlockId}
            handleBlockLoad={handleBlockLoad}
            handleExploreClick={handleExploreClick}
            reLayout={reLayout}
            reLayoutCleared={reLayoutCleared}
            savePos={savePos}
            />;


    return (
        <>
            <ReactFlowProvider>
                {activeApp}
                <Panel position="top-left">
                    <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                        <div style={{textAlign: 'center'}}> Model inspection pane</div>
                        <div><i>Inspecting:</i> <b>{viewBlockId}</b></div>
                        <div><i>Parent:</i> {parentBlockId}</div>
                        <div>Mode: {schematicModeEnabled ? 'schematic' : 'block diagram'}</div>
                        <button style={{margin: '5px'}} onClick={() => handleReturnClick()} disabled={schematicModeEnabled} >return</button>
                        <button style={{margin: '5px'}} onClick={() => handleReLayout()} disabled={schematicModeEnabled} >re-layout</button>
                        <button style={{margin: '5px'}} onClick={() => handleModeSwitch()}>{schematicModeEnabled ? 'block diagram' : 'schematic'}</button>
                        <button style={{margin: '5px'}} onClick={() => setReload(!reload)} disabled={!schematicModeEnabled}>reload</button>
                    </div>
                </Panel>
            </ReactFlowProvider>
        </>
    );
}

export default App;

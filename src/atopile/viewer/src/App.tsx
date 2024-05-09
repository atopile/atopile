// @ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Panel,
} from 'reactflow';

import AtopileSchematicApp from './SchematicApp.tsx';
import AtopileBlockDiagramApp from './BlockDiagramApp.tsx';

import AppOne from './AppOne.tsx';
import AppTwo from './AppTwo.tsx';

let activeApp;

const App = () => {
    const [viewBlockId, setViewBlockId] = useState('root');
    const [parentBlockId, setParentBlockId] = useState('none');
    const [reLayout, setReLayout] = useState(false);
    const [schematicModeEnabled, setSchematicModeEnabled] = useState(false);

    function handleReturnClick() {
        if (parentBlockId === 'none') {
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

    // useEffect(() => {
    //     activeApp = schematicModeEnabled ? <AtopileSchematicApp viewBlockId={viewBlockId} /> : <AtopileBlockDiagramApp viewBlockId={viewBlockId} handleBlockLoad={handleBlockLoad} handleExploreClick={handleExploreClick} reLayout={reLayout} reLayoutCleared={reLayoutCleared} />;
    // }, [schematicModeEnabled]);

    activeApp = schematicModeEnabled ? <AtopileSchematicApp viewBlockId={viewBlockId} /> : <AtopileBlockDiagramApp viewBlockId={viewBlockId} handleBlockLoad={handleBlockLoad} handleExploreClick={handleExploreClick} reLayout={reLayout} reLayoutCleared={reLayoutCleared} />;

    // useEffect(() => {
    //     activeApp = schematicModeEnabled ? <AppOne /> : <AppTwo />;
    // }, [schematicModeEnabled]);

    return (
        <>
            <ReactFlowProvider>
                {/* <AtopileSchematicApp viewBlockId={viewBlockId} />
                <AtopileBlockDiagramApp viewBlockId={viewBlockId} handleBlockLoad={handleBlockLoad} handleExploreClick={handleExploreClick} reLayout={reLayout} reLayoutCleared={reLayoutCleared} /> */}
                {activeApp}
                {/* <AtopileBlockDiagramApp viewBlockId={viewBlockId} handleBlockLoad={handleBlockLoad} handleExploreClick={handleExploreClick} reLayout={reLayout} reLayoutCleared={reLayoutCleared} /> */}
                {/* <AppOne />
                <AppTwo /> */}
            <Panel position="top-left">
                <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                    <div style={{textAlign: 'center'}}> Model inspection pane</div>
                    <div><i>Inspecting:</i> <b>{viewBlockId}</b></div>
                    <div><i>Parent:</i> {parentBlockId}</div>
                    <button onClick={() => handleReturnClick()}>return</button>
                    <button onClick={() => handleReLayout()}>re-layout</button>
                    <button onClick={() => handleModeSwitch()}>mode switch</button>
                </div>
            </Panel>
            </ReactFlowProvider>
        </>
    );
}

export default App;

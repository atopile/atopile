// @ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Panel,
} from 'reactflow';

import AtopileSchematicApp from './SchematicApp.tsx';
import AtopileBlockDiagramApp from './BlockDiagramApp.tsx';

const block_id = "root";
const parent_block_addr = "none";

function App() {
    return (
        <ReactFlowProvider>
            <AtopileBlockDiagramApp />
            {/* <AtopileSchematicViewer /> */}
            <Panel position="top-left">
                <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                    <div style={{textAlign: 'center'}}> Model inspection pane</div>
                    <div><i>Inspecting:</i> <b>{block_id}</b></div>
                    <div><i>Parent:</i> {parent_block_addr}</div>
                    <button onClick={() => handleExpandClick(parent_block_addr)}>return</button>
                    <button onClick={() => onLayout({ direction: 'DOWN' })}>re-layout</button>
                </div>
            </Panel>
        </ReactFlowProvider>
    );
}

export default App;
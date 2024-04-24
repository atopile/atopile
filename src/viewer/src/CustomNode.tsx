// @ts-nocheck
//import React, { memo } from 'react';
import { Handle, Position, NodeProps, NodeToolbar } from 'reactflow';

export const CustomNodeBlock = ({ data }: {data: NodeProps}) => {
    //TODO: is the type NodeProps?
    return (
        <>
            <Handle
                type="source"
                position={Position.Bottom}
                style={{background: '#555' }}
            />
            <Handle
                type="target"
                position={Position.Top}
                style={{background: '#555' }}
            />
            <div onClick={() => data.handleExpandClick(data.address)} style={{ width: '160px', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: data.color }}>
                <div style={{ fontSize: '8px'}}>{data.type}</div>
                <div style={{textAlign: 'center'}}>
                    <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                    <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.title}</div>
                </div>
            </div>
        </>
    )
};

export const CircularNodeComponent = ({ data }: {data: NodeProps}) => {
    return (
        <>
            <Handle
                type="target"
                position={Position.Top}
                style={{ background: '#555' }}
            />
            <div style={{ textAlign: 'center', padding: '10px', borderRadius: '50%', backgroundColor: data.color }}>
            <div>{data.instance_of}</div>
            <div style={{fontWeight: 'bold'}}>{data.title}</div>
            </div>

            <Handle
                type="source"
                position={Position.Bottom}
                style={{ background: '#555' }}
            />
        </>
    )
  };
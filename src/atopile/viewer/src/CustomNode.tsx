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

export const InterfaceNode = ({ data }: {data: NodeProps}) => {
    const LeftPins = data.interfaces.map((pin, index) => {
        return (<>
                <Handle
                    type="target"
                    id={pin}
                    position={Position.Left}
                    style={{ top: `${10 + index * 15}px`, background: '#555'}}
                />
                <div
                    style={{height: '15px',  top: `${10 + index * 15}px`, fontSize: '8px'}}>
                    {pin}
                </div>
            </>)
    });
    const RightPins = data.interfaces.map((pin, index) => {
        return (<>
                <Handle
                    type="source"
                    id={pin}
                    position={Position.Right}
                    style={{ top: `${10 + index * 15}px`, background: '#555'}}
                />
                <div
                    style={{height: '15px', left: '10px', fontSize: '8px'}}>
                    {pin}
                </div>
            </>)
    });
    return (
        <>
            <div onClick={() => data.handleExpandClick(data.address)} style={{display: 'flex', alignItems: 'center', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: data.color }}>
                <div style={{display: 'flex', flexDirection: 'column', paddingRight: '10px'}}>
                    {LeftPins}
                </div>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                    <div style={{textAlign: 'left', fontSize: '8px'}}>{data.type}</div>
                    <div style={{textAlign: 'center'}}>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.title}</div>
                    </div>
                </div>
                <div style={{display: 'flex', flexDirection: 'column', paddingLeft: '10px'}}>
                    {RightPins}
                </div>
            </div>
        </>
        )
}

export const ComponentNode = ({ data }: {data: NodeProps}) => {
    const LeftPins = data.interfaces.map((pin, index) => {
        return (<>
                <Handle
                    type="target"
                    id={pin}
                    position={Position.Left}
                    style={{ top: `${10 + index * 15}px`, background: '#555'}}
                />
                <div
                    style={{height: '15px',  top: `${10 + index * 15}px`, fontSize: '8px'}}>
                    {pin}
                </div>
            </>)
    });
    const RightPins = data.interfaces.map((pin, index) => {
        return (<>
                <Handle
                    type="source"
                    id={pin}
                    position={Position.Right}
                    style={{ top: `${10 + index * 15}px`, background: '#555'}}
                />
                <div
                    style={{height: '15px', left: '10px', fontSize: '8px'}}>
                    {pin}
                </div>
            </>)
    });
    return (
        <>
            <div onClick={() => data.handleExpandClick(data.address)} style={{display: 'flex', alignItems: 'center', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: data.color }}>
                <div style={{display: 'flex', flexDirection: 'column', paddingRight: '10px'}}>
                    {LeftPins}
                </div>
                <div style={{display: 'flex', flexDirection: 'column'}}>
                    <div style={{textAlign: 'left', fontSize: '8px'}}>{data.type}</div>
                    <div style={{textAlign: 'center'}}>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.title}</div>
                    </div>
                </div>
                <div style={{display: 'flex', flexDirection: 'column', paddingLeft: '10px'}}>
                    {RightPins}
                </div>
            </div>
        </>
        )
}
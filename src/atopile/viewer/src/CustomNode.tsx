// @ts-nocheck
import { Link } from "react-router-dom";
import { Handle, Position, NodeProps, NodeToolbar } from 'reactflow';

export const ModuleNode = ({ data }: {data: NodeProps}) => {
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
            <Link to={`?block_id=${data.address}`} style={{ textDecoration: 'none', color: 'inherit' }}>
                <div style={{ width: '160px', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: data.color }}>
                    <div style={{ fontSize: '8px'}}>{data.type}</div>
                    <div style={{textAlign: 'center'}}>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                        <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.title}</div>
                    </div>
                </div>
            </Link>
        </>
    )
};

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
            <div style={{ width: '160px', padding: '10px', paddingTop: '4px', borderRadius: '10px', backgroundColor: data.color }}>
                <div style={{ fontSize: '8px'}}>{data.type}</div>
                <div style={{textAlign: 'center'}}>
                    <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{data.instance_of}</div>
                    <div style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', fontWeight: 'bold'}}>{data.title}</div>
                </div>
            </div>
        </>
    )
};

// export const BuiltInNodeBlock = ({ data }: {data: NodeProps}) => {
//     //TODO: is the type NodeProps?
//     // From: https://github.com/chris-pikul/electronic-symbols/tree/main
//     let content;
//     if (data.lib_key === 'Capacitor') {
//         content = <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" transform="rotate(90,75,75)" d="M0 74.97h65.5m84.5.28H84.5m0-31.25v62m-19-62v62"/>;
//     } else if (data.lib_key === 'Resistor') {
//         content = <path fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="5" transform="rotate(90,75,75)" d="M25 56.25h100v37.5H25zM25 75H0m125 0h25"/>;
//     } else {
//         content = <path/>;
//     }
//     return (
//         <>
//             <Handle
//                 type="source"
//                 position={Position.Bottom}
//                 style={{background: '#555' }}
//             />
//             <Handle
//                 type="target"
//                 position={Position.Top}
//                 style={{background: '#555' }}
//             />
//             <div onClick={() => data.handleExpandClick(data.address)} style={{ display: 'flex', padding: '10px', paddingTop: '4px', paddingBottom: '4px', borderRadius: '10px', backgroundColor: "#FFFFFF"}}>
//                 <svg xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 150 150">
//                     {content}
//                 </svg>
//                 <div style={{textAlign: 'left', width: '100px'}}>
//                     <div style={{ fontSize: '8px'}}>value: <b>{data.value}</b></div>
//                     <div style={{fontSize: '10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100px' }}>{data.instance_of}</div>
//                     <div style={{fontSize: '10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100px', fontWeight: 'bold'}}>{data.title}</div>
//                 </div>
//             </div>
//         </>
//     )
// };

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
// @ts-nocheck
import { useState } from 'react';
import {
    BaseEdge,
    EdgeLabelRenderer,
    EdgeProps,
    getBezierPath,
    //useReactFlow,
    } from 'reactflow';

import './edge_style.css';

function EdgeLabel({ transform, label, isClicked }: { transform: string; label: string; isClicked: boolean}) {
    if (!isClicked) return null;
    return (
    <div
        style={{
            position: 'absolute',
            background: 'transparent',
            padding: 10,
            fontSize: 12,
            fontWeight: 700,
            transform,
        }}
        className="nodrag nopan edge-label"
    >
        {label}
    </div>
    );
  }

export default function CustomEdge({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    markerEnd,
    data,
}: EdgeProps) {

    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    return (
        <>
        <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
        <div className="edge-label">
            <EdgeLabelRenderer>
                <div
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%)translate(${labelX}px,${labelY}px)`,
                        padding: 10,
                        borderRadius: 5,
                        fontSize: 12,
                        fontWeight: 700,
                        pointerEvents: 'all',
                    }}
                    className="nodrag nopan"
                >
                    <div className="customedge">
                        {data.name}
                    </div>
                </div>
            </EdgeLabelRenderer>
        </div>
        </>
    );
}
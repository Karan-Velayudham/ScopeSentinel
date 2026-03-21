"use client";

import React, { useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    Node,
    Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { yamlToWorkflowGraph } from '@/lib/workflow-parser';
import { TriggerNode } from '../workflow-designer/nodes/TriggerNode';
import { AgentNode } from '../workflow-designer/nodes/AgentNode';
import { HitlNode } from '../workflow-designer/nodes/HitlNode';
import { ToolNode } from '../workflow-designer/nodes/ToolNode';
import { ConditionNode } from '../workflow-designer/nodes/ConditionNode';

const nodeTypes = {
    triggerNode: TriggerNode,
    agentNode: AgentNode,
    hitlNode: HitlNode,
    toolNode: ToolNode,
    conditionNode: ConditionNode,
};

interface ExecutionReplayProps {
    yamlContent: string;
    steps: any[]; // RunStep objects
}

export function ExecutionReplay({ yamlContent, steps }: ExecutionReplayProps) {
    const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
        return yamlToWorkflowGraph(yamlContent);
    }, [yamlContent]);

    // M-7: Highlight nodes based on executed steps
    const nodes = useMemo(() => {
        return initialNodes.map(node => {
            // Find if this node corresponds to an executed step
            // Note: node.id in Designer matches step.id in YAML, which should match step_name or something in RunStep
            // Actually, in our parser, step.id is used as node.id.
            const executedStep = steps.find(s => s.step_id === node.id || s.step_name === node.id);

            if (executedStep) {
                const status = executedStep.status; // SUCCEEDED, FAILED, RUNNING
                let borderColor = '#94a3b8'; // default
                let bgColor = undefined;

                if (status === 'SUCCEEDED') borderColor = '#22c55e';
                if (status === 'FAILED') borderColor = '#ef4444';
                if (status === 'RUNNING') borderColor = '#3b82f6';

                return {
                    ...node,
                    style: {
                        ...node.style,
                        borderWidth: '3px',
                        borderColor: borderColor,
                        boxShadow: status === 'RUNNING' ? '0 0 10px #3b82f6' : undefined,
                    },
                    data: {
                        ...node.data,
                        executionStatus: status,
                    }
                };
            }
            return node;
        });
    }, [initialNodes, steps]);

    return (
        <div className="w-full h-full border rounded-lg overflow-hidden bg-background">
            <ReactFlow
                nodes={nodes}
                edges={initialEdges}
                nodeTypes={nodeTypes}
                fitView
                nodesConnectable={false}
                nodesDraggable={false}
                zoomOnScroll={false}
                panOnDrag={true}
            >
                <Background />
                <Controls />
            </ReactFlow>
        </div>
    );
}

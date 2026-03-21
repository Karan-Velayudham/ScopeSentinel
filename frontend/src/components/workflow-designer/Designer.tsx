"use client";

import React, { useState, useCallback, useRef } from 'react';
import {
    ReactFlow,
    ReactFlowProvider,
    addEdge,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    Connection,
    Edge,
    Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Sidebar } from './Sidebar';
import { ConfigPanel } from './ConfigPanel';
import { TriggerNode } from './nodes/TriggerNode';
import { AgentNode } from './nodes/AgentNode';
import { HitlNode } from './nodes/HitlNode';
import { ToolNode } from './nodes/ToolNode';
import { ConditionNode } from './nodes/ConditionNode';
import { apiFetch } from "@/lib/api-client";

const nodeTypes = {
    triggerNode: TriggerNode,
    agentNode: AgentNode,
    hitlNode: HitlNode,
    toolNode: ToolNode,
    conditionNode: ConditionNode,
};

let id = 0;
const getId = () => `node_${id++}`;

export function DesignerComponent({
    initialNodes = [],
    initialEdges = [],
    onSave
}: {
    initialNodes?: Node[],
    initialEdges?: Edge[],
    onSave: (nodes: Node[], edges: Edge[]) => void
}) {
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

    const onConnect = useCallback(
        (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
        [setEdges]
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const type = event.dataTransfer.getData('application/reactflow');
            const label = event.dataTransfer.getData('application/reactflow-label');

            if (typeof type === 'undefined' || !type) {
                return;
            }

            if (!reactFlowInstance) return;

            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode: Node = {
                id: getId(),
                type,
                position,
                data: { label: label || `${type} node` },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance, setNodes]
    );

    const updateNodeData = (nodeId: string, data: any) => {
        setNodes((nds) =>
            nds.map((node) => {
                if (node.id === nodeId) {
                    node.data = { ...node.data, ...data };
                }
                return node;
            })
        );
    };

    const selectedNode = nodes.find((n) => n.id === selectedNodeId);

    const [testRunOpen, setTestRunOpen] = useState(false);
    const [testTicketId, setTestTicketId] = useState("");

    const handleTestRun = async () => {
        if (!testTicketId.trim()) return;
        setTestRunOpen(false);
        try {
            const res = await apiFetch(`/api/runs`, {
                method: 'POST',
                body: JSON.stringify({ ticket_id: testTicketId.trim(), dry_run: false })
            });
            if (res.ok) {
                const data = await res.json();
                alert(`Test run initiated! Run ID: ${data.run_id}`);
            } else {
                alert("Test run failed. Check Temporal is running.");
            }
        } catch (e) {
            alert("Error initiating test run.");
        } finally {
            setTestTicketId("");
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-120px)] border rounded-lg overflow-hidden relative">
            <div className="flex h-12 items-center justify-between border-b bg-muted/30 px-4">
                <div className="font-semibold flex items-center gap-2">
                    <span>Visual Workflow Designer</span>
                </div>
                <div className="flex gap-2">
                    {/* M-2 Fix: Prompt for ticket_id via dialog instead of hardcoding */}
                    <button
                        className="px-3 py-1.5 text-sm border bg-card text-foreground rounded-md hover:bg-muted/50 transition-colors cursor-pointer"
                        onClick={() => setTestRunOpen(true)}
                    >
                        Test Run
                    </button>
                    <button
                        className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors cursor-pointer"
                        onClick={() => onSave(nodes, edges)}
                    >
                        Save YAML
                    </button>
                </div>
            </div>
            {/* Test Run Dialog */}
            {testRunOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
                    <div className="bg-card border rounded-lg shadow-xl p-6 w-96 space-y-4">
                        <h3 className="font-semibold text-lg">Trigger Test Run</h3>
                        <p className="text-sm text-muted-foreground">Enter a Jira ticket ID to trigger a test run of this workflow.</p>
                        <input
                            type="text"
                            className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                            placeholder="e.g. SCRUM-8"
                            value={testTicketId}
                            onChange={e => setTestTicketId(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleTestRun()}
                            autoFocus
                        />
                        <div className="flex gap-2 justify-end">
                            <button
                                className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted/50"
                                onClick={() => { setTestRunOpen(false); setTestTicketId(""); }}
                            >
                                Cancel
                            </button>
                            <button
                                className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                                onClick={handleTestRun}
                                disabled={!testTicketId.trim()}
                            >
                                Start Run
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <div className="flex flex-1 overflow-hidden">
                <Sidebar />
                <div className="flex-1 h-full" ref={reactFlowWrapper}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        onInit={setReactFlowInstance}
                        onDrop={onDrop}
                        onDragOver={onDragOver}
                        onNodeClick={(_, node) => setSelectedNodeId(node.id)}
                        onPaneClick={() => setSelectedNodeId(null)}
                        nodeTypes={nodeTypes}
                        fitView
                    >
                        <Controls />
                        <Background color="#ccc" gap={16} />
                    </ReactFlow>
                </div>
                <ConfigPanel selectedNode={selectedNode} updateNodeData={updateNodeData} />
            </div>
        </div>
    );
}

export function Designer(props: any) {
    return (
        <ReactFlowProvider>
            <DesignerComponent {...props} />
        </ReactFlowProvider>
    );
}

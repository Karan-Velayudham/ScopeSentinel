"use client";

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    ReactFlow,
    ReactFlowProvider,
    addEdge,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    BackgroundVariant,
    Connection,
    Edge,
    Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Share2, Save, Play, ChevronDown, Zap, LayoutGrid, Check, Loader2, X } from 'lucide-react';

import { Sidebar } from './Sidebar';
import { ConfigPanel } from './ConfigPanel';
import { TriggerNode } from './nodes/TriggerNode';
import { AgentNode } from './nodes/AgentNode';
import { HitlNode } from './nodes/HitlNode';
import { ToolNode } from './nodes/ToolNode';
import { ConditionNode } from './nodes/ConditionNode';
import { InputNode } from './nodes/InputNode';
import { OutputNode } from './nodes/OutputNode';
import { OAuthConnectModal } from './OAuthConnectModal';
import { apiFetch } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

const nodeTypes = {
    triggerNode: TriggerNode,
    agentNode: AgentNode,
    hitlNode: HitlNode,
    toolNode: ToolNode,
    conditionNode: ConditionNode,
    inputNode: InputNode,
    outputNode: OutputNode,
};

let nodeCount = 0;
const getId = () => `node_${++nodeCount}`;

// ─── DesignerComponent ────────────────────────────────────────────────────────

export function DesignerComponent({
    workflowId,
    initialName = 'New Workflow',
    initialNodes = [],
    initialEdges = [],
    initialStatus = 'draft',
    onSave,
}: {
    workflowId?: string;
    initialName?: string;
    initialNodes?: Node[];
    initialEdges?: Edge[];
    initialStatus?: string;
    onSave: (nodes: Node[], edges: Edge[], name: string) => void;
}) {
    const reactFlowWrapper = useRef<HTMLDivElement>(null);
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [workflowName, setWorkflowName] = useState(initialName);
    const [isEditingName, setIsEditingName] = useState(false);
    const [status, setStatus] = useState(initialStatus);
    const [saveDropdownOpen, setSaveDropdownOpen] = useState(false);
    const [connectModal, setConnectModal] = useState<{ connector: any } | null>(null);
    const [activating, setActivating] = useState(false);
    const [saved, setSaved] = useState(false);

    // Run Modal State
    const router = useRouter();
    const [runModalOpen, setRunModalOpen] = useState(false);
    const [runInputs, setRunInputs] = useState<Record<string, string>>({});
    const [running, setRunning] = useState(false);

    const onConnect = useCallback(
        (params: Connection | Edge) => setEdges(eds => addEdge({ ...params, animated: true }, eds)),
        [setEdges]
    );

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault();

            const type = event.dataTransfer.getData('application/reactflow/type');
            const label = event.dataTransfer.getData('application/reactflow/label');
            const rawData = event.dataTransfer.getData('application/reactflow/data');

            if (!type) return;
            if (!reactFlowInstance) return;

            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            let extraData: Record<string, any> = {};
            try { extraData = JSON.parse(rawData); } catch { }

            const newNode: Node = {
                id: getId(),
                type,
                position,
                data: { label: label || type, ...extraData },
            };

            setNodes(nds => nds.concat(newNode));
        },
        [reactFlowInstance, setNodes]
    );

    const updateNodeData = useCallback((nodeId: string, data: any) => {
        setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data } : n));
    }, [setNodes]);

    const selectedNode = nodes.find(n => n.id === selectedNodeId);

    // ── Save handler ──────────────────────────────────────────────────────────
    const handleSave = () => {
        onSave(nodes, edges, workflowName);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
    };

    // ── Activate / Deactivate ─────────────────────────────────────────────────
    const handleActivate = async () => {
        if (!workflowId) return;
        setActivating(true);
        try {
            const action = status === 'active' ? 'deactivate' : 'activate';
            const res = await apiFetch(`/api/workflows/${workflowId}/${action}`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                setStatus(data.status);
            }
        } finally {
            setActivating(false);
        }
    };

    // ── Run Handler ───────────────────────────────────────────────────────────
    const inputNode = nodes.find(n => n.type === 'inputNode');
    const inputFields = (inputNode?.data?.fields as any[]) || [];

    const handleRunClick = () => {
        if (!workflowId) {
            alert("Please save the workflow first before running it.");
            return;
        }
        if (inputFields.length > 0) {
            // Pre-fill defaults
            const defaults: Record<string, string> = {};
            inputFields.forEach(f => defaults[f.name] = f.defaultValue || '');
            setRunInputs(defaults);
            setRunModalOpen(true);
        } else {
            handleExecuteRun({});
        }
    };

    const handleExecuteRun = async (inputs: Record<string, string>) => {
        setRunning(true);
        try {
            const res = await apiFetch('/api/runs/', {
                method: 'POST',
                body: JSON.stringify({
                    workflow_id: workflowId,
                    inputs,
                    dry_run: false
                }),
            });
            if (res.ok) {
                const data = await res.json();
                router.push(`/runs/${data.id}`);
            } else {
                const err = await res.json();
                alert(`Run failed: ${err.detail}`);
            }
        } catch (e) {
            console.error(e);
            alert("Failed to start workflow run.");
        } finally {
            setRunning(false);
            setRunModalOpen(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-64px)] border rounded-lg overflow-hidden bg-background">

            {/* ── Top Bar ───────────────────────────────────────────────────── */}
            <div className="flex h-12 items-center gap-3 border-b bg-card px-4 shrink-0">
                {/* Workflow name */}
                <div className="flex items-center gap-1.5">
                    <div className="h-6 w-6 rounded bg-primary flex items-center justify-center">
                        <LayoutGrid className="h-3.5 w-3.5 text-primary-foreground" />
                    </div>
                    {isEditingName ? (
                        <input
                            autoFocus
                            className="text-sm font-semibold outline-none border-b border-primary bg-transparent"
                            value={workflowName}
                            onChange={e => setWorkflowName(e.target.value)}
                            onBlur={() => setIsEditingName(false)}
                            onKeyDown={e => e.key === 'Enter' && setIsEditingName(false)}
                        />
                    ) : (
                        <button
                            onClick={() => setIsEditingName(true)}
                            className="text-sm font-semibold hover:text-primary transition-colors"
                        >
                            {workflowName}
                        </button>
                    )}

                    {/* Status badge */}
                    <span className={`text-[10px] font-mono rounded-full px-2 py-0.5 ${status === 'active'
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                        : status === 'paused'
                            ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                            : 'bg-muted text-muted-foreground'
                        }`}>{status}</span>
                </div>

                <div className="flex-1" />

                {/* Add Trigger button */}
                <button
                    onClick={() => {
                        const trigNode: Node = {
                            id: getId(),
                            type: 'triggerNode',
                            position: { x: 60, y: 100 },
                            data: { label: 'Manual Trigger', triggerType: 'manual' },
                        };
                        setNodes(nds => nds.concat(trigNode));
                    }}
                    className="flex items-center gap-1.5 text-xs border rounded-md px-3 py-1.5 hover:bg-muted/50 transition-colors"
                >
                    <Zap className="h-3.5 w-3.5" /> Add Trigger
                </button>

                {/* Activate / Deactivate */}
                {workflowId && (
                    <button
                        disabled={activating}
                        onClick={handleActivate}
                        className={`flex items-center gap-1.5 text-xs rounded-md px-3 py-1.5 transition-colors font-medium ${status === 'active'
                            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-300'
                            : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300'
                            }`}
                    >
                        {activating ? '…' : status === 'active' ? 'Deactivate' : 'Activate'}
                    </button>
                )}

                {/* Share */}
                <button className="flex items-center gap-1.5 text-xs border rounded-md px-3 py-1.5 hover:bg-muted/50 transition-colors">
                    <Share2 className="h-3.5 w-3.5" /> Share
                </button>

                {/* Save */}
                <div className="relative">
                    <div className="flex items-center border rounded-md overflow-hidden">
                        <button
                            onClick={handleSave}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 transition-colors font-medium ${saved
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                : 'bg-card hover:bg-muted/50'
                                }`}
                        >
                            {saved ? <Check className="h-3.5 w-3.5" /> : <Save className="h-3.5 w-3.5" />}
                            {saved ? 'Saved' : 'Save'}
                        </button>
                        <button
                            onClick={() => setSaveDropdownOpen(!saveDropdownOpen)}
                            className="border-l px-1.5 py-1.5 hover:bg-muted/50 transition-colors"
                        >
                            <ChevronDown className="h-3 w-3" />
                        </button>
                    </div>
                    {saveDropdownOpen && (
                        <div className="absolute right-0 top-full mt-1 bg-card border rounded-md shadow-lg z-50 min-w-36 text-sm">
                            <button onClick={() => { handleSave(); setSaveDropdownOpen(false); }}
                                className="w-full text-left px-3 py-2 hover:bg-muted/50">Save</button>
                            <button className="w-full text-left px-3 py-2 hover:bg-muted/50 text-muted-foreground text-xs">Export YAML</button>
                        </div>
                    )}
                </div>

                {/* Run */}
                <button
                    onClick={handleRunClick}
                    disabled={running}
                    className="flex items-center gap-1.5 text-xs bg-primary text-primary-foreground rounded-md px-3 py-1.5 hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                >
                    {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                    {running ? 'Starting...' : 'Run'}
                </button>
            </div>

            {/* ── Canvas Area ────────────────────────────────────────────────── */}
            <div className="flex flex-1 overflow-hidden">
                <Sidebar onConnectClick={connector => setConnectModal({ connector })} />

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
                        onPaneClick={() => { setSelectedNodeId(null); setSaveDropdownOpen(false); }}
                        nodeTypes={nodeTypes}
                        fitView
                        defaultEdgeOptions={{ animated: true, style: { strokeWidth: 1.5 } }}
                    >
                        <Controls />
                        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
                    </ReactFlow>
                </div>

                <ConfigPanel selectedNode={selectedNode} updateNodeData={updateNodeData} />
            </div>

            {/* ── OAuth Connect Modal ────────────────────────────────────────── */}
            {connectModal && (
                <OAuthConnectModal
                    connector={connectModal.connector}
                    onClose={() => setConnectModal(null)}
                    onConnected={() => {
                        setConnectModal(null);
                        // Sidebar will refetch on next render
                        window.location.reload();
                    }}
                />
            )}
            {/* ── Run Modal ───────────────────────────────────────────────────── */}
            {runModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="w-[450px] bg-background border rounded-lg shadow-xl flex flex-col overflow-hidden">
                        <div className="flex items-center justify-between p-4 border-b">
                            <h2 className="font-semibold text-lg flex items-center gap-2">
                                <Play className="h-4 w-4" /> Run Workflow
                            </h2>
                            <button onClick={() => setRunModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                        <div className="p-4 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
                            <p className="text-sm text-muted-foreground">
                                Provide the required inputs to start execution.
                            </p>
                            {inputFields.map((field) => (
                                <div key={field.name} className="flex flex-col gap-1.5">
                                    <label className="text-sm font-medium">
                                        {field.name} <span className="text-muted-foreground font-normal">({field.type})</span>
                                        {field.required && <span className="text-destructive ml-1">*</span>}
                                    </label>
                                    <input
                                        type={field.type === 'number' ? 'number' : 'text'}
                                        required={field.required}
                                        value={runInputs[field.name] || ''}
                                        onChange={(e) => setRunInputs({ ...runInputs, [field.name]: e.target.value })}
                                        className="text-sm px-3 py-2 rounded-md border bg-background"
                                        placeholder={`Enter ${field.name}...`}
                                    />
                                    {field.description && <p className="text-xs text-muted-foreground">{field.description}</p>}
                                </div>
                            ))}
                        </div>
                        <div className="p-4 border-t bg-muted/30 flex justify-end gap-2">
                            <button
                                onClick={() => setRunModalOpen(false)}
                                className="px-4 py-2 text-sm rounded-md hover:bg-muted"
                            >
                                Cancel
                            </button>
                            <button
                                disabled={running}
                                onClick={() => handleExecuteRun(runInputs)}
                                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-2"
                            >
                                {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                                Start Run
                            </button>
                        </div>
                    </div>
                </div>
            )}
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

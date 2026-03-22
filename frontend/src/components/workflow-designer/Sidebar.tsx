"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    Search, Play, Bot, Hammer, GitBranch, UserCheck, Clock, LogIn, LogOut,
    MessageSquare, Globe, Zap, ChevronDown, ChevronRight, PlugZap, Link2, Loader2
} from 'lucide-react';
import { apiFetch } from '@/lib/api-client';

// ─── Types ──────────────────────────────────────────────────────────────────

interface NodeDef {
    type: string;
    label: string;
    description: string;
    icon: any;
    color: string;           // Tailwind bg class for the icon badge
    textColor?: string;
    defaultData?: Record<string, any>;
}

interface ConnectorTool {
    name: string;
    description: string;
    inputs: any[];
}

interface InstalledConnector {
    id: string;
    connector_id: string;
    connector_name: string;
    icon_url: string;
    auth_type: string;
    is_active: boolean;
    tools: ConnectorTool[];
}

interface AvailableConnector {
    id: string;
    name: string;
    description: string;
    category: string;
    icon_url: string;
    auth_type: string;
    tools: ConnectorTool[];
}

// ─── Node definitions ───────────────────────────────────────────────────────

const CORE_NODES: NodeDef[] = [
    {
        type: 'inputNode',
        label: 'Input',
        description: 'Entry point for the workflow',
        icon: LogIn,
        color: 'bg-slate-500',
        defaultData: { label: 'Input', fields: [] },
    },
    {
        type: 'outputNode',
        label: 'Output',
        description: 'Terminal — marks end of workflow',
        icon: LogOut,
        color: 'bg-slate-500',
        defaultData: { label: 'Output' },
    },
    {
        type: 'conditionNode',
        label: 'Router',
        description: 'Branch workflow based on a condition',
        icon: GitBranch,
        color: 'bg-yellow-500',
        defaultData: { label: 'Condition', expression: '' },
    },
    {
        type: 'triggerNode',
        label: 'Webhook',
        description: 'Trigger on inbound HTTP webhook',
        icon: Globe,
        color: 'bg-emerald-600',
        defaultData: { label: 'Webhook', triggerType: 'webhook', eventType: '' },
    },
    {
        type: 'delayNode',
        label: 'Delay',
        description: 'Pause execution for a duration',
        icon: Clock,
        color: 'bg-slate-400',
        defaultData: { label: 'Delay', duration_seconds: 300 },
    },
];

const AI_NODES: NodeDef[] = [
    {
        type: 'agentNode',
        label: 'Agent',
        description: 'Run an agent with tools and a goal',
        icon: Bot,
        color: 'bg-violet-600',
        defaultData: { label: 'Agent', model: 'gpt-4o', tools: [] },
    },
    {
        type: 'agentNode',
        label: 'Ask AI',
        description: 'Single-turn LLM prompt → response',
        icon: MessageSquare,
        color: 'bg-violet-500',
        defaultData: { label: 'Ask AI', model: 'gpt-4o', max_iterations: 1 },
    },
    {
        type: 'agentNode',
        label: 'Classify',
        description: 'Classify input into categories',
        icon: Zap,
        color: 'bg-pink-500',
        defaultData: { label: 'Classify', model: 'gpt-4o', categories: [] },
    },
];

const TRIGGER_NODES: NodeDef[] = [
    {
        type: 'triggerNode',
        label: 'Manual',
        description: 'User-initiated via UI or API',
        icon: Play,
        color: 'bg-emerald-600',
        defaultData: { label: 'Manual Trigger', triggerType: 'manual' },
    },
    {
        type: 'triggerNode',
        label: 'Webhook',
        description: 'Inbound HTTP POST from any system',
        icon: Globe,
        color: 'bg-emerald-600',
        defaultData: { label: 'Webhook Trigger', triggerType: 'webhook' },
    },
    {
        type: 'triggerNode',
        label: 'Schedule',
        description: 'Time-based cron trigger',
        icon: Clock,
        color: 'bg-emerald-600',
        defaultData: { label: 'Scheduled Trigger', triggerType: 'cron', schedule: '0 9 * * 1-5' },
    },
    {
        type: 'triggerNode',
        label: 'Event',
        description: 'Internal platform event',
        icon: Zap,
        color: 'bg-emerald-600',
        defaultData: { label: 'Event Trigger', triggerType: 'event' },
    },
    {
        type: 'hitlNode',
        label: 'HITL Gate',
        description: 'Pause for human approval',
        icon: UserCheck,
        color: 'bg-amber-500',
        defaultData: { label: 'Approval Gate', timeout_hours: 24, message: '' },
    },
];

// ─── DraggableItem ───────────────────────────────────────────────────────────

function DraggableItem({ node, onDragStart }: { node: NodeDef; onDragStart: (e: React.DragEvent, node: NodeDef, extra?: any) => void }) {
    const Icon = node.icon;
    return (
        <div
            className="flex items-center gap-2.5 px-2 py-1.5 rounded-md cursor-grab hover:bg-muted/60 transition-colors select-none"
            draggable
            onDragStart={(e) => onDragStart(e, node)}
        >
            <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${node.color} text-white`}>
                <Icon className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0">
                <div className="text-sm font-medium leading-tight">{node.label}</div>
                <div className="text-xs text-muted-foreground leading-tight truncate">{node.description}</div>
            </div>
        </div>
    );
}

// ─── Section ─────────────────────────────────────────────────────────────────

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="flex w-full items-center gap-1 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
            >
                {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                {title}
            </button>
            {open && <div className="pb-1">{children}</div>}
        </div>
    );
}

// ─── IntegrationSection ───────────────────────────────────────────────────────

function IntegrationSection({
    onDragStart,
    onConnectClick,
}: {
    onDragStart: (e: React.DragEvent, node: NodeDef, extra?: any) => void;
    onConnectClick: (connector: AvailableConnector) => void;
}) {
    const [installed, setInstalled] = useState<InstalledConnector[]>([]);
    const [available, setAvailable] = useState<AvailableConnector[]>([]);
    const [expanded, setExpanded] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchConnectors = async () => {
            try {
                const [insRes, avRes] = await Promise.all([
                    apiFetch('/api/connectors/installed'),
                    apiFetch('/api/connectors/available'),
                ]);
                const insData = insRes.ok ? await insRes.json() : [];
                const avData = avRes.ok ? await avRes.json() : [];
                setInstalled(insData);
                setAvailable(avData);
            } catch {
            } finally {
                setLoading(false);
            }
        };
        fetchConnectors();
    }, []);

    const installedIds = new Set(installed.map(c => c.connector_id));

    if (loading) {
        return (
            <div className="flex items-center gap-2 px-2 py-2 text-xs text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" /> Loading integrations…
            </div>
        );
    }

    return (
        <div className="space-y-0.5">
            {/* Installed connectors */}
            {installed.map(connector => (
                <div key={connector.connector_id} className="border rounded-md overflow-hidden mb-1">
                    <button
                        onClick={() => setExpanded(e => ({ ...e, [connector.connector_id]: !e[connector.connector_id] }))}
                        className="flex w-full items-center gap-2 px-2 py-1.5 bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                        <img src={connector.icon_url} alt="" className="h-4 w-4 rounded object-contain" onError={e => (e.currentTarget.style.display = 'none')} />
                        <span className="text-sm font-medium flex-1 text-left truncate">{connector.connector_name}</span>
                        <span className="text-[9px] font-mono bg-violet-100 text-violet-700 dark:bg-violet-900/50 dark:text-violet-300 rounded px-1 py-0.5">MCP</span>
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                        {expanded[connector.connector_id] ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
                    </button>
                    {expanded[connector.connector_id] && (
                        <div className="border-t bg-background">
                            {connector.tools.length === 0 && (
                                <div className="text-xs text-muted-foreground px-3 py-2">No tools available</div>
                            )}
                            {connector.tools.map(tool => (
                                <div
                                    key={tool.name}
                                    className="flex items-start gap-2 px-3 py-1.5 cursor-grab hover:bg-muted/40 transition-colors border-b last:border-b-0"
                                    draggable
                                    onDragStart={(e) => onDragStart(e, {
                                        type: 'toolNode',
                                        label: tool.name,
                                        description: tool.description,
                                        icon: Hammer,
                                        color: 'bg-indigo-600',
                                        defaultData: {
                                            label: tool.name,
                                            connector_id: connector.connector_id,
                                            connector_name: connector.connector_name,
                                            tool_name: tool.name,
                                        },
                                    })}
                                >
                                    <Hammer className="h-3 w-3 mt-0.5 text-muted-foreground shrink-0" />
                                    <div className="min-w-0">
                                        <div className="text-xs font-medium font-mono text-slate-700 dark:text-slate-200 truncate">{tool.name}</div>
                                        <div className="text-[10px] text-muted-foreground leading-tight">{tool.description}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}

            {/* Available (uninstalled) connectors */}
            {available.filter(c => !installedIds.has(c.id)).map(connector => (
                <div key={connector.id} className="flex items-center gap-2 px-2 py-1.5 rounded-md opacity-60">
                    <img src={connector.icon_url} alt="" className="h-4 w-4 rounded object-contain" onError={e => (e.currentTarget.style.display = 'none')} />
                    <span className="text-sm flex-1 truncate">{connector.name}</span>
                    <button
                        onClick={() => onConnectClick(connector)}
                        className="text-xs bg-primary text-primary-foreground rounded px-2 py-0.5 hover:bg-primary/90 transition-colors shrink-0"
                    >
                        Connect
                    </button>
                </div>
            ))}
        </div>
    );
}

// ─── Main Sidebar ─────────────────────────────────────────────────────────────

export function Sidebar({
    onConnectClick,
}: {
    onConnectClick?: (connector: AvailableConnector) => void;
}) {
    const [search, setSearch] = useState('');

    const onDragStart = useCallback((event: React.DragEvent, node: NodeDef, _extra?: any) => {
        event.dataTransfer.setData('application/reactflow/type', node.type);
        event.dataTransfer.setData('application/reactflow/label', node.label);
        event.dataTransfer.setData('application/reactflow/data', JSON.stringify(node.defaultData || {}));
        event.dataTransfer.effectAllowed = 'move';
    }, []);

    const filterNodes = (nodes: NodeDef[]) =>
        nodes.filter(n =>
            !search ||
            n.label.toLowerCase().includes(search.toLowerCase()) ||
            n.description.toLowerCase().includes(search.toLowerCase())
        );

    const showIntegrations = !search || 'integrations'.includes(search.toLowerCase());

    return (
        <div className="w-64 border-r bg-card flex flex-col h-full">
            {/* Search */}
            <div className="p-3 border-b">
                <div className="flex items-center gap-2 bg-muted/40 rounded-md px-2 py-1.5">
                    <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <input
                        className="bg-transparent text-sm outline-none w-full placeholder:text-muted-foreground"
                        placeholder="Search all nodes"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
            </div>

            {/* Node sections */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {/* Core Nodes */}
                <Section title="Core Nodes">
                    {filterNodes(CORE_NODES).map(n => (
                        <DraggableItem key={n.label} node={n} onDragStart={onDragStart} />
                    ))}
                </Section>

                {/* AI Nodes */}
                <Section title="Using AI">
                    {filterNodes(AI_NODES).map(n => (
                        <DraggableItem key={n.label} node={n} onDragStart={onDragStart} />
                    ))}
                </Section>

                {/* Triggers */}
                <Section title="Triggers">
                    {filterNodes(TRIGGER_NODES).map(n => (
                        <DraggableItem key={n.label} node={n} onDragStart={onDragStart} />
                    ))}
                </Section>

                {/* Integrations */}
                {showIntegrations && (
                    <Section title="Integrations" defaultOpen={true}>
                        <IntegrationSection
                            onDragStart={onDragStart}
                            onConnectClick={onConnectClick || (() => { })}
                        />
                    </Section>
                )}
            </div>
        </div>
    );
}

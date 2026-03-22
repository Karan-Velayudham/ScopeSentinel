"use client";

import { useState, useEffect } from "react";
import { X, Plus, Trash2, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConnectorTool {
    name: string;
    description: string;
    inputs: any[];
}

interface InstalledConnector {
    connector_id: string;
    connector_name: string;
    icon_url: string;
    tools: ConnectorTool[];
}

// ─── Helper components ────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</label>
            {children}
        </div>
    );
}

function TextInput({ value, onChange, placeholder = '', mono = false }: {
    value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean;
}) {
    return (
        <input
            className={`w-full border rounded-md px-2.5 py-1.5 text-sm bg-background outline-none focus:ring-1 focus:ring-ring ${mono ? 'font-mono text-xs' : ''}`}
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
        />
    );
}

function TextArea({ value, onChange, placeholder = '' }: {
    value: string; onChange: (v: string) => void; placeholder?: string;
}) {
    return (
        <textarea
            className="w-full border rounded-md px-2.5 py-1.5 text-sm bg-background outline-none focus:ring-1 focus:ring-ring resize-none"
            rows={4}
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
        />
    );
}

function SelectInput({ value, onChange, options }: {
    value: string; onChange: (v: string) => void; options: { value: string; label: string }[];
}) {
    return (
        <select
            className="w-full border rounded-md px-2.5 py-1.5 text-sm bg-background outline-none focus:ring-1 focus:ring-ring"
            value={value}
            onChange={e => onChange(e.target.value)}
        >
            {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
    );
}

// ─── MCP Tool Checklist ───────────────────────────────────────────────────────

function McpToolChecklist({ selectedTools, onChange }: {
    selectedTools: string[];
    onChange: (tools: string[]) => void;
}) {
    const [connectors, setConnectors] = useState<InstalledConnector[]>([]);
    const [expanded, setExpanded] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiFetch('/api/connectors/installed')
            .then(r => r.json())
            .then(data => { setConnectors(data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const toggle = (toolKey: string) => {
        onChange(
            selectedTools.includes(toolKey)
                ? selectedTools.filter(t => t !== toolKey)
                : [...selectedTools, toolKey]
        );
    };

    if (loading) return <div className="flex items-center gap-1 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /> Loading tools…</div>;
    if (connectors.length === 0) return <div className="text-xs text-muted-foreground">No integrations connected yet.</div>;

    return (
        <div className="border rounded-md overflow-hidden divide-y">
            {connectors.map(c => (
                <div key={c.connector_id}>
                    <button
                        onClick={() => setExpanded(e => ({ ...e, [c.connector_id]: !e[c.connector_id] }))}
                        className="flex w-full items-center gap-2 px-2.5 py-1.5 bg-muted/30 hover:bg-muted/50 text-left"
                    >
                        <img src={c.icon_url} alt="" className="h-3.5 w-3.5 object-contain" onError={e => (e.currentTarget.style.display = 'none')} />
                        <span className="text-xs font-medium flex-1">{c.connector_name}</span>
                        {expanded[c.connector_id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                    {expanded[c.connector_id] && (
                        <div className="bg-background">
                            {c.tools.map(tool => {
                                const key = `${c.connector_id}:${tool.name}`;
                                const checked = selectedTools.includes(key);
                                return (
                                    <label key={key} className="flex items-start gap-2 px-3 py-1.5 hover:bg-muted/30 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={checked}
                                            onChange={() => toggle(key)}
                                            className="mt-0.5 h-3.5 w-3.5"
                                        />
                                        <div>
                                            <div className="text-xs font-mono font-medium">{tool.name}</div>
                                            <div className="text-[10px] text-muted-foreground">{tool.description}</div>
                                        </div>
                                    </label>
                                );
                            })}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

// ─── Agent selector ───────────────────────────────────────────────────────────

function AgentSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [agents, setAgents] = useState<any[]>([]);
    useEffect(() => {
        apiFetch('/api/agents').then(r => r.json()).then(d => setAgents(d.items || [])).catch(() => { });
    }, []);
    return (
        <SelectInput
            value={value || 'none'}
            onChange={v => onChange(v === 'none' ? '' : v)}
            options={[
                { value: 'none', label: '— Default Agent —' },
                ...agents.map(a => ({ value: a.id, label: `${a.name} (${a.model})` })),
            ]}
        />
    );
}

// ─── Per-type panels ──────────────────────────────────────────────────────────

function TriggerConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    return (
        <>
            <Field label="Trigger Type">
                <SelectInput value={data.triggerType || 'manual'} onChange={v => update('triggerType', v)} options={[
                    { value: 'manual', label: 'Manual' },
                    { value: 'webhook', label: 'Webhook' },
                    { value: 'cron', label: 'Schedule (Cron)' },
                    { value: 'event', label: 'Platform Event' },
                    { value: 'message', label: 'Chat Message' },
                ]} />
            </Field>
            {data.triggerType === 'webhook' && (
                <Field label="Event Filter (JMESPath)">
                    <TextInput value={data.eventFilter || ''} onChange={v => update('eventFilter', v)} placeholder="action == 'opened'" mono />
                </Field>
            )}
            {data.triggerType === 'cron' && (
                <Field label="Cron Schedule">
                    <TextInput value={data.schedule || '0 9 * * 1-5'} onChange={v => update('schedule', v)} placeholder="0 9 * * 1-5" mono />
                </Field>
            )}
            {data.triggerType === 'event' && (
                <Field label="Event Topic">
                    <TextInput value={data.eventType || ''} onChange={v => update('eventType', v)} placeholder="t.{org}.workflow.run_completed" mono />
                </Field>
            )}
        </>
    );
}

function AgentConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    return (
        <>
            <Field label="Agent">
                <AgentSelector value={data.agent_id || ''} onChange={v => update('agent_id', v)} />
            </Field>
            <Field label="Model Override">
                <SelectInput value={data.model || 'gpt-4o'} onChange={v => update('model', v)} options={[
                    { value: 'gpt-4o', label: 'GPT-4o' },
                    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
                    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
                ]} />
            </Field>
            <Field label="Goal / Prompt">
                <TextArea value={data.goal || ''} onChange={v => update('goal', v)} placeholder="Describe what this agent should accomplish..." />
            </Field>
            <Field label="Memory Mode">
                <SelectInput value={data.memory_mode || 'session'} onChange={v => update('memory_mode', v)} options={[
                    { value: 'session', label: 'Session (short-term)' },
                    { value: 'long_term', label: 'Long-term (Qdrant)' },
                ]} />
            </Field>
            <Field label="Max Iterations">
                <TextInput value={String(data.max_iterations ?? 10)} onChange={v => update('max_iterations', parseInt(v) || 10)} placeholder="10" />
            </Field>
            <Field label="Allowed Tools (MCP)">
                <McpToolChecklist
                    selectedTools={Array.isArray(data.tools) ? data.tools : []}
                    onChange={v => update('tools', v)}
                />
            </Field>
        </>
    );
}

function ToolConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    const args: Record<string, string> = data.args || {};
    const setArg = (k: string, v: string) => update('args', { ...args, [k]: v });
    const removeArg = (k: string) => {
        const next = { ...args };
        delete next[k];
        update('args', next);
    };
    const addArg = () => update('args', { ...args, '': '' });

    return (
        <>
            <Field label="Connector">
                <div className="text-sm px-2.5 py-1.5 bg-muted rounded-md font-mono">{data.connector_id || '—'}</div>
            </Field>
            <Field label="Tool">
                <div className="text-sm px-2.5 py-1.5 bg-muted rounded-md font-mono">{data.tool_name || '—'}</div>
            </Field>
            <Field label="Input Bindings">
                <div className="space-y-1.5">
                    {Object.entries(args).map(([k, v]) => (
                        <div key={k} className="flex items-center gap-1.5">
                            <input
                                className="border rounded px-2 py-1 text-xs font-mono bg-background w-28 outline-none"
                                value={k}
                                onChange={e => {
                                    const newArgs = { ...args };
                                    delete newArgs[k];
                                    newArgs[e.target.value] = v;
                                    update('args', newArgs);
                                }}
                                placeholder="key"
                            />
                            <span className="text-muted-foreground text-xs">→</span>
                            <input
                                className="border rounded px-2 py-1 text-xs font-mono bg-background flex-1 outline-none"
                                value={v}
                                onChange={e => setArg(k, e.target.value)}
                                placeholder="{{ steps.prev.outputs.result }}"
                            />
                            <button onClick={() => removeArg(k)} className="text-muted-foreground hover:text-destructive">
                                <Trash2 className="h-3 w-3" />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={addArg}
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                        <Plus className="h-3 w-3" /> Add binding
                    </button>
                </div>
            </Field>
        </>
    );
}

function HitlConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    return (
        <>
            <Field label="Review Message">
                <TextArea value={data.message || ''} onChange={v => update('message', v)} placeholder="Describe what the reviewer should evaluate..." />
            </Field>
            <Field label="Timeout (hours)">
                <TextInput value={String(data.timeout_hours ?? 24)} onChange={v => update('timeout_hours', parseInt(v) || 24)} />
            </Field>
            <Field label="On Timeout">
                <SelectInput value={data.on_timeout || 'abort'} onChange={v => update('on_timeout', v)} options={[
                    { value: 'abort', label: 'Abort workflow' },
                    { value: 'approve', label: 'Auto-approve' },
                ]} />
            </Field>
            <Field label="Slack Notification Channel">
                <TextInput value={data.notify_channel || ''} onChange={v => update('notify_channel', v)} placeholder="#approvals" />
            </Field>
        </>
    );
}

function ConditionConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    return (
        <>
            <Field label="Expression">
                <TextArea
                    value={data.expression || ''}
                    onChange={v => update('expression', v)}
                    placeholder="{{ steps.classify.outputs.confidence >= 0.85 }}"
                />
            </Field>
            <div className="text-xs text-muted-foreground bg-muted/40 rounded-md p-2">
                <div className="font-medium mb-1">Available variables:</div>
                <div className="font-mono space-y-0.5">
                    <div>{'{{ trigger.payload.<field> }}'}</div>
                    <div>{'{{ steps.<id>.outputs.<key> }}'}</div>
                    <div>{'{{ inputs.<field> }}'}</div>
                </div>
            </div>
        </>
    );
}

function InputNodeConfig({ data, update }: { data: any; update: (k: string, v: any) => void }) {
    const fields: Array<{ name: string; type: string; required: boolean }> = data.fields || [];

    const addField = () => update('fields', [...fields, { name: '', type: 'string', required: true }]);
    const removeField = (i: number) => update('fields', fields.filter((_, idx) => idx !== i));
    const updateField = (i: number, key: string, val: any) => {
        const updated = fields.map((f, idx) => idx === i ? { ...f, [key]: val } : f);
        update('fields', updated);
    };

    return (
        <Field label="Input Fields">
            <div className="space-y-2">
                {fields.map((f, i) => (
                    <div key={i} className="border rounded-md p-2 space-y-1.5 bg-muted/20">
                        <div className="flex items-center gap-1">
                            <input
                                className="border rounded px-2 py-1 text-xs bg-background flex-1 outline-none font-mono"
                                value={f.name}
                                onChange={e => updateField(i, 'name', e.target.value)}
                                placeholder="field_name"
                            />
                            <button onClick={() => removeField(i)} className="text-muted-foreground hover:text-destructive p-1">
                                <X className="h-3 w-3" />
                            </button>
                        </div>
                        <div className="flex items-center gap-2">
                            <select
                                className="border rounded px-2 py-1 text-xs bg-background flex-1 outline-none"
                                value={f.type}
                                onChange={e => updateField(i, 'type', e.target.value)}
                            >
                                <option value="string">string</option>
                                <option value="number">number</option>
                                <option value="boolean">boolean</option>
                                <option value="object">object</option>
                            </select>
                            <label className="flex items-center gap-1 text-xs">
                                <input
                                    type="checkbox"
                                    checked={f.required}
                                    onChange={e => updateField(i, 'required', e.target.checked)}
                                    className="h-3 w-3"
                                />
                                required
                            </label>
                        </div>
                    </div>
                ))}
                <button
                    onClick={addField}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                    <Plus className="h-3 w-3" /> Add field
                </button>
            </div>
        </Field>
    );
}

// ─── Main ConfigPanel ─────────────────────────────────────────────────────────

const NODE_TYPE_LABELS: Record<string, string> = {
    inputNode: 'Input',
    outputNode: 'Output',
    triggerNode: 'Trigger',
    agentNode: 'Agent',
    toolNode: 'Integration Tool',
    hitlNode: 'HITL Gate',
    conditionNode: 'Condition',
    delayNode: 'Delay',
};

export function ConfigPanel({
    selectedNode,
    updateNodeData,
}: {
    selectedNode: any;
    updateNodeData: (id: string, data: any) => void;
}) {
    if (!selectedNode) {
        return (
            <div className="w-72 border-l bg-card flex flex-col items-center justify-center p-4 text-center">
                <div className="text-muted-foreground text-sm">Select a node to configure</div>
            </div>
        );
    }

    const data = selectedNode.data;
    const update = (key: string, value: any) => {
        updateNodeData(selectedNode.id, { ...data, [key]: value });
    };

    return (
        <div className="w-72 border-l bg-card flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b">
                <div>
                    <div className="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                        {NODE_TYPE_LABELS[selectedNode.type] || selectedNode.type}
                    </div>
                    <div className="text-sm font-semibold mt-0.5">{data.label || 'Untitled'}</div>
                </div>
            </div>

            {/* Fields */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Common: node label */}
                <Field label="Label">
                    <TextInput value={data.label || ''} onChange={v => update('label', v)} placeholder="Node label" />
                </Field>

                {/* Type-specific config */}
                {selectedNode.type === 'triggerNode' && <TriggerConfig data={data} update={update} />}
                {selectedNode.type === 'agentNode' && <AgentConfig data={data} update={update} />}
                {selectedNode.type === 'toolNode' && <ToolConfig data={data} update={update} />}
                {selectedNode.type === 'hitlNode' && <HitlConfig data={data} update={update} />}
                {selectedNode.type === 'conditionNode' && <ConditionConfig data={data} update={update} />}
                {selectedNode.type === 'inputNode' && <InputNodeConfig data={data} update={update} />}
                {selectedNode.type === 'delayNode' && (
                    <Field label="Delay Duration (seconds)">
                        <TextInput
                            value={String(data.duration_seconds ?? 300)}
                            onChange={v => update('duration_seconds', parseInt(v) || 300)}
                        />
                    </Field>
                )}

                {/* On Failure — available for all step nodes except input/trigger/output */}
                {!['inputNode', 'outputNode', 'triggerNode'].includes(selectedNode.type) && (
                    <Field label="On Failure">
                        <SelectInput value={data.on_failure || 'abort'} onChange={v => update('on_failure', v)} options={[
                            { value: 'abort', label: 'Abort workflow' },
                            { value: 'retry', label: 'Retry (max 3 attempts)' },
                            { value: 'skip', label: 'Skip and continue' },
                        ]} />
                    </Field>
                )}
            </div>
        </div>
    );
}

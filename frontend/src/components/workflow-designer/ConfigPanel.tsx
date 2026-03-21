import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiFetch } from "@/lib/api-client";

export function ConfigPanel({ selectedNode, updateNodeData }: { selectedNode: any, updateNodeData: (id: string, data: any) => void }) {
    if (!selectedNode) {
        return (
            <div className="w-80 border-l bg-card p-4 text-sm text-muted-foreground flex items-center justify-center">
                Select a node to configure
            </div>
        );
    }

    const handleChange = (key: string, value: any) => {
        updateNodeData(selectedNode.id, { ...selectedNode.data, [key]: value });
    };

    return (
        <div className="w-80 border-l bg-card flex flex-col h-full">
            <div className="p-4 border-b font-medium">Configuration</div>
            <div className="p-4 flex flex-col gap-4 overflow-y-auto">

                <div className="space-y-2">
                    <Label>Node Type</Label>
                    <div className="text-sm px-3 py-2 bg-muted rounded-md">{selectedNode.type}</div>
                </div>

                <div className="space-y-2">
                    <Label>Label</Label>
                    <Input
                        value={selectedNode.data.label || ''}
                        onChange={(e) => handleChange('label', e.target.value)}
                    />
                </div>

                {selectedNode.type === 'triggerNode' && (
                    <div className="space-y-2">
                        <Label>Trigger Event</Label>
                        <Input
                            value={selectedNode.data.type || ''}
                            onChange={(e) => handleChange('type', e.target.value)}
                            placeholder="e.g. github.push"
                        />
                    </div>
                )}

                {selectedNode.type === 'agentNode' && (
                    <div className="space-y-2">
                        <Label>Agent Type</Label>
                        <Select
                            value={selectedNode.data.agentType || 'planner'}
                            onValueChange={(v) => handleChange('agentType', v)}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="planner">Planner</SelectItem>
                                <SelectItem value="coder">Coder</SelectItem>
                                <SelectItem value="analyzer">Analyzer</SelectItem>
                                <SelectItem value="custom">Custom (Generic)</SelectItem>
                            </SelectContent>
                        </Select>

                        <Label className="pt-2">Specialized Agent (Optional)</Label>
                        <AgentSelector
                            value={selectedNode.data.agent_id || ''}
                            onChange={(v) => handleChange('agent_id', v)}
                        />

                        <Label className="pt-2">Direct Instructions Override</Label>
                        <Input
                            value={selectedNode.data.instructions || ''}
                            onChange={(e) => handleChange('instructions', e.target.value)}
                            placeholder="System prompt override..."
                        />
                        <Label className="pt-2">Inputs Bindings</Label>
                        <Input
                            value={selectedNode.data.inputsBinding || ''}
                            onChange={(e) => handleChange('inputsBinding', e.target.value)}
                            placeholder="{{ steps.xyz.output }}"
                        />
                    </div>
                )}

            </div>
        </div>
    );
}

function AgentSelector({ value, onChange }: { value: string, onChange: (v: string) => void }) {
    const [agents, setAgents] = useState<any[]>([]);

    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await apiFetch('/api/agents');
                const data = await res.json();
                setAgents(data.items || []);
            } catch (e) {
                console.error("Failed to fetch agents", e);
            } finally {
                // Done loading
            }
        };
        fetchAgents();
    }, []);

    return (
        <Select value={value || "none"} onValueChange={(v) => onChange(v === "none" ? "" : v)}>
            <SelectTrigger>
                <SelectValue placeholder="Using Default Agent" />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value="none">Use Default {value ? "" : "(Current)"}</SelectItem>
                {agents.map((agent: any) => (
                    <SelectItem key={agent.id} value={agent.id}>
                        {agent.name} ({agent.model})
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}

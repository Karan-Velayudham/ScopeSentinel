import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
                        <Input
                            value={selectedNode.data.agentType || ''}
                            onChange={(e) => handleChange('agentType', e.target.value)}
                            placeholder="e.g. planner, coder"
                        />
                        <Label className="pt-2">Instructions</Label>
                        <Input
                            value={selectedNode.data.instructions || ''}
                            onChange={(e) => handleChange('instructions', e.target.value)}
                            placeholder="System prompt..."
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

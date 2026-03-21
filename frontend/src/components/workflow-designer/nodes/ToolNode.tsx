import { Handle, Position } from '@xyflow/react';
import { Hammer, GripVertical } from 'lucide-react';

export function ToolNode({ data }: { data: any }) {
    return (
        <div className="flex items-center rounded-md border bg-card shadow-sm min-w-[220px]">
            <div className="flex h-full w-6 cursor-grab items-center justify-center border-r bg-muted/50 drag-handle">
                <GripVertical className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="flex flex-1 items-center gap-3 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300">
                    <Hammer className="h-4 w-4" />
                </div>
                <div>
                    <div className="font-medium text-sm">{data.label || 'Tool Call'}</div>
                    <div className="text-xs text-muted-foreground">{data.toolName || 'Any Tool'}</div>
                </div>
            </div>
            <Handle type="target" position={Position.Left} className="w-3 h-3 bg-muted-foreground" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 bg-muted-foreground" />
        </div>
    );
}

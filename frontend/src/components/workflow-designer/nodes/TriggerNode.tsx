import { Handle, Position } from '@xyflow/react';
import { Play } from 'lucide-react';

export function TriggerNode({ data }: { data: any }) {
    return (
        <div className="flex items-center gap-3 rounded-md border bg-card p-3 shadow-sm min-w-[200px]">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-300">
                <Play className="h-4 w-4" />
            </div>
            <div>
                <div className="font-medium text-sm">{data.label || 'Trigger'}</div>
                <div className="text-xs text-muted-foreground">{data.type || 'Event'}</div>
            </div>
            <Handle type="source" position={Position.Right} className="w-3 h-3 bg-muted-foreground" />
        </div>
    );
}

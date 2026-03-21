import { Handle, Position } from '@xyflow/react';
import { Split, GripVertical } from 'lucide-react';

export function ConditionNode({ data }: { data: any }) {
    return (
        <div className="flex flex-col rounded-md border bg-card shadow-sm min-w-[220px]">
            <div className="flex items-center border-b bg-muted/30">
                <div className="flex py-2 w-6 cursor-grab items-center justify-center border-r bg-muted/50 drag-handle">
                    <GripVertical className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex flex-1 items-center gap-3 p-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded-md bg-yellow-100 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-300">
                        <Split className="h-3 w-3" />
                    </div>
                    <div className="font-medium text-sm">{data.label || 'Condition'}</div>
                </div>
            </div>
            <div className="flex flex-col gap-2 p-3 relative h-16">
                <Handle type="target" position={Position.Left} className="w-3 h-3 bg-muted-foreground" style={{ top: '50%' }} />

                <div className="flex justify-between items-center text-xs">
                    <span className="text-muted-foreground">True</span>
                    <Handle type="source" position={Position.Right} id="true" className="w-2 h-2 bg-green-500" style={{ top: '25%' }} />
                </div>
                <div className="flex justify-between items-center text-xs mt-1">
                    <span className="text-muted-foreground">False</span>
                    <Handle type="source" position={Position.Right} id="false" className="w-2 h-2 bg-red-500" style={{ top: '75%' }} />
                </div>
            </div>
        </div>
    );
}

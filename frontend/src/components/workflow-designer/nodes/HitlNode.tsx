import { Handle, Position } from '@xyflow/react';
import { UserCheck, GripVertical } from 'lucide-react';

export function HitlNode({ data }: { data: any }) {
    return (
        <div className="flex items-center rounded-md border border-orange-200 bg-orange-50 dark:bg-orange-950/30 dark:border-orange-900 shadow-sm min-w-[220px]">
            <div className="flex h-full w-6 cursor-grab items-center justify-center border-r border-orange-200 dark:border-orange-900 bg-orange-100 dark:bg-orange-900/50 drag-handle">
                <GripVertical className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            </div>
            <div className="flex flex-1 items-center gap-3 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-orange-200 text-orange-700 dark:bg-orange-800 dark:text-orange-300">
                    <UserCheck className="h-4 w-4" />
                </div>
                <div>
                    <div className="font-medium text-sm text-orange-900 dark:text-orange-100">{data.label || 'HITL Gate'}</div>
                    <div className="text-xs text-orange-700/80 dark:text-orange-300/80">Require Approval</div>
                </div>
            </div>
            <Handle type="target" position={Position.Left} className="w-3 h-3 bg-orange-500" />
            <Handle type="source" position={Position.Right} className="w-3 h-3 bg-orange-500" />
        </div>
    );
}

import { Handle, Position } from '@xyflow/react';
import { LogOut } from 'lucide-react';

export function OutputNode({ data }: { data: any }) {
    return (
        <div className="flex flex-col rounded-lg border-2 border-slate-300 bg-white shadow-md min-w-[200px] overflow-hidden dark:bg-slate-900 dark:border-slate-600">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-100 border-b border-slate-200 dark:bg-slate-800 dark:border-slate-600">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-slate-500 text-white">
                    <LogOut className="h-3.5 w-3.5" />
                </div>
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">OUTPUT</span>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Output'}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Terminal — marks end of workflow</div>
            </div>
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-slate-400" />
        </div>
    );
}

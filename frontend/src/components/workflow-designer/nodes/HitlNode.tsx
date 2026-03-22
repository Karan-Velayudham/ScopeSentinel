import { Handle, Position } from '@xyflow/react';
import { UserCheck, Clock } from 'lucide-react';

export function HitlNode({ data }: { data: any }) {
    const timeout = data.timeout_hours ? `${data.timeout_hours}h timeout` : null;

    return (
        <div className="flex flex-col rounded-lg border-2 border-amber-400 bg-white shadow-md min-w-[210px] overflow-hidden dark:bg-slate-900 dark:border-amber-500">
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-500 border-b border-amber-400">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-white/20">
                    <UserCheck className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="text-xs font-semibold text-white uppercase tracking-wide">Human Review</span>
                {timeout && (
                    <div className="ml-auto flex items-center gap-0.5 text-xs bg-white/20 text-white rounded px-1.5 py-0.5">
                        <Clock className="h-2.5 w-2.5" />{timeout}
                    </div>
                )}
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Approval Gate'}</div>
                {data.message && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{data.message}</p>
                )}
            </div>
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-amber-400" />
            <Handle type="source" position={Position.Right} id="approved" className="!w-3 !h-3 !bg-green-400" style={{ top: '35%' }} />
            <Handle type="source" position={Position.Right} id="rejected" className="!w-3 !h-3 !bg-red-400" style={{ top: '65%' }} />
        </div>
    );
}

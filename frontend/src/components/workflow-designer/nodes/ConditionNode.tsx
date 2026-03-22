import { Handle, Position } from '@xyflow/react';
import { GitBranch } from 'lucide-react';

export function ConditionNode({ data }: { data: any }) {
    return (
        <div className="flex flex-col rounded-lg border-2 border-yellow-400 bg-white shadow-md min-w-[210px] overflow-hidden dark:bg-slate-900 dark:border-yellow-500">
            <div className="flex items-center gap-2 px-3 py-2 bg-yellow-400 border-b border-yellow-300 dark:bg-yellow-500">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-white/30">
                    <GitBranch className="h-3.5 w-3.5 text-yellow-900" />
                </div>
                <span className="text-xs font-semibold text-yellow-900 uppercase tracking-wide">Condition</span>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Branch'}</div>
                {data.expression && (
                    <div className="mt-1 text-xs font-mono bg-yellow-50 text-yellow-800 rounded px-2 py-1 line-clamp-2 dark:bg-yellow-900/30 dark:text-yellow-300">
                        {data.expression}
                    </div>
                )}
            </div>
            {/* Input */}
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-yellow-400" />
            {/* True branch — top-right */}
            <Handle
                type="source"
                position={Position.Right}
                id="true"
                className="!w-3 !h-3 !bg-green-400"
                style={{ top: '30%' }}
            />
            {/* False branch — bottom-right */}
            <Handle
                type="source"
                position={Position.Right}
                id="false"
                className="!w-3 !h-3 !bg-red-400"
                style={{ top: '70%' }}
            />
            {/* Branch labels */}
            <div className="absolute right-4 top-[22%] text-[10px] text-green-600 font-semibold select-none">TRUE</div>
            <div className="absolute right-4 top-[60%] text-[10px] text-red-500 font-semibold select-none">FALSE</div>
        </div>
    );
}

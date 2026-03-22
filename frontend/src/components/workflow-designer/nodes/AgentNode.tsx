import { Handle, Position } from '@xyflow/react';
import { Bot, Cpu, Wrench } from 'lucide-react';

export function AgentNode({ data }: { data: any }) {
    const toolCount = Array.isArray(data.tools) ? data.tools.length : 0;
    const modelLabel = data.model || 'gpt-4o';

    return (
        <div className="flex flex-col rounded-lg border-2 border-violet-400 bg-white shadow-md min-w-[220px] overflow-hidden dark:bg-slate-900 dark:border-violet-500">
            <div className="flex items-center gap-2 px-3 py-2 bg-violet-600 border-b border-violet-500">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-white/20">
                    <Bot className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="text-xs font-semibold text-white uppercase tracking-wide">Agent</span>
                <div className="ml-auto flex items-center gap-1">
                    {toolCount > 0 && (
                        <span className="flex items-center gap-0.5 text-xs bg-white/20 text-white rounded px-1.5 py-0.5">
                            <Wrench className="h-2.5 w-2.5" />{toolCount}
                        </span>
                    )}
                </div>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Agent Task'}</div>
                <div className="flex items-center gap-1 mt-1">
                    <Cpu className="h-3 w-3 text-violet-500" />
                    <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">{modelLabel}</span>
                </div>
                {data.goal && (
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{data.goal}</p>
                )}
            </div>
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-violet-400" />
            <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-violet-400" />
        </div>
    );
}

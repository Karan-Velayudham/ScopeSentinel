import { Handle, Position } from '@xyflow/react';
import { Hammer } from 'lucide-react';

// Map connector_id → brand color and emoji-like badge
const CONNECTOR_COLORS: Record<string, { border: string; header: string; dot: string }> = {
    github: { border: 'border-slate-700', header: 'bg-slate-800', dot: 'bg-slate-600' },
    gitlab: { border: 'border-orange-500', header: 'bg-orange-500', dot: 'bg-orange-400' },
    jira: { border: 'border-blue-500', header: 'bg-blue-600', dot: 'bg-blue-400' },
    linear: { border: 'border-indigo-500', header: 'bg-indigo-600', dot: 'bg-indigo-400' },
    slack: { border: 'border-purple-500', header: 'bg-purple-600', dot: 'bg-purple-400' },
    discord: { border: 'border-indigo-600', header: 'bg-indigo-700', dot: 'bg-indigo-500' },
    datadog: { border: 'border-violet-500', header: 'bg-violet-600', dot: 'bg-violet-400' },
    prometheus: { border: 'border-orange-600', header: 'bg-orange-600', dot: 'bg-orange-500' },
    pagerduty: { border: 'border-green-600', header: 'bg-green-700', dot: 'bg-green-500' },
    jenkins: { border: 'border-red-500', header: 'bg-red-600', dot: 'bg-red-400' },
};

const DEFAULT_COLORS = { border: 'border-indigo-400', header: 'bg-indigo-600', dot: 'bg-indigo-400' };

export function ToolNode({ data }: { data: any }) {
    const connectorId = data.connector_id || '';
    const toolName = data.tool_name || 'tool_call';
    const colors = CONNECTOR_COLORS[connectorId] || DEFAULT_COLORS;
    const connectorLabel = data.connector_name || connectorId || 'Integration';

    return (
        <div className={`flex flex-col rounded-lg border-2 ${colors.border} bg-white shadow-md min-w-[210px] overflow-hidden dark:bg-slate-900`}>
            <div className={`flex items-center gap-2 px-3 py-2 ${colors.header} border-b`}>
                <div className="flex h-6 w-6 items-center justify-center rounded bg-white/20">
                    <Hammer className="h-3.5 w-3.5 text-white" />
                </div>
                <div className="flex flex-col min-w-0">
                    <span className="text-xs font-semibold text-white uppercase tracking-wide truncate">{connectorLabel}</span>
                </div>
                <span className="ml-auto text-[9px] bg-white/25 text-white rounded px-1 py-0.5 font-mono tracking-widest">MCP</span>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || toolName}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-mono">{connectorId}:{toolName}</div>
            </div>
            <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-indigo-400" />
            <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-indigo-400" />
        </div>
    );
}

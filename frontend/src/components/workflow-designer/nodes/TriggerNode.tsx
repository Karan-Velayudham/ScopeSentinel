import { Handle, Position } from '@xyflow/react';
import { Play, Zap, Clock, Globe, MessageSquare } from 'lucide-react';

const TRIGGER_STYLES: Record<string, { icon: any; bg: string; text: string; label: string }> = {
    manual: { icon: Play, bg: 'bg-emerald-600', text: 'text-white', label: 'Manual' },
    webhook: { icon: Globe, bg: 'bg-emerald-600', text: 'text-white', label: 'Webhook' },
    cron: { icon: Clock, bg: 'bg-emerald-600', text: 'text-white', label: 'Schedule' },
    event: { icon: Zap, bg: 'bg-emerald-600', text: 'text-white', label: 'Event' },
    message: { icon: MessageSquare, bg: 'bg-emerald-600', text: 'text-white', label: 'Message' },
};

export function TriggerNode({ data }: { data: any }) {
    const triggerType = data.triggerType || 'manual';
    const style = TRIGGER_STYLES[triggerType] || TRIGGER_STYLES.manual;
    const Icon = style.icon;

    return (
        <div className="flex flex-col rounded-lg border-2 border-emerald-400 bg-white shadow-md min-w-[200px] overflow-hidden dark:bg-slate-900 dark:border-emerald-500">
            <div className={`flex items-center gap-2 px-3 py-2 ${style.bg} border-b border-emerald-500`}>
                <div className="flex h-6 w-6 items-center justify-center rounded bg-white/20">
                    <Icon className={`h-3.5 w-3.5 ${style.text}`} />
                </div>
                <span className="text-xs font-semibold text-white uppercase tracking-wide">{style.label}</span>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Trigger'}</div>
                {data.eventType && (
                    <div className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5 font-mono">{data.eventType}</div>
                )}
            </div>
            <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-emerald-400" />
        </div>
    );
}

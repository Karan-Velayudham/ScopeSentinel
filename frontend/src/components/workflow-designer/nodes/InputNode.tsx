import { Handle, Position } from '@xyflow/react';
import { LogIn } from 'lucide-react';

export function InputNode({ data }: { data: any }) {
    const fields: string[] = data.fields || [];
    return (
        <div className="flex flex-col rounded-lg border-2 border-slate-300 bg-white shadow-md min-w-[200px] overflow-hidden dark:bg-slate-900 dark:border-slate-600">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-100 border-b border-slate-200 dark:bg-slate-800 dark:border-slate-600">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-slate-500 text-white">
                    <LogIn className="h-3.5 w-3.5" />
                </div>
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">INPUT</span>
            </div>
            <div className="px-3 py-2">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-100">{data.label || 'Input'}</div>
                {fields.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                        {fields.map((f: string) => (
                            <span key={f} className="text-xs bg-slate-100 text-slate-600 rounded px-1.5 py-0.5 dark:bg-slate-700 dark:text-slate-300">{f}</span>
                        ))}
                    </div>
                )}
            </div>
            <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-slate-400" />
        </div>
    );
}

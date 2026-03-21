import React from 'react';
import { Play, Bot, Hammer, Split, UserCheck, Clock } from 'lucide-react';

interface SidebarProps {
    className?: string;
}

export function Sidebar({ className }: SidebarProps) {
    const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
        event.dataTransfer.setData('application/reactflow', nodeType);
        event.dataTransfer.setData('application/reactflow-label', label);
        event.dataTransfer.effectAllowed = 'move';
    };

    const draggables = [
        { type: 'triggerNode', label: 'Trigger', icon: Play, color: 'text-green-600 bg-green-100 dark:text-green-300 dark:bg-green-900' },
        { type: 'agentNode', label: 'Agent Task', icon: Bot, color: 'text-blue-600 bg-blue-100 dark:text-blue-300 dark:bg-blue-900' },
        { type: 'toolNode', label: 'Tool Call', icon: Hammer, color: 'text-purple-600 bg-purple-100 dark:text-purple-300 dark:bg-purple-900' },
        { type: 'hitlNode', label: 'HITL Gate', icon: UserCheck, color: 'text-orange-700 bg-orange-200 dark:text-orange-300 dark:bg-orange-800' },
        { type: 'conditionNode', label: 'Condition', icon: Split, color: 'text-yellow-600 bg-yellow-100 dark:text-yellow-300 dark:bg-yellow-900' },
    ];

    return (
        <div className={`w-64 border-r bg-card flex flex-col ${className}`}>
            <div className="p-4 border-b font-medium">Node Palette</div>
            <div className="p-4 flex flex-col gap-3">
                <div className="text-xs text-muted-foreground mb-2 uppercase font-semibold tracking-wide">Drag to Canvas</div>

                {draggables.map((item) => {
                    const Icon = item.icon;
                    return (
                        <div
                            key={item.type}
                            className="flex items-center gap-3 p-2 border rounded-md cursor-grab hover:bg-muted/50 transition-colors"
                            onDragStart={(event) => onDragStart(event, item.type, item.label)}
                            draggable
                        >
                            <div className={`flex h-8 w-8 items-center justify-center rounded-md ${item.color}`}>
                                <Icon className="h-4 w-4" />
                            </div>
                            <span className="text-sm font-medium">{item.label}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

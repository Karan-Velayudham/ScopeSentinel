"use client"

import { useEffect, useRef, useState } from "react"

const MOCK_LOGS = [
    "[2026-03-21T10:00:00Z] INFO (orchestrator): Starting run run-123 for ticket SCRUM-8",
    "[2026-03-21T10:00:01Z] DEBUG (mcp): Connecting to GitHub MCP server...",
    "[2026-03-21T10:00:02Z] INFO (mcp): Successfully connected to GitHub",
    "[2026-03-21T10:00:15Z] INFO (agent-planner): Analyzing ticket context and codebase...",
    "[2026-03-21T10:00:40Z] WARN (agent-planner): Re-requesting LLM due to schema validation failure",
    "[2026-03-21T10:01:05Z] INFO (agent-planner): Implementation plan generated successfully",
    "[2026-03-21T10:02:40Z] INFO (hitl): Pinging user for plan approval",
    "[2026-03-21T10:03:50Z] INFO (hitl): Plan approved by user",
    "[2026-03-21T10:03:52Z] INFO (agent-coder): Executing file edits...",
]

export function LiveLogs({ runId: _runId }: { runId: string }) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [logs, setLogs] = useState<string[]>([]);

    useEffect(() => {
        let i = 0;
        const interval = setInterval(() => {
            if (i < MOCK_LOGS.length) {
                setLogs(prev => [...prev, MOCK_LOGS[i]]);
                i++;
            } else {
                clearInterval(interval);
            }
        }, 800);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div
            ref={scrollRef}
            className="absolute inset-0 p-4 overflow-y-auto font-mono text-xs leading-5"
        >
            {logs.map((log, idx) => {
                let colorClass = "text-zinc-300";
                if (log.includes("INFO")) colorClass = "text-blue-400";
                if (log.includes("WARN")) colorClass = "text-yellow-400";
                if (log.includes("ERROR")) colorClass = "text-red-400";
                if (log.includes("DEBUG")) colorClass = "text-zinc-500";

                return (
                    <div key={idx} className={`${colorClass} whitespace-pre-wrap break-all mb-1`}>
                        {log}
                    </div>
                )
            })}
            {logs.length < MOCK_LOGS.length && (
                <div className="flex items-center gap-2 text-zinc-500 mt-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-zinc-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-zinc-500"></span>
                    </span>
                    Waiting for logs...
                </div>
            )}
        </div>
    )
}

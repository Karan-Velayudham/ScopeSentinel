import { useEffect, useRef, useState } from "react"

const API_BASE_WS = process.env.NEXT_PUBLIC_API_URL_WS || 'ws://localhost:8000'

export function LiveLogs({ runId }: { runId: string }) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const ws = new WebSocket(`${API_BASE_WS}/api/runs/${runId}/logs`);

        ws.onopen = () => {
            console.log("WebSocket connected");
            setConnected(true);
        };

        ws.onmessage = (event) => {
            setLogs(prev => [...prev, event.data]);
        };

        ws.onclose = () => {
            console.log("WebSocket disconnected");
            setConnected(false);
        };

        ws.onerror = (error) => {
            console.error("WebSocket error", error);
        };

        return () => {
            ws.close();
        };
    }, [runId]);

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
            {!connected && logs.length === 0 && (
                <div className="flex items-center gap-2 text-zinc-500 mt-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-zinc-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-zinc-500"></span>
                    </span>
                    Connecting to log stream...
                </div>
            )}
            {connected && logs.length === 0 && (
                <div className="text-zinc-500 italic mt-2">
                    Connected. Waiting for logs...
                </div>
            )}
        </div>
    )
}

"use client"

import { useEffect, useState } from "react"
import { AlertCircle, ArrowRight } from "lucide-react"
import Link from "next/link"
import { useApi } from "@/hooks/use-api"

export function HitlBanner() {
    const api = useApi()
    const [pendingRunId, setPendingRunId] = useState<string | null>(null);

    useEffect(() => {
        if (!api.orgId) return

        // Fetch runs with status=WAITING_HITL
        api.get<any>("/api/runs?status=WAITING_HITL&page_size=1")
            .then(data => {
                if (data.items && data.items.length > 0) {
                    setPendingRunId(data.items[0].run_id);
                } else {
                    setPendingRunId(null);
                }
            })
            .catch(err => {
                console.error("Failed to fetch pending HITL runs", err);
            });
    }, [api.orgId]);

    if (!pendingRunId) return null

    return (
        <div className="px-4 py-2 border-b bg-yellow-500/10 dark:bg-yellow-500/20 text-yellow-900 dark:text-yellow-200">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm font-medium">Waiting for your approval on Run {pendingRunId}</span>
                </div>
                <Link href={`/runs/${pendingRunId}`} className="flex items-center text-sm font-medium hover:underline text-yellow-900 dark:text-yellow-200">
                    Review Now <ArrowRight className="ml-1 h-3 w-3" />
                </Link>
            </div>
        </div>
    )
}

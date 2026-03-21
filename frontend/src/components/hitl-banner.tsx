import { AlertCircle, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export function HitlBanner() {
    // In a real app, this would poll or use a WebSocket to check for pending HITL tasks.
    const hasPendingApproval = true
    const pendingRunId = "run-126"

    if (!hasPendingApproval) return null

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

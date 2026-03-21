"use client"

import { CheckCircle2, Circle, Clock, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useState } from "react"
import { StepDrawer } from "./step-drawer"

const MOCK_STEPS = [
    { id: "step-1", name: "Fetch Ticket Details", status: "DONE", duration: "1.2s", time: "10:00:01" },
    { id: "step-2", name: "Analyze Codebase", status: "DONE", duration: "14s", time: "10:00:15" },
    { id: "step-3", name: "Generate Implementation Plan", status: "DONE", duration: "25s", time: "10:00:40" },
    { id: "step-4", name: "Awaiting HITL Approval", status: "DONE", duration: "2m", time: "10:02:40" },
    { id: "step-5", name: "Execute Code Changes", status: "RUNNING", duration: "1m 12s", time: "10:03:52" },
    { id: "step-6", name: "Run Tests", status: "PENDING", duration: "-", time: "-" },
]

export function RunTimeline({ runId }: { runId: string }) {
    const [selectedStep, setSelectedStep] = useState<string | null>(null);

    const StatusIcon = ({ status }: { status: string }) => {
        switch (status) {
            case "DONE": return <CheckCircle2 className="h-5 w-5 text-green-500" />
            case "FAILED": return <XCircle className="h-5 w-5 text-red-500" />
            case "RUNNING": return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
            default: return <Circle className="h-5 w-5 text-muted-foreground" />
        }
    }

    return (
        <>
            <div className="relative border-l ml-3 border-muted-foreground/30 space-y-6 pb-4">
                {MOCK_STEPS.map((step, idx) => (
                    <div key={step.id}
                        className="relative pl-6 cursor-pointer group"
                        onClick={() => setSelectedStep(step.id)}>
                        <div className="absolute -left-2.5 bg-background">
                            <StatusIcon status={step.status} />
                        </div>
                        <div className={cn(
                            "flex flex-col gap-1 p-3 rounded-md transition-colors border",
                            step.status === "PENDING" ? "opacity-60" : "hover:bg-muted/50",
                            selectedStep === step.id ? "bg-muted border-border" : "border-transparent"
                        )}>
                            <div className="flex items-center justify-between">
                                <span className="font-medium text-sm">{step.name}</span>
                                <span className="text-xs text-muted-foreground">{step.time}</span>
                            </div>
                            <div className="text-xs text-muted-foreground">
                                Duration: {step.duration}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <StepDrawer
                stepId={selectedStep}
                open={!!selectedStep}
                onOpenChange={(val) => !val && setSelectedStep(null)}
            />
        </>
    )
}

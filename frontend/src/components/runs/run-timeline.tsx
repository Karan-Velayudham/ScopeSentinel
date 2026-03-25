import { useEffect, useState } from "react"
import { CheckCircle2, Circle, Clock, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/use-api"
import { StepDrawer } from "./step-drawer"

export function RunTimeline({ runId }: { runId: string }) {
    const api = useApi()
    const [steps, setSteps] = useState<any[]>([]);
    const [selectedStep, setSelectedStep] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchSteps = async () => {
        if (!api.orgId) return

        try {
            const data = await api.get<any>(`/api/runs/${runId}`);
            setSteps(data.steps || []);
        } catch (e) {
            console.error("Failed to fetch run steps", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSteps();
        const interval = setInterval(fetchSteps, 5000);
        return () => clearInterval(interval);
    }, [runId, api.orgId, api]);

    const StatusIcon = ({ status }: { status: string }) => {
        switch (status) {
            case "SUCCEEDED": return <CheckCircle2 className="h-5 w-5 text-green-500" />
            case "FAILED": return <XCircle className="h-5 w-5 text-red-500" />
            case "RUNNING": return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />
            default: return <Circle className="h-5 w-5 text-muted-foreground" />
        }
    }

    const formatTime = (dateStr?: string) => {
        if (!dateStr) return "-";
        return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    if (loading && steps.length === 0) return <div className="p-4 text-sm text-muted-foreground">Loading timeline...</div>

    return (
        <>
            <div className="relative border-l ml-3 border-muted-foreground/30 space-y-6 pb-4">
                {steps.map((step) => (
                    <div key={step.step_id}
                        className="relative pl-6 cursor-pointer group"
                        onClick={() => setSelectedStep(step.step_id)}>
                        <div className="absolute -left-2.5 bg-background">
                            <StatusIcon status={step.status} />
                        </div>
                        <div className={cn(
                            "flex flex-col gap-1 p-3 rounded-md transition-colors border",
                            step.status === "PENDING" ? "opacity-60" : "hover:bg-muted/50",
                            selectedStep === step.step_id ? "bg-muted border-border" : "border-transparent"
                        )}>
                            <div className="flex items-center justify-between">
                                <span className="font-medium text-sm">{step.step_name}</span>
                                <div className="flex items-center gap-2">
                                    {step.total_tokens > 0 && (
                                        <span className="text-[10px] text-blue-500 font-medium bg-blue-50 dark:bg-blue-900/20 px-1.5 py-0.5 rounded border border-blue-100 dark:border-blue-800">
                                            {step.total_tokens} tokens
                                        </span>
                                    )}
                                    <span className="text-xs text-muted-foreground">{formatTime(step.started_at)}</span>
                                </div>
                            </div>
                            {step.error_message && (
                                <div className="text-xs text-red-500 mt-1 line-clamp-1">
                                    {step.error_message}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {steps.length === 0 && (
                    <div className="pl-6 text-sm text-muted-foreground">No steps recorded yet.</div>
                )}
            </div>

            <StepDrawer
                step={steps.find(s => s.step_id === selectedStep)}
                open={!!selectedStep}
                onOpenChange={(val: boolean) => !val && setSelectedStep(null)}
            />
        </>
    )
}

"use client";

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { RunTimeline } from "@/components/runs/run-timeline"
import { LiveLogs } from "@/components/runs/live-logs"
import { PlanReviewPanel } from "@/components/hitl/plan-review"
import { DiffViewer } from "@/components/hitl/diff-viewer"
import { ExecutionReplay } from "@/components/runs/execution-replay"
import { ArrowLeft, Play, RefreshCw, SquareTerminal, Info, Activity } from "lucide-react"
import Link from "next/link"
import { apiGet } from "@/lib/api-client"

export default function RunDetailPage() {
    const params = useParams()
    const runId = params.id as string

    const [run, setRun] = useState<any>(null)
    const [workflow, setWorkflow] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchData = async () => {
        try {
            const data = await apiGet<any>(`/api/runs/${runId}`)
            setRun(data)

            if (data.workflow_id && !workflow) {
                const wfData = await apiGet<any>(`/api/workflows/${data.workflow_id}`)
                setWorkflow(wfData)
            }
        } catch (e: any) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 5000)
        return () => clearInterval(interval)
    }, [runId])

    if (loading && !run) return <div className="p-8">Loading run details...</div>
    if (error) return <div className="p-8 text-destructive">Error: {error}</div>
    if (!run) return <div className="p-8">Run not found.</div>

    const isWaitingHitl = run.status === "WAITING_HITL"

    return (
        <div className="flex flex-col gap-6 h-[calc(100vh-8rem)]">
            <div className="flex items-center justify-between shrink-0">
                <div className="flex items-center gap-4">
                    <Link href="/runs">
                        <Button variant="ghost" size="icon">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Run {runId.slice(0, 8)}</h1>
                        <p className="text-muted-foreground text-sm">
                            Ticket: {run.ticket_id} • Started {new Date(run.created_at).toLocaleString()}
                        </p>
                    </div>
                    <Badge variant={isWaitingHitl ? "destructive" : "default"} className="ml-2">
                        {run.status}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={fetchData}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh
                    </Button>
                </div>
            </div>

            <Tabs defaultValue="replay" className="flex-1 flex flex-col overflow-hidden">
                <TabsList className="w-fit">
                    <TabsTrigger value="replay">
                        <Activity className="h-4 w-4 mr-2" />
                        Execution Replay
                    </TabsTrigger>
                    <TabsTrigger value="timeline">
                        <Info className="h-4 w-4 mr-2" />
                        Timeline & Logs
                    </TabsTrigger>
                    {isWaitingHitl && (
                        <TabsTrigger value="hitl" className="text-destructive font-bold">
                            HITL Review Required
                        </TabsTrigger>
                    )}
                </TabsList>

                <TabsContent value="replay" className="flex-1 mt-4 overflow-hidden">
                    <Card className="h-full flex flex-col">
                        <CardHeader className="pb-3 px-6 pt-6">
                            <CardTitle>Workflow Execution Canvas</CardTitle>
                            <CardDescription>Live playback of agent steps and tool calls.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 overflow-hidden">
                            {workflow ? (
                                <ExecutionReplay yamlContent={workflow.yaml_content} steps={run.steps} />
                            ) : (
                                <div className="h-full flex items-center justify-center text-muted-foreground">
                                    {run.workflow_id ? "Loading workflow graph..." : "No workflow associated with this run."}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="timeline" className="flex-1 mt-4 overflow-hidden">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
                        <div className="lg:col-span-1 overflow-y-auto">
                            <Card className="h-full flex flex-col shadow-sm">
                                <CardHeader className="pb-3">
                                    <CardTitle>Timeline</CardTitle>
                                    <CardDescription>Execution sequence.</CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 overflow-y-auto">
                                    <RunTimeline runId={runId} />
                                </CardContent>
                            </Card>
                        </div>
                        <div className="lg:col-span-2 overflow-y-auto">
                            <Card className="h-full flex flex-col border-zinc-800 bg-zinc-950 text-zinc-50 shadow-xl overflow-hidden">
                                <CardHeader className="border-b border-zinc-800 bg-zinc-900 pb-3 p-4 flex flex-row items-center gap-2 shrink-0">
                                    <SquareTerminal className="h-5 w-5 text-zinc-400" />
                                    <CardTitle className="text-sm font-medium">Live Output</CardTitle>
                                </CardHeader>
                                <CardContent className="flex-1 p-0 overflow-hidden relative">
                                    <LiveLogs runId={runId} />
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>

                {isWaitingHitl && (
                    <TabsContent value="hitl" className="flex-1 mt-4 overflow-y-auto">
                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                            <PlanReviewPanel runId={runId} />
                            <Card>
                                <CardHeader>
                                    <CardTitle>Proposed Changes</CardTitle>
                                    <CardDescription>Review the generated plan and diff before continuing.</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    {/* In a real implementation, we'd fetch the actual diff */}
                                    <p className="text-sm text-muted-foreground mb-4">View plan details on the left to see reasoning.</p>
                                    <DiffViewer code="// No diff available yet" language="diff" />
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>
                )}
            </Tabs>
        </div>
    )
}

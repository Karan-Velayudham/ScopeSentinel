import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RunTimeline } from "@/components/runs/run-timeline"
import { LiveLogs } from "@/components/runs/live-logs"
import { ArrowLeft, Play, RefreshCw, SquareTerminal } from "lucide-react"
import Link from "next/link"

export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const resolvedParams = await params;
    const runId = resolvedParams.id;

    return (
        <div className="flex flex-col gap-6 h-[calc(100vh-8rem)]">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" asChild>
                        <Link href="/runs"><ArrowLeft className="h-4 w-4" /></Link>
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">Run {runId}</h1>
                        <p className="text-muted-foreground text-sm">Ticket: SCRUM-8 • Started at 2026-03-21T10:00:00Z</p>
                    </div>
                    <Badge variant="default" className="ml-2">SUCCEEDED</Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh
                    </Button>
                    <Button size="sm">
                        <Play className="mr-2 h-4 w-4" />
                        Replay Run
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
                <div className="lg:col-span-1 overflow-y-auto pr-2">
                    <Card className="h-full flex flex-col">
                        <CardHeader className="pb-3">
                            <CardTitle>Timeline</CardTitle>
                            <CardDescription>Execution steps and state.</CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1 overflow-y-auto">
                            <RunTimeline runId={runId} />
                        </CardContent>
                    </Card>
                </div>

                <div className="lg:col-span-2 overflow-y-auto">
                    <Card className="h-full flex flex-col border-zinc-800 bg-zinc-950 text-zinc-50">
                        <CardHeader className="border-b border-zinc-800 bg-zinc-900 pb-3 p-4 flex flex-row items-center gap-2">
                            <SquareTerminal className="h-5 w-5 text-zinc-400" />
                            <CardTitle className="text-sm font-medium">Live Logs</CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 p-0 overflow-hidden relative">
                            <LiveLogs runId={runId} />
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}

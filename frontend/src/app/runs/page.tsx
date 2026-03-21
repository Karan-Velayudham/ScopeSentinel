import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { Button } from "@/components/ui/button"

const MOCK_RUNS = [
    { id: "run-123", ticket: "SCRUM-8", status: "SUCCEEDED", startedAt: "2026-03-21T10:00:00Z", duration: "45s" },
    { id: "run-124", ticket: "SCRUM-9", status: "FAILED", startedAt: "2026-03-21T10:05:00Z", duration: "12s" },
    { id: "run-125", ticket: "SCRUM-10", status: "RUNNING", startedAt: "2026-03-21T10:45:00Z", duration: "-" },
    { id: "run-126", ticket: "SCRUM-11", status: "WAITING_HITL", startedAt: "2026-03-21T10:40:00Z", duration: "5m" },
]

export default function RunsPage() {
    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Runs</h1>
                <Button>Trigger New Run</Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Workflow Executions</CardTitle>
                    <CardDescription>View and manage recent workflow runs.</CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Run ID</TableHead>
                                <TableHead>Ticket</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Started At</TableHead>
                                <TableHead>Duration</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {MOCK_RUNS.map((run) => (
                                <TableRow key={run.id}>
                                    <TableCell className="font-medium">
                                        <Link href={`/runs/${run.id}`} className="hover:underline text-blue-600 dark:text-blue-400">
                                            {run.id}
                                        </Link>
                                    </TableCell>
                                    <TableCell>{run.ticket}</TableCell>
                                    <TableCell>
                                        <Badge variant={
                                            run.status === "SUCCEEDED" ? "default" :
                                                run.status === "FAILED" ? "destructive" :
                                                    run.status === "WAITING_HITL" ? "outline" : "secondary"
                                        }>
                                            {run.status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>{new Date(run.startedAt).toLocaleString()}</TableCell>
                                    <TableCell>{run.duration}</TableCell>
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="sm" asChild>
                                            <Link href={`/runs/${run.id}`}>View</Link>
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}

"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiGet, apiPost } from '@/lib/api-client';
import { useSession } from 'next-auth/react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { RefreshCw, Info } from 'lucide-react';

const statusColor = (status: string) => {
    if (status === "SUCCEEDED") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
    if (status === "FAILED") return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
    if (status === "RUNNING") return "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300";
    if (status === "WAITING_HITL") return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
    return "bg-muted text-muted-foreground";
};

export default function RunsPage() {
    const { data: session } = useSession();
    const [runs, setRuns] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [triggerOpen, setTriggerOpen] = useState(false);
    const [ticketId, setTicketId] = useState("");
    const [triggering, setTriggering] = useState(false);

    const hasPendingVisualRuns = runs.some(r => r.status === 'PENDING' && r.workflow_id && !r.ticket_id);

    const fetchRuns = async () => {
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        setLoading(true);
        try {
            const data = await apiGet<{ items: any[] }>('/api/runs/', {
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            });
            setRuns(data.items || []);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (session?.user?.org_id) {
            fetchRuns();
            const interval = setInterval(fetchRuns, 10000);
            return () => clearInterval(interval);
        }
    }, [session]);

    const handleTrigger = async () => {
        const orgId = session?.user?.org_id;
        if (!ticketId.trim() || !orgId) return;
        setTriggering(true);
        try {
            await apiPost('/api/runs/', { ticket_id: ticketId.trim(), dry_run: false }, {
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            });
            setTriggerOpen(false);
            setTicketId("");
            await fetchRuns();
        } catch (e: any) {
            alert(`Failed to trigger run: ${e.message}`);
        } finally {
            setTriggering(false);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">Runs</h1>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={fetchRuns}>
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Refresh
                    </Button>
                    <Dialog open={triggerOpen} onOpenChange={setTriggerOpen}>
                        <DialogTrigger render={<Button>Trigger New Run</Button>} />
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Trigger a New Workflow Run</DialogTitle>
                                <DialogDescription>
                                    Enter a Jira ticket ID to start the agent pipeline.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="py-4 space-y-3">
                                <Label htmlFor="ticket-id">Ticket ID</Label>
                                <Input
                                    id="ticket-id"
                                    placeholder="e.g. SCRUM-8"
                                    value={ticketId}
                                    onChange={e => setTicketId(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleTrigger()}
                                />
                                <p className="text-xs text-muted-foreground">
                                    To trigger a visual workflow, use the <strong>Run</strong> button in the Workflow Designer instead.
                                </p>
                            </div>
                            <DialogFooter>
                                <Button variant="outline" onClick={() => setTriggerOpen(false)}>Cancel</Button>
                                <Button onClick={handleTrigger} disabled={!ticketId.trim() || triggering}>
                                    {triggering ? "Starting..." : "Start Run"}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {/* Info banner for pending visual workflow runs */}
            {hasPendingVisualRuns && (
                <div className="flex items-start gap-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 text-sm text-blue-800 dark:text-blue-200">
                    <Info className="h-4 w-4 mt-0.5 shrink-0" />
                    <div>
                        <p className="font-medium">Visual workflow execution is coming soon</p>
                        <p className="mt-0.5 text-blue-700 dark:text-blue-300">
                            Runs triggered from the visual designer stay in <strong>PENDING</strong> until the execution engine is released. Your workflow definition and inputs have been saved and will run automatically when it is enabled.
                        </p>
                    </div>
                </div>
            )}

            {error && (
                <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                    Error loading runs: {error}
                </div>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Workflow Executions</CardTitle>
                    <CardDescription>
                        {loading ? "Loading..." : `${runs.length} run(s) found. Auto-refreshes every 10s.`}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">Loading runs...</div>
                    ) : runs.length === 0 ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">
                            No runs found. Trigger one above or use the Run button in the Workflow Designer.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Run ID</TableHead>
                                    <TableHead>Source</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Dry Run</TableHead>
                                    <TableHead>Started At</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {runs.map((run) => (
                                    <TableRow key={run.run_id}>
                                        <TableCell className="font-mono text-xs">
                                            <Link href={`/runs/${run.run_id}`} className="hover:underline text-blue-600 dark:text-blue-400">
                                                {run.run_id.slice(0, 8)}...
                                            </Link>
                                        </TableCell>
                                        <TableCell className="font-medium text-sm">
                                            {run.ticket_id ? (
                                                <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{run.ticket_id}</span>
                                            ) : run.workflow_id ? (
                                                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                    <span className="h-1.5 w-1.5 rounded-full bg-violet-500 shrink-0 inline-block" />
                                                    Visual Workflow
                                                    <span className="font-mono text-[10px] opacity-60">{run.workflow_id.slice(0, 8)}</span>
                                                </span>
                                            ) : (
                                                <span className="text-muted-foreground">—</span>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`text-[11px] font-semibold rounded-full px-2 py-0.5 ${statusColor(run.status)}`}>
                                                {run.status}
                                            </span>
                                        </TableCell>
                                        <TableCell>{run.dry_run ? "Yes" : "No"}</TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {new Date(run.created_at).toLocaleString()}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button variant="ghost" size="sm">
                                                <Link href={`/runs/${run.run_id}`}>View</Link>
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

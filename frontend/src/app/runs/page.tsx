"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiGet, apiPost } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
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
import { RefreshCw } from 'lucide-react';

const statusVariant = (status: string) => {
    if (status === "SUCCEEDED") return "default";
    if (status === "FAILED") return "destructive";
    if (status === "WAITING_HITL") return "outline";
    return "secondary";
};

export default function RunsPage() {
    const [runs, setRuns] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [triggerOpen, setTriggerOpen] = useState(false);
    const [ticketId, setTicketId] = useState("");
    const [triggering, setTriggering] = useState(false);

    const fetchRuns = async () => {
        setLoading(true);
        try {
            const data = await apiGet<{ items: any[] }>('/api/runs/');
            setRuns(data.items || []);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRuns();
        // Poll every 10 seconds to reflect live run status updates
        const interval = setInterval(fetchRuns, 10000);
        return () => clearInterval(interval);
    }, []);

    const handleTrigger = async () => {
        if (!ticketId.trim()) return;
        setTriggering(true);
        try {
            await apiPost('/api/runs/', { ticket_id: ticketId.trim(), dry_run: false });
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
                        <DialogTrigger>
                            <Button>Trigger New Run</Button>
                        </DialogTrigger>
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
                            No runs found. Trigger one above to get started.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Run ID</TableHead>
                                    <TableHead>Ticket</TableHead>
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
                                        <TableCell className="font-medium">{run.ticket_id}</TableCell>
                                        <TableCell>
                                            <Badge variant={statusVariant(run.status)}>
                                                {run.status}
                                            </Badge>
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

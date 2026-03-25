"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";
import { useSession } from "next-auth/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RefreshCw, Search, Filter } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AuditEvent {
    id: string;
    org_id: string;
    user_id: string | null;
    action: string;
    resource_type: string | null;
    resource_id: string | null;
    payload: any;
    occurred_at: string;
}

export default function AuditLogPage() {
    const { data: session } = useSession();
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState("");

    const fetchAuditEvents = async () => {
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        setLoading(true);
        try {
            const data = await apiGet<AuditEvent[]>("/audit/events?limit=100", {
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            });
            setEvents(data || []);
            setError(null);
        } catch (e: any) {
            setError(e.message || "Failed to load audit events");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (session?.user?.org_id) {
            fetchAuditEvents();
        }
    }, [session]);

    const filteredEvents = events.filter(e =>
        (e.action && e.action.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (e.user_id && e.user_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (e.resource_type && e.resource_type.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    const getActionColor = (action: string) => {
        if (action.startsWith("post:")) return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
        if (action.startsWith("patch:") || action.startsWith("put:")) return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300";
        if (action.startsWith("delete:")) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
        return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300";
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
                    <p className="text-muted-foreground mt-1">Immutable record of all mutating actions in your organization.</p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchAuditEvents}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh Log
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Security Events</CardTitle>
                    <CardDescription>
                        Review recent actions performed by users and API keys.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="search"
                                placeholder="Search actions, users..."
                                className="pl-9"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                        <Button variant="outline" size="icon">
                            <Filter className="h-4 w-4" />
                        </Button>
                    </div>

                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Timestamp</TableHead>
                                    <TableHead>Action</TableHead>
                                    <TableHead>Resource Type</TableHead>
                                    <TableHead>User / Actor</TableHead>
                                    <TableHead>Details</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {loading ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                                            Loading audit trail...
                                        </TableCell>
                                    </TableRow>
                                ) : error ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="h-32 text-center text-destructive">
                                            {error}
                                        </TableCell>
                                    </TableRow>
                                ) : filteredEvents.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="h-32 text-center text-muted-foreground">
                                            No audit events found. Make sure the audit microservice is running.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredEvents.map((event) => (
                                        <TableRow key={event.id}>
                                            <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                                                {new Date(event.occurred_at).toLocaleString()}
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className={`font-mono text-xs ${getActionColor(event.action)} border-none`}>
                                                    {event.action.toUpperCase()}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="capitalize">
                                                {event.resource_type || <span className="text-muted-foreground">—</span>}
                                            </TableCell>
                                            <TableCell>
                                                <div className="font-mono text-xs truncate max-w-[150px]" title={event.user_id || "System"}>
                                                    {event.user_id || "System"}
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="text-xs font-mono text-muted-foreground bg-muted/50 p-1.5 rounded line-clamp-2 max-w-sm break-all">
                                                    {JSON.stringify(event.payload)}
                                                </div>
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

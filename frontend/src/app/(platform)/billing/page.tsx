"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";
import { useSession } from "next-auth/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { RefreshCw, Zap, Box, BrainCircuit, CreditCard, Activity } from "lucide-react";

interface UsageBreakdown {
    event_type: string;
    count: number;
    total_tokens: number;
}

interface UsageData {
    org_id: string;
    period: string; // YYYY-MM
    breakdown: UsageBreakdown[];
    quota: {
        runs_this_month: number;
        limit: number;
    };
}

export default function BillingPage() {
    const { data: session } = useSession();
    const [usage, setUsage] = useState<UsageData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchUsage = async () => {
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        setLoading(true);
        try {
            const data = await apiGet<UsageData>(`/metering/usage?org_id=${orgId}`, {
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            });
            setUsage(data);
            setError(null);
        } catch (e: any) {
            setError(e.message || "Failed to load usage metrics");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (session?.user?.org_id) {
            fetchUsage();
        }
    }, [session]);

    const getBreakdownStat = (type: string, field: "count" | "total_tokens") => {
        if (!usage) return 0;
        const b = usage.breakdown.find((x) => x.event_type === type);
        return b ? b[field] : 0;
    };

    const runCount = usage?.quota?.runs_this_month || 0;
    const runLimit = usage?.quota?.limit || 1000;
    const runPercentage = Math.min((runCount / runLimit) * 100, 100);

    const formatNumber = (num: number) => new Intl.NumberFormat().format(num);

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Billing & Usage</h1>
                    <p className="text-muted-foreground mt-1">
                        Monitor your platform usage and quota limits for {usage ? new Date(usage.period + "-01").toLocaleString('default', { month: 'long', year: 'numeric' }) : "the current period"}.
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchUsage}>
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            {error && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm p-4 rounded-md">
                    {error}
                </div>
            )}

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {/* Workflow Runs Quota Card */}
                <Card className="col-span-full md:col-span-2 lg:col-span-3">
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2">
                            <Activity className="h-5 w-5 text-indigo-500" />
                            Workflow Runs Quota
                        </CardTitle>
                        <CardDescription>Executions consumed this billing cycle</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline gap-2 mb-2">
                            <span className="text-3xl font-bold">{formatNumber(runCount)}</span>
                            <span className="text-muted-foreground">/ {formatNumber(runLimit)} runs</span>
                        </div>
                        <Progress value={runPercentage} className={`h-3 ${runPercentage > 90 ? 'text-red-500' : 'text-indigo-500'}`} />
                        <p className="text-xs text-muted-foreground mt-3">
                            {runPercentage >= 100 ? "Limit reached. Further runs will be blocked until the next billing cycle." : `${formatNumber(runLimit - runCount)} runs remaining this month.`}
                        </p>
                    </CardContent>
                </Card>

                {/* Tokens Card */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">LLM Tokens Processed</CardTitle>
                        <BrainCircuit className="h-4 w-4 text-violet-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {formatNumber(getBreakdownStat("llm_call", "total_tokens"))}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Across {formatNumber(getBreakdownStat("llm_call", "count"))} model inferences
                        </p>
                    </CardContent>
                </Card>

                {/* Steps Card */}
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Steps Executed</CardTitle>
                        <Box className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {formatNumber(getBreakdownStat("step", "count"))}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Individual agent or tool actions
                        </p>
                    </CardContent>
                </Card>

                {/* Plan Card */}
                <Card className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900/50 dark:to-slate-900">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Current Plan</CardTitle>
                        <Zap className="h-4 w-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">Enterprise Beta</div>
                        <p className="text-xs text-muted-foreground mt-1">
                            Usage is actively metered but currently free of charge.
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card className="border-dashed bg-transparent shadow-none">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <CreditCard className="h-5 w-5 text-muted-foreground" />
                        Billing Details (Coming Soon)
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground">
                        Stripe integration for managing subscription plans, payment methods, and invoices is scheduled for a future release (Epic 5.4.5).
                    </p>
                </CardContent>
                <CardFooter>
                    <Button variant="outline" disabled>Manage Payment Methods</Button>
                </CardFooter>
            </Card>
        </div>
    );
}

"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, Workflow, CheckCircle, Clock } from "lucide-react"
import { useApi } from "@/hooks/use-api"

export default function Home() {
  const api = useApi();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.orgId) return;

    api.get<any>("/api/runs/stats")
      .then((data: any) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err: any) => {
        console.error("Failed to fetch dashboard stats", err);
        setLoading(false);
      });
  }, [api.orgId]);

  if (loading) return <div className="p-8 text-muted-foreground italic">Loading dashboard...</div>

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Runs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_runs ?? 0}</div>
            <p className="text-xs text-muted-foreground">Currently executing</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workflows Executed</CardTitle>
            <Workflow className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.workflows_executed ?? 0}</div>
            <p className="text-xs text-muted-foreground">Total history</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending HITL Approvals</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.pending_hitl ?? 0}</div>
            <p className="text-xs text-muted-foreground">Needs your attention</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.success_rate ?? 100}%</div>
            <p className="text-xs text-muted-foreground">Completed runs</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7 mt-4">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Overview of recent workflow executions.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center border-t text-muted-foreground text-sm italic">
            Activity Chart (Future Integration)
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Needs Approval</CardTitle>
            <CardDescription>HITL events waiting for review.</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center border-t text-muted-foreground text-sm italic">
            Pending Tasks (Future Integration)
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

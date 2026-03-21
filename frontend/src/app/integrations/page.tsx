"use client"

import { useState } from "react"
import { Database, Github, Key, Link as LinkIcon, MonitorCircle, RefreshCw, Slack } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const MOCK_INTEGRATIONS = [
    {
        id: "github",
        name: "GitHub",
        description: "Connect to GitHub repositories for PRs and issues.",
        icon: Github,
        type: "oauth",
        status: "connected",
        lastSync: "10 mins ago",
        health: "healthy",
    },
    {
        id: "jira",
        name: "Jira",
        description: "Sync with Jira issues, epics, and sprints.",
        icon: Database,
        type: "oauth",
        status: "disconnected",
        lastSync: null,
        health: null,
    },
    {
        id: "slack",
        name: "Slack",
        description: "Send notifications to Slack channels.",
        icon: Slack,
        type: "oauth",
        status: "connected",
        lastSync: "1 hour ago",
        health: "error",
    },
    {
        id: "openai",
        name: "OpenAI API",
        description: "Connect to OpenAI models directly using an API key.",
        icon: MonitorCircle,
        type: "apikey",
        status: "disconnected",
        lastSync: null,
        health: null,
    }
]

export default function IntegrationsPage() {
    const [integrations, setIntegrations] = useState(MOCK_INTEGRATIONS)
    const [activeApiKeyDialog, setActiveApiKeyDialog] = useState<string | null>(null)
    const [apiKey, setApiKey] = useState("")

    const handleConnectOauth = (id: string) => {
        // Mock OAuth redirect
        setIntegrations(prev => prev.map(int => int.id === id ? { ...int, status: "connected", health: "healthy", lastSync: "just now" } : int))
    }

    const handleConnectApiKey = (id: string) => {
        // Mock API key save
        setIntegrations(prev => prev.map(int => int.id === id ? { ...int, status: "connected", health: "healthy", lastSync: "just now" } : int))
        setActiveApiKeyDialog(null)
        setApiKey("")
    }

    const handleDisconnect = (id: string) => {
        setIntegrations(prev => prev.map(int => int.id === id ? { ...int, status: "disconnected", health: null, lastSync: null } : int))
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
                    <p className="text-muted-foreground mt-1">Manage connected applications, API keys, and workflow tools.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {integrations.map((integration) => {
                    const isConnected = integration.status === "connected"
                    const isHealthy = integration.health === "healthy"

                    return (
                        <Card key={integration.id} className="flex flex-col">
                            <CardHeader className="pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 border rounded-md">
                                        <integration.icon className="h-6 w-6" />
                                    </div>
                                    {isConnected && (
                                        <Badge variant={isHealthy ? "default" : "destructive"} className={isHealthy ? "bg-green-500/10 text-green-600 hover:bg-green-500/20 dark:text-green-400" : ""}>
                                            {isHealthy ? "Healthy" : "Error"}
                                        </Badge>
                                    )}
                                </div>
                                <CardTitle className="mt-4">{integration.name}</CardTitle>
                                <CardDescription className="line-clamp-2 min-h-[40px]">{integration.description}</CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                {isConnected ? (
                                    <div className="flex flex-col gap-2 text-sm text-muted-foreground">
                                        <div className="flex items-center gap-2">
                                            <RefreshCw className="h-3.5 w-3.5" />
                                            <span>Last synced: {integration.lastSync}</span>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-sm text-muted-foreground flex items-center gap-1">
                                        {integration.type === "oauth" ? <LinkIcon className="h-3.5 w-3.5" /> : <Key className="h-3.5 w-3.5" />}
                                        <span>{integration.type === "oauth" ? "OAuth Connection" : "API Key Required"}</span>
                                    </div>
                                )}
                            </CardContent>
                            <CardFooter className="pt-4 border-t gap-2">
                                {isConnected ? (
                                    <>
                                        <Button variant="outline" className="w-full">Configure</Button>
                                        <Button variant="ghost" className="text-destructive hover:text-destructive hover:bg-destructive/10 px-3" onClick={() => handleDisconnect(integration.id)}>
                                            Disconnect
                                        </Button>
                                    </>
                                ) : (
                                    integration.type === "oauth" ? (
                                        <Button className="w-full" onClick={() => handleConnectOauth(integration.id)}>
                                            Connect
                                        </Button>
                                    ) : (
                                        <Dialog open={activeApiKeyDialog === integration.id} onOpenChange={(open) => setActiveApiKeyDialog(open ? integration.id : null)}>
                                            <DialogTrigger asChild>
                                                <Button className="w-full">Provide API Key</Button>
                                            </DialogTrigger>
                                            <DialogContent>
                                                <DialogHeader>
                                                    <DialogTitle>Connect {integration.name}</DialogTitle>
                                                    <DialogDescription>
                                                        Enter your API key or Personal Access Token to connect this integration.
                                                    </DialogDescription>
                                                </DialogHeader>
                                                <div className="py-4 space-y-4">
                                                    <div className="space-y-2">
                                                        <Label htmlFor="api-key">API Key</Label>
                                                        <Input
                                                            id="api-key"
                                                            type="password"
                                                            placeholder="sk-..."
                                                            value={apiKey}
                                                            onChange={(e) => setApiKey(e.target.value)}
                                                        />
                                                    </div>
                                                </div>
                                                <DialogFooter>
                                                    <Button variant="outline" onClick={() => setActiveApiKeyDialog(null)}>Cancel</Button>
                                                    <Button onClick={() => handleConnectApiKey(integration.id)} disabled={!apiKey}>Save Connection</Button>
                                                </DialogFooter>
                                            </DialogContent>
                                        </Dialog>
                                    )
                                )}
                            </CardFooter>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}

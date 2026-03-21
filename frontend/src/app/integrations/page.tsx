"use client"

import { useState, useEffect } from "react"
import { Database, Github, Key, Link as LinkIcon, Monitor, Slack } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { apiFetch } from "@/lib/api-client"

const getIconForCategory = (category: string) => {
    switch (category) {
        case "VCS": return Github;
        case "Chat": return Slack;
        case "Observability": return Monitor;
        case "Issue Tracking": return Database;
        default: return LinkIcon;
    }
}

export default function IntegrationsPage() {
    const [available, setAvailable] = useState<any[]>([])
    const [installed, setInstalled] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const fetchData = async () => {
        try {
            const [resAvail, resInst] = await Promise.all([
                apiFetch('/api/connectors/available'),
                apiFetch('/api/connectors/installed'),
            ])
            setAvailable(await resAvail.json())
            setInstalled(await resInst.json())
        } catch (e) {
            console.error("Failed to fetch connectors", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { fetchData() }, [])

    const handleConnect = async (connectorId: string) => {
        try {
            const res = await apiFetch(`/api/connectors/${connectorId}/install`, {
                method: 'POST',
                body: JSON.stringify({ config: { token: "mock_token" } }),
            })
            if (res.ok) {
                fetchData()
            } else {
                const err = await res.json()
                alert(err.detail || "Failed to install connector.")
            }
        } catch (e) {
            alert("Error installing connector")
        }
    }

    // m-3 fix: Add disconnect/uninstall handler
    const handleDisconnect = async (connectorId: string) => {
        if (!confirm(`Remove ${connectorId} connector?`)) return
        try {
            const res = await apiFetch(`/api/connectors/${connectorId}/uninstall`, { method: 'DELETE' })
            if (res.ok || res.status === 204) {
                fetchData()
            } else {
                alert("Failed to uninstall connector.")
            }
        } catch (e) {
            alert("Error removing connector")
        }
    }

    if (loading) return <div className="p-8">Loading Marketplace...</div>

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between border-b pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">App Marketplace</h1>
                    <p className="text-muted-foreground mt-1">
                        Discover and install connectors to use tools inside your Agentic Workflows.
                    </p>
                </div>
                <Badge variant="secondary">{available.length} connectors available</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {available.map((connector) => {
                    const instEntry = installed.find((i: any) => i.connector_id === connector.id)
                    const isConnected = !!instEntry
                    const Icon = getIconForCategory(connector.category)

                    return (
                        <Card key={connector.id} className="flex flex-col shadow-sm">
                            <CardHeader className="pb-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 border rounded-md">
                                        <Icon className="h-6 w-6" />
                                    </div>
                                    {isConnected && (
                                        <Badge variant="default" className="bg-green-500/10 text-green-600 dark:text-green-400">
                                            Installed
                                        </Badge>
                                    )}
                                </div>
                                <CardTitle className="mt-4">{connector.name}</CardTitle>
                                <CardDescription className="line-clamp-2 min-h-[40px]">{connector.description}</CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <Badge variant="secondary">{connector.category}</Badge>
                            </CardContent>
                            <CardFooter className="pt-4 border-t flex gap-2">
                                {isConnected ? (
                                    <>
                                        <Button variant="outline" className="flex-1" size="sm">Configure</Button>
                                        {/* m-3 fix: Wire Remove/Disconnect button */}
                                        <Button
                                            variant="destructive"
                                            className="flex-1"
                                            size="sm"
                                            onClick={() => handleDisconnect(connector.id)}
                                        >
                                            Remove
                                        </Button>
                                    </>
                                ) : (
                                    <Button className="w-full" onClick={() => handleConnect(connector.id)}>
                                        Install Connector
                                    </Button>
                                )}
                            </CardFooter>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}

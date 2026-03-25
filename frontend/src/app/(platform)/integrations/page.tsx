"use client"

import { useState, useEffect } from "react"
import { Database, Github, Key, Link as LinkIcon, Monitor, Slack } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { apiFetch } from "@/lib/api-client"
import { useSession } from "next-auth/react"
import { CapabilitiesDialog } from "./capabilities-dialog"

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
    const { data: session } = useSession()
    const [available, setAvailable] = useState<any[]>([])
    const [installed, setInstalled] = useState<any[]>([])
    const [oauthConnections, setOauthConnections] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const [isCapModalOpen, setIsCapModalOpen] = useState(false)
    const [selectedConnector, setSelectedConnector] = useState<any>(null)
    const [capabilities, setCapabilities] = useState<any[]>([])
    const [capsLoading, setCapsLoading] = useState(false)

    const fetchData = async () => {
        const orgId = session?.user?.org_id
        if (!orgId) return

        try {
            const [resAvail, resInst, resOauth] = await Promise.all([
                apiFetch('/api/connectors/available', { headers: { 'X-ScopeSentinel-Org-ID': orgId } }),
                apiFetch('/api/connectors/installed', { headers: { 'X-ScopeSentinel-Org-ID': orgId } }),
                apiFetch('/api/oauth-connections', { headers: { 'X-ScopeSentinel-Org-ID': orgId } }),
            ])
            setAvailable(await resAvail.json())
            setInstalled(await resInst.json())
            setOauthConnections(await resOauth.json())
        } catch (e) {
            console.error("Failed to fetch connectors", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { 
        if (session?.user?.org_id) {
            fetchData() 
        }
    }, [session])
    useEffect(() => {
        // Poll for oauth changes or check localStorage
        const handleOauthUpdate = () => fetchData();
        window.addEventListener('storage', (e) => {
            if (e.key?.startsWith('oauth_connected_')) fetchData();
        });
    }, [])

    const handleConnect = async (connector: any) => {
        const connectorId = connector.id;
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        if (connector.auth_type === 'oauth') {
            const user_id = session?.user?.email || "unknown";
            const authUrl = `http://localhost:8005/api/connections/oauth/${connectorId}/authorize?org_id=${orgId}&user_id=${user_id}`;
            window.location.href = authUrl;
            return;
        }
        try {
            const res = await apiFetch(`/api/connectors/${connectorId}/install`, {
                method: 'POST',
                headers: { 'X-ScopeSentinel-Org-ID': orgId },
                body: JSON.stringify({ config: { token: "" } }),
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
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        if (!confirm(`Remove ${connectorId} connection?`)) return
        try {
            await apiFetch(`/api/oauth-connections/${connectorId}`, { 
                method: 'DELETE',
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            })
            const res = await apiFetch(`/api/connectors/${connectorId}/uninstall`, { 
                method: 'DELETE',
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            })
            if (res.ok || res.status === 204) {
                fetchData()
            } else {
                // If it's oauth only, we might not have a "connector" record
                fetchData()
            }
        } catch (e) {
            alert("Error removing connector")
        }
    }

    const handleViewCapabilities = async (connector: any) => {
        const orgId = session?.user?.org_id;
        if (!orgId) return;

        setSelectedConnector(connector)
        setIsCapModalOpen(true)
        setCapsLoading(true)
        try {
            const res = await apiFetch(`/api/tools?org_id=${orgId}`, {
                headers: { 'X-ScopeSentinel-Org-ID': orgId }
            }) 
            const data = await res.json()
            const tools = data.tools || []
            const connectorTools = tools.filter((t: any) => 
                t.server_name === `oauth_${connector.id}_${orgId}` || 
                t.server_name.includes(connector.id)
            )
            setCapabilities(connectorTools)
        } catch (e) {
            console.error("Failed to fetch capabilities", e)
        } finally {
            setCapsLoading(false)
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
                    const oauthEntry = oauthConnections.find((oc: any) => oc.provider === connector.id)
                    const isConnected = !!instEntry || !!oauthEntry
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
                                            {instEntry?.connector_id ? "Installed" : "Connected"}
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
                                        <Button
                                            variant="outline"
                                            className="flex-1"
                                            size="sm"
                                            onClick={() => alert(`Configuration for ${connector.name} is coming soon.`)}
                                        >
                                            Configure
                                        </Button>
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
                                    <Button className="w-full" onClick={() => handleConnect(connector)}>
                                        Install Connector
                                    </Button>
                                )}
                                {oauthConnections.find((oc: any) => oc.provider === connector.id) && (
                                    <Button
                                        variant="secondary"
                                        className="w-full mt-2"
                                        size="sm"
                                        onClick={() => handleViewCapabilities(connector)}
                                    >
                                        View Capabilities
                                    </Button>
                                )}
                            </CardFooter>
                        </Card>
                    )
                })}
            </div>

            <CapabilitiesDialog
                isOpen={isCapModalOpen}
                onClose={() => setIsCapModalOpen(false)}
                connectorName={selectedConnector?.name || ""}
                capabilities={capabilities}
            />
        </div>
    )
}

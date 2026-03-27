"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import { 
    Link as LinkIcon, 
    ChevronDown, 
    Plus,
    Zap,
    Search
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { useApi } from "@/hooks/use-api"
import { CapabilitiesDialog } from "./capabilities-dialog"

export default function IntegrationsPage() {
    const api = useApi()
    const [available, setAvailable] = useState<any[]>([])
    const [installed, setInstalled] = useState<any[]>([])
    const [oauthConnections, setOauthConnections] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState("")
    const [error, setError] = useState<string | null>(null)

    const [isCapModalOpen, setIsCapModalOpen] = useState(false)
    const [selectedConnector, setSelectedConnector] = useState<any>(null)
    const [capabilities, setCapabilities] = useState<any[]>([])
    const [capsLoading, setCapsLoading] = useState(false)

    const searchParams = useSearchParams()

    const fetchData = useCallback(async () => {
        if (!api.orgId) return

        try {
            setLoading(true)
            setError(null)
            const [dataAvail, dataInst, dataOauth] = await Promise.all([
                api.get<any[]>('/api/connectors/available'),
                api.get<any[]>('/api/connectors/installed'),
                api.get<any[]>('/api/oauth-connections/'),
            ])
            setAvailable(dataAvail || [])
            setInstalled(dataInst || [])
            setOauthConnections(dataOauth || [])
        } catch (e) {
            console.error("Failed to fetch connectors", e)
            setError("Failed to load connectors. Please try again.")
        } finally {
            setLoading(false)
        }
    }, [api.orgId])

    // Re-fetch on orgId change
    useEffect(() => { 
        fetchData() 
    }, [fetchData])

    // Re-fetch when redirected back from OAuth provider (status=success in URL)
    useEffect(() => {
        if (searchParams.get('status') === 'success') {
            fetchData()
            // Clean up URL without triggering navigation
            const url = new URL(window.location.href)
            url.searchParams.delete('status')
            url.searchParams.delete('provider')
            window.history.replaceState({}, '', url.pathname)
        }
    }, [searchParams])

    const handleConnect = async (connector: any) => {
        const connectorId = connector.id
        if (!api.orgId) return

        if (connector.auth_type === 'oauth') {
            const user_id = api.session?.user?.email || "unknown"
            const authUrl = `http://localhost:8005/api/connections/oauth/${connectorId}/authorize?org_id=${api.orgId}&user_id=${user_id}`
            window.location.href = authUrl
            return
        }
        try {
            const res = await api.fetch(`/api/connectors/${connectorId}/install`, {
                method: 'POST',
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

    const handleDisconnect = async (connectorId: string) => {
        if (!api.orgId) return
        if (!confirm(`Remove ${connectorId} connection?`)) return
        try {
            await api.delete(`/api/oauth-connections/${connectorId}`)
            await api.delete(`/api/connectors/${connectorId}/uninstall`)
        } finally {
            fetchData()
        }
    }

    const handleViewCapabilities = async (connector: any) => {
        if (!api.orgId) return
        setSelectedConnector(connector)
        setIsCapModalOpen(true)
        setCapsLoading(true)
        try {
            const data = await api.get<any>(`/api/tools?org_id=${api.orgId}`) 
            const tools = (data as any).tools || []
            const connectorTools = tools.filter((t: any) => 
                t.server_name?.includes(connector.id)
            )
            setCapabilities(connectorTools)
        } catch (e) {
            console.error("Failed to fetch capabilities", e)
        } finally {
            setCapsLoading(false)
        }
    }

    const filteredApps = available.filter(app => 
        app.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.description?.toLowerCase().includes(searchQuery.toLowerCase())
    )

    if (loading) {
        return (
            <div className="flex flex-col gap-8 max-w-7xl mx-auto p-6 md:p-10">
                <div className="flex items-center justify-between">
                    <h1 className="text-4xl font-bold tracking-tight">Apps</h1>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="h-24 rounded-2xl bg-muted animate-pulse" />
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-8 max-w-7xl mx-auto p-6 md:p-10">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <h1 className="text-4xl font-bold tracking-tight">Apps</h1>
                <div className="flex items-center">
                    <DropdownMenu>
                        <DropdownMenuTrigger className="bg-[#2D2D2D] hover:bg-[#3D3D3D] text-white rounded-lg px-4 py-2 flex items-center gap-2 h-11 cursor-pointer outline-none">
                            <span className="font-semibold text-sm">Connect App</span>
                            <div className="w-px h-4 bg-white/20 mx-1" />
                            <ChevronDown className="h-4 w-4 opacity-70" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-[180px]">
                            <DropdownMenuItem className="flex items-center gap-2">
                                <Plus className="h-4 w-4" />
                                <span>Add API Key</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem className="flex items-center gap-2">
                                <Zap className="h-4 w-4" />
                                <span>Custom Webhook</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            {/* Sub-header */}
            <div className="flex flex-col gap-1">
                <h2 className="text-lg font-semibold">Connected Apps</h2>
                <p className="text-muted-foreground text-sm">
                    Manage your connected apps and API keys
                </p>
            </div>

            {/* Search Bar */}
            <div className="relative group">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors" />
                </div>
                <Input 
                    placeholder="Search apps..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-12 h-14 bg-background border-[#E5E5E5] focus-visible:ring-offset-0 focus-visible:ring-1 focus-visible:ring-primary rounded-xl text-lg shadow-sm"
                />
            </div>

            {/* Error state */}
            {error && (
                <div className="text-red-500 text-sm bg-red-50 border border-red-100 rounded-xl p-4">
                    {error}
                </div>
            )}

            {/* Grid */}
            {filteredApps.length === 0 && !error ? (
                <div className="text-center text-muted-foreground py-16">
                    No connectors found{searchQuery ? ` for "${searchQuery}"` : ""}.
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    {filteredApps.map((connector) => {
                        const instEntry = installed.find((i: any) => i.connector_id === connector.id)
                        const oauthEntry = oauthConnections.find((oc: any) => oc.provider === connector.id)
                        const isConnected = !!instEntry || !!oauthEntry

                        return (
                            <div key={connector.id} className="group relative flex items-center justify-between p-5 bg-white border border-[#F0F0F0] hover:border-primary/20 hover:shadow-md transition-all duration-200 rounded-2xl">
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex-shrink-0 w-14 h-14 rounded-xl border border-[#F0F0F0] flex items-center justify-center bg-white shadow-sm group-hover:bg-primary/5 transition-colors overflow-hidden">
                                        {connector.icon_url ? (
                                            // eslint-disable-next-line @next/next/no-img-element
                                            <img 
                                                src={connector.icon_url} 
                                                alt={connector.name}
                                                className="w-8 h-8 object-contain"
                                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                            />
                                        ) : (
                                            <LinkIcon className="h-7 w-7 text-[#2D2D2D] group-hover:text-primary transition-colors" />
                                        )}
                                    </div>
                                    <div className="flex flex-col min-w-0 pr-4">
                                        <div className="flex items-center gap-2">
                                            <h3 className="font-bold text-[#1A1A1A] truncate text-lg">
                                                {connector.name}
                                            </h3>
                                            {isConnected && (
                                                <Badge variant="secondary" className="bg-green-500/10 text-green-600 border-none font-medium h-5 px-1.5 text-[10px] uppercase tracking-wider">
                                                    Connected
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="text-[#6B7280] text-sm line-clamp-1 leading-relaxed mt-0.5">
                                            {connector.description}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex flex-shrink-0 items-center">
                                    {isConnected ? (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleDisconnect(connector.id)}
                                            className="rounded-lg h-10 px-6 font-semibold border-[#E5E5E5] hover:bg-red-50 hover:text-red-600 hover:border-red-100 transition-all"
                                        >
                                            Disconnect
                                        </Button>
                                    ) : (
                                        <Button 
                                            onClick={() => handleConnect(connector)}
                                            className="bg-[#F8F9FA] hover:bg-[#EDEDED] text-[#2D2D2D] border border-[#E5E5E5] rounded-xl h-10 px-6 font-semibold shadow-none transition-colors"
                                        >
                                            Connect
                                        </Button>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {selectedConnector && (
                <CapabilitiesDialog
                    isOpen={isCapModalOpen}
                    onClose={() => setIsCapModalOpen(false)}
                    connectorName={selectedConnector?.name || ""}
                    capabilities={capabilities}
                />
            )}
        </div>
    )
}

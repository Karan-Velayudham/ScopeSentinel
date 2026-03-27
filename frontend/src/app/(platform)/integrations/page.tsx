"use client"

import { useState, useEffect } from "react"
import { 
    Database, 
    Github, 
    Key, 
    Link as LinkIcon, 
    Monitor, 
    Slack, 
    Search, 
    ChevronDown, 
    Plus,
    Flame,
    Cloud,
    Layout,
    Type,
    StickyNote,
    Grid3X3,
    Rss,
    Zap
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

const MOCK_APPS = [
    { id: "firestore", name: "Firestore", description: "Build powerful, scalable database automations.", category: "Database", icon: Flame },
    { id: "bigquery", name: "BigQuery", description: "Transform and analyze large datasets effortlessly.", category: "Data Warehouse", icon: Cloud },
    { id: "slack", name: "Slack", description: "Automate team communications and boost work...", category: "Chat", icon: Slack },
    { id: "custom-slack", name: "Custom Slack App", description: "Connect your custom Slack app to Gumloop", category: "Chat", icon: Slack },
    { id: "wordpress", name: "WordPress", description: "Automate content publishing and website manag...", category: "CMS", icon: Layout },
    { id: "typeform", name: "Typeform", description: "Transform survey responses into automated wor...", category: "Forms", icon: Type },
    { id: "notion", name: "Notion", description: "Build powerful knowledge management automat...", category: "Productivity", icon: StickyNote },
    { id: "airtable", name: "Airtable", description: "Create powerful automated workflows with your...", category: "Database", icon: Grid3X3 },
    { id: "inoreader", name: "Inoreader", description: "Transform RSS content into automated actions.", category: "RSS", icon: Rss },
    { id: "hubspot", name: "HubSpot", description: "Supercharge your sales and marketing automati...", category: "CRM", icon: Zap },
]

export default function IntegrationsPage() {
    const api = useApi()
    const [available, setAvailable] = useState<any[]>([])
    const [installed, setInstalled] = useState<any[]>([])
    const [oauthConnections, setOauthConnections] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState("")

    const [isCapModalOpen, setIsCapModalOpen] = useState(false)
    const [selectedConnector, setSelectedConnector] = useState<any>(null)
    const [capabilities, setCapabilities] = useState<any[]>([])
    const [capsLoading, setCapsLoading] = useState(false)

    const fetchData = async () => {
        if (!api.orgId) {
            setAvailable(MOCK_APPS)
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            const [dataAvail, dataInst, dataOauth] = await Promise.all([
                api.get<any[]>('/api/connectors/available'),
                api.get<any[]>('/api/connectors/installed'),
                api.get<any[]>('/api/oauth-connections'),
            ])
            
            // Merge actual available apps with mock apps that aren't already there
            const actualAvail = dataAvail || []
            const mergedAvail = [...actualAvail]
            
            MOCK_APPS.forEach(mock => {
                if (!mergedAvail.find(a => a.id === mock.id)) {
                    mergedAvail.push(mock)
                }
            })

            setAvailable(mergedAvail)
            setInstalled(dataInst || [])
            setOauthConnections(dataOauth || [])
        } catch (e) {
            console.error("Failed to fetch connectors", e)
            setAvailable(MOCK_APPS)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { 
        fetchData() 
    }, [api.orgId])

    useEffect(() => {
        const handleOauthUpdate = () => fetchData();
        window.addEventListener('storage', (e) => {
            if (e.key?.startsWith('oauth_connected_')) fetchData();
        });
    }, [])

    const handleConnect = async (connector: any) => {
        const connectorId = connector.id;
        if (!api.orgId) return;

        if (connector.auth_type === 'oauth') {
            const user_id = api.session?.user?.email || "unknown";
            const authUrl = `http://localhost:8005/api/connections/oauth/${connectorId}/authorize?org_id=${api.orgId}&user_id=${user_id}`;
            window.location.href = authUrl;
            return;
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
        if (!api.orgId) return;
        if (!confirm(`Remove ${connectorId} connection?`)) return
        try {
            await api.delete(`/api/oauth-connections/${connectorId}`)
            await api.delete(`/api/connectors/${connectorId}/uninstall`)
            fetchData()
        } catch (e) {
            fetchData()
        }
    }

    const handleViewCapabilities = async (connector: any) => {
        if (!api.orgId) return;
        setSelectedConnector(connector)
        setIsCapModalOpen(true)
        setCapsLoading(true)
        try {
            const data = await api.get<any>(`/api/tools?org_id=${api.orgId}`) 
            const tools = data.tools || []
            const connectorTools = tools.filter((t: any) => 
                t.server_name === `oauth_${connector.id}_${api.orgId}` || 
                t.server_name.includes(connector.id)
            )
            setCapabilities(connectorTools)
        } catch (e) {
            console.error("Failed to fetch capabilities", e)
        } finally {
            setCapsLoading(false)
        }
    }

    const filteredApps = available.filter(app => 
        app.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.description.toLowerCase().includes(searchQuery.toLowerCase())
    )

    if (loading) return <div className="p-8">Loading Marketplace...</div>

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

            {/* Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {filteredApps.map((connector) => {
                    const instEntry = installed.find((i: any) => i.connector_id === connector.id)
                    const oauthEntry = oauthConnections.find((oc: any) => oc.provider === connector.id)
                    const isConnected = !!instEntry || !!oauthEntry
                    const Icon = connector.icon || LinkIcon

                    return (
                        <div key={connector.id} className="group relative flex items-center justify-between p-5 bg-white border border-[#F0F0F0] hover:border-primary/20 hover:shadow-md transition-all duration-200 rounded-2xl">
                            <div className="flex items-center gap-4 flex-1">
                                <div className="flex-shrink-0 w-14 h-14 rounded-xl border border-[#F0F0F0] flex items-center justify-center bg-white shadow-sm group-hover:bg-primary/5 transition-colors">
                                    <Icon className="h-7 w-7 text-[#2D2D2D] group-hover:text-primary transition-colors" />
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

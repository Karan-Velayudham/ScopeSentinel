"use client"

import { useState, useEffect } from "react"
import { Bot, Plus, Pencil, Trash2, Search, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { useApi } from "@/hooks/use-api"
import Link from "next/link"
import { AgentResponse } from "@/types/agent"

export default function AgentsPage() {
    const api = useApi()
    const [agents, setAgents] = useState<AgentResponse[]>([])
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState("")

    const fetchAgents = async () => {
        if (!api.orgId) return

        try {
            const data = await api.get<{ items: AgentResponse[] }>('/api/agents/')
            setAgents(data.items || [])
        } catch (e) {
            console.error("Failed to fetch agents", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { 
        if (api.orgId) {
            fetchAgents() 
        }
    }, [api.orgId])

    const handleDelete = async (agentId: string, name: string) => {
        if (!api.orgId) return

        if (!confirm(`Are you sure you want to delete agent "${name}"?`)) return
        try {
            await api.delete(`/api/agents/${agentId}`)
            setAgents(agents.filter(a => a.id !== agentId))
        } catch (e) {
            alert("Error deleting agent")
        }
    }

    const filteredAgents = agents.filter(a =>
        a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
    )

    if (loading) return <div className="p-8">Loading Agents...</div>

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between border-b pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
                    <p className="text-muted-foreground mt-1">
                        Build and manage custom AI agents with specialized identities and toolsets.
                    </p>
                </div>
                <Link href="/agents/new">
                    <Button>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Agent
                    </Button>
                </Link>
            </div>

            <div className="flex items-center gap-2 max-w-md">
                <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search agents..."
                        className="pl-8"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredAgents.map((agent) => (
                    <Card key={agent.id} className="flex flex-col shadow-sm border-2 hover:border-primary/50 transition-colors">
                        <Link href={`/agents/${agent.id}/chat`} className="flex-1">
                        <CardHeader className="pb-4">
                            <div className="flex items-start justify-between">
                                <div className="p-2 bg-primary/10 rounded-md">
                                    <Bot className="h-6 w-6 text-primary" />
                                </div>
                                <Badge variant="outline">{agent.model}</Badge>
                            </div>
                            <CardTitle className="mt-4">{agent.name}</CardTitle>
                            <CardDescription className="line-clamp-2 min-h-[40px]">
                                {agent.description || "No description provided."}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="flex-1">
                            <div className="flex gap-4">
                                <div>
                                    <div className="text-xs text-muted-foreground mb-1">Skills</div>
                                    <div className="text-sm font-semibold">
                                        {agent.skills?.length || 0}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-xs text-muted-foreground mb-1">Apps Connected</div>
                                    <div className="text-sm font-semibold">
                                        {agent.app_connections?.length || 0}
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                        </Link>
                        <CardFooter className="pt-4 border-t flex gap-2">
                            <Link href={`/agents/${agent.id}/chat`} className="flex-1">
                                <Button variant="default" className="w-full" size="sm">
                                    <MessageSquare className="h-4 w-4 mr-2" />
                                    Chat
                                </Button>
                            </Link>
                            <Link href={`/agents/${agent.id}`}>
                                <Button variant="outline" size="sm" className="px-3">
                                    <Pencil className="h-4 w-4" />
                                </Button>
                            </Link>
                            <Button
                                variant="destructive"
                                size="sm"
                                className="px-3"
                                onClick={() => handleDelete(agent.id, agent.name)}
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </CardFooter>
                    </Card>
                ))}

                {filteredAgents.length === 0 && !loading && (
                    <div className="col-span-full flex flex-col items-center justify-center py-12 border-2 border-dashed rounded-lg bg-muted/20">
                        <Bot className="h-12 w-12 text-muted-foreground mb-4 opacity-20" />
                        <h3 className="text-lg font-medium">No agents found</h3>
                        <p className="text-muted-foreground">Get started by creating your first specialized AI agent.</p>
                        <Link href="/agents/new" className="mt-4">
                            <Button variant="outline">Create Agent</Button>
                        </Link>
                    </div>
                )}
            </div>
        </div>
    )
}

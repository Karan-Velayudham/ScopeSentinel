"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { Bot, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { AgentForm } from "@/components/agents/AgentForm"
import { apiFetch } from "@/lib/api-client"

export default function EditAgentPage() {
    const params = useParams()
    const id = params.id as string
    const [agent, setAgent] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchAgent = async () => {
            try {
                const res = await apiFetch(`/api/agents/${id}`)
                if (res.ok) {
                    setAgent(await res.json())
                }
            } catch (e) {
                console.error("Failed to fetch agent", e)
            } finally {
                setLoading(false)
            }
        }
        fetchAgent()
    }, [id])

    if (loading) return <div className="p-8">Loading Agent...</div>
    if (!agent) return <div className="p-8 text-destructive">Agent not found.</div>

    return (
        <div className="flex flex-col gap-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-4 border-b pb-4">
                <Link href="/agents">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                </Link>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Edit Agent: {agent.name}</h1>
                    <p className="text-muted-foreground mt-1">
                        Update the identity, model, or tools for this agent.
                    </p>
                </div>
            </div>

            <div className="bg-card border rounded-lg p-6 shadow-sm">
                <AgentForm initialData={agent} isEditing />
            </div>
        </div>
    )
}

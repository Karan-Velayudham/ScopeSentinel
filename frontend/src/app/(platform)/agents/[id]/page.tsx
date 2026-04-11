"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { Bot, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { AgentBuilder } from "@/components/agents/AgentBuilder"
import { useApi } from "@/hooks/use-api"
import { AgentResponse } from "@/types/agent"

export default function EditAgentPage() {
    const api = useApi()
    const params = useParams()
    const id = params.id as string
    const [agent, setAgent] = useState<AgentResponse | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchAgent = async () => {
            if (!api.orgId) return

            try {
                const res = await api.fetch(`/api/agents/${id}`)
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
    }, [id, api.orgId])

    if (loading) return <div className="p-8 flex items-center justify-center">Loading Agent...</div>
    if (!agent) return <div className="p-8 text-destructive flex items-center justify-center">Agent not found.</div>

    return (
        <div className="-m-6 md:-m-8 h-[calc(100vh-theme(spacing.16))] flex overflow-hidden">
            <AgentBuilder initialData={agent} isEditing />
        </div>
    )
}

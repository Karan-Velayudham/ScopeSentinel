"use client"

import { Bot, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { AgentForm } from "@/components/agents/AgentForm"

export default function NewAgentPage() {
    return (
        <div className="flex flex-col gap-6 max-w-5xl mx-auto">
            <div className="flex items-center gap-4 border-b pb-4">
                <Link href="/agents">
                    <Button variant="ghost" size="icon">
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                </Link>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Create Agent</h1>
                    <p className="text-muted-foreground mt-1">
                        Define a new specialized persona and toolset.
                    </p>
                </div>
            </div>

            <div className="bg-card border rounded-lg p-6 shadow-sm">
                <AgentForm />
            </div>
        </div>
    )
}

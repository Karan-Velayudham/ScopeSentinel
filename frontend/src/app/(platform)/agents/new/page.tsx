"use client"

import { AgentBuilder } from "@/components/agents/AgentBuilder"

export default function NewAgentPage() {
    return (
        <div className="-m-6 md:-m-8 h-[calc(100vh-theme(spacing.16))] flex overflow-hidden">
            <AgentBuilder />
        </div>
    )
}

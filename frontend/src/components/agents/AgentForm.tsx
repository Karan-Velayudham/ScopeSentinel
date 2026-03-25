"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Save, Check, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { useApi } from "@/hooks/use-api"

interface AgentFormProps {
    initialData?: {
        id: string;
        name: string;
        description?: string;
        identity: string;
        model: string;
        tools: string[];
    };
    isEditing?: boolean;
}

const AVAILABLE_MODELS = [
    { id: "gpt-4o", name: "GPT-4o (Reasoning)" },
    { id: "gpt-4o-mini", name: "GPT-4o Mini (Fast)" },
    { id: "claude-3-5-sonnet", name: "Claude 3.5 Sonnet (Nuanced)" },
    { id: "claude-3-haiku", name: "Claude 3 Haiku (Streaming)" },
]

const COMMON_TOOLS = [
    "fetch_jira_ticket",
    "update_jira_ticket",
    "search_index",
    "write_file",
    "shell_command",
    "github_create_pr",
    "slack_notify"
]

export function AgentForm({ initialData, isEditing = false }: AgentFormProps) {
    const api = useApi()
    const router = useRouter()
    const [loading, setLoading] = useState(false)
    const [formData, setFormData] = useState({
        name: initialData?.name || "",
        description: initialData?.description || "",
        identity: initialData?.identity || "",
        model: initialData?.model || "gpt-4o",
        tools: initialData?.tools || []
    })

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!api.orgId) {
            alert("No organization context found. Please log in again.")
            return
        }

        setLoading(true)

        const url = isEditing && initialData ? `/api/agents/${initialData.id}` : "/api/agents"
        const method = isEditing ? "PUT" : "POST"

        try {
            const res = await api.fetch(url, {
                method,
                body: JSON.stringify(formData)
            })

            if (res.ok) {
                router.push("/agents")
                router.refresh()
            } else {
                const err = await res.json()
                alert(err.detail || "Failed to save agent")
            }
        } catch (e) {
            alert("Error saving agent")
        } finally {
            setLoading(false)
        }
    }

    const toggleTool = (tool: string) => {
        setFormData(prev => ({
            ...prev,
            tools: prev.tools.includes(tool)
                ? prev.tools.filter((t: string) => t !== tool)
                : [...prev.tools, tool]
        }))
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Agent Name</Label>
                        <Input
                            id="name"
                            placeholder="e.g. Code Auditor"
                            required
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="model">Model</Label>
                        <Select
                            value={formData.model}
                            onValueChange={(v) => setFormData({ ...formData, model: v || 'gpt-4o' })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select a model" />
                            </SelectTrigger>
                            <SelectContent>
                                {AVAILABLE_MODELS.map(m => (
                                    <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="description">Description</Label>
                        <Textarea
                            id="description"
                            placeholder="What does this agent do?"
                            rows={3}
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>
                </div>

                <div className="space-y-4">
                    <Label>Tools / Capabilities</Label>
                    <div className="flex flex-wrap gap-2 p-4 border rounded-md min-h-[120px] bg-muted/20">
                        {COMMON_TOOLS.map(tool => {
                            const isSelected = formData.tools.includes(tool)
                            return (
                                <Badge
                                    key={tool}
                                    variant={isSelected ? "default" : "outline"}
                                    className={`cursor-pointer transition-all hover:scale-105 ${isSelected ? 'bg-primary' : 'hover:bg-primary/10'}`}
                                    onClick={() => toggleTool(tool)}
                                >
                                    {tool}
                                    {isSelected ? <Check className="ml-1 h-3 w-3" /> : <Plus className="ml-1 h-3 w-3" />}
                                </Badge>
                            )
                        })}
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Select tool capabilities that this agent will have access to via MCP.
                    </p>
                </div>
            </div>

            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <Label htmlFor="identity">Identity & Instructions (System Prompt)</Label>
                    <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider opacity-60">System Message</Badge>
                </div>
                <Textarea
                    id="identity"
                    placeholder="You are an expert software engineer... Your task is to..."
                    className="font-mono text-sm min-h-[300px] resize-y"
                    required
                    value={formData.identity}
                    onChange={(e) => setFormData({ ...formData, identity: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                    Define how the agent thinks, its persona, and specific formatting rules.
                </p>
            </div>

            <div className="flex items-center gap-4 pt-4 border-t">
                <Button type="submit" disabled={loading}>
                    {loading ? "Saving..." : <><Save className="h-4 w-4 mr-2" /> Save Agent</>}
                </Button>
                <Button type="button" variant="ghost" onClick={() => router.back()}>
                    Cancel
                </Button>
            </div>
        </form>
    )
}

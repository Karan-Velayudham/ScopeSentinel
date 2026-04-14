import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { 
    Share, MessageSquare, PanelRightClose, Activity, Image as ImageIcon, 
    Globe, Paperclip, SquarePen, ArrowUp, Undo2, ChevronDown, 
    ExternalLink, Settings2, Sparkles, ChevronRight, FileEdit, 
    Plus, ListTodo, MoreVertical, Search, Zap, Hexagon, Loader2
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { useApi } from "@/hooks/use-api"

interface Skill {
    id: string;
    name: string;
    content: string;
}

interface Tool {
    name: string;
    description: string;
}

interface Connector {
    connector_id: string;
    connector_name: string;
    icon_url: string;
    tools: Tool[];
}

interface FormData {
    name: string;
    description: string;
    instructions: string;
    model: string;
    app_connections: string[];
    skills: string[];
    timeout_seconds: number;
    self_improve: boolean;
}

interface AgentBuilderProps {
    initialData?: {
        id: string;
        name: string;
        description?: string | null;
        instructions: string;
        model: string;
        app_connections: string[];
        skills: string[];
        timeout_seconds: number;
        self_improve?: boolean;
    };
    isEditing?: boolean;
}

export function AgentBuilder({ initialData, isEditing = false }: AgentBuilderProps) {
    const router = useRouter()
    const api = useApi()
    
    // Form State
    const [formData, setFormData] = useState<FormData>({
        name: initialData?.name || "Ready Maker",
        description: initialData?.description || "",
        instructions: initialData?.instructions || "",
        model: initialData?.model || "claude-3-5-sonnet-20240620",
        app_connections: initialData?.app_connections || [],
        skills: initialData?.skills || [],
        timeout_seconds: initialData?.timeout_seconds || 60,
        self_improve: initialData?.self_improve ?? true
    })
    
    const [msg, setMsg] = useState("")
    const [executing, setExecuting] = useState(false)
    const [executionResult, setExecutionResult] = useState<string | null>(null)
    const [skills, setSkills] = useState<Skill[]>([])
    const [connectors, setConnectors] = useState<Connector[]>([])
    const [models, setModels] = useState<{value: string, label: string}[]>([])
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        if (!api.orgId) return;

        const fetchData = async () => {
            setLoading(true)
            try {
                const [skillsData, connectorsData, modelsData] = await Promise.all([
                    api.get<{ items: Skill[] }>('/api/skills'),
                    api.get<Connector[]>('/api/connectors/installed'),
                    api.get<{value: string, label: string}[]>('/api/models/').catch(() => [])
                ])
                setSkills(skillsData.items || [])
                setConnectors(connectorsData || [])
                setModels(modelsData || [])
            } catch (err) {
                console.error("Failed to fetch builder data", err)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [api.orgId])

    const handleSave = async () => {
        if (!api.orgId) return;
        setSaving(true)
        try {
            const url = isEditing && initialData ? `/api/agents/${initialData.id}` : '/api/agents/';
            const method = isEditing ? 'PUT' : 'POST';
            
            await api.fetch(url, {
                method,
                body: JSON.stringify({
                    name: formData.name,
                    description: formData.description,
                    instructions: formData.instructions,
                    model: formData.model,
                    app_connections: formData.app_connections,
                    skills: formData.skills,
                    timeout_seconds: formData.timeout_seconds,
                    status: "active"
                })
            })
            router.push('/agents')
        } catch (err) {
            alert("Failed to save agent")
        } finally {
            setSaving(false)
        }
    }

    const toggleAppConnection = (connectorId: string) => {
        setFormData((prev: FormData) => ({
            ...prev,
            app_connections: prev.app_connections.includes(connectorId) 
                ? prev.app_connections.filter((id: string) => id !== connectorId)
                : [...prev.app_connections, connectorId]
        }))
    }

    const handleExecute = async () => {
        if (!isEditing || !initialData?.id) {
            alert("Please save the agent first before testing.")
            return;
        }
        if (!msg.trim()) return;

        setExecuting(true)
        setExecutionResult(null)
        try {
            const inputData = { task: msg }
            const res = await api.post<{ output: string }>(`/api/agents/${initialData.id}/execute`, {
                input: inputData,
                skill_ids: formData.skills,
                triggered_by: "manual"
            })
            setExecutionResult(res.output || "No output returned.")
        } catch (err: any) {
            setExecutionResult(`Error: ${err.message || String(err)}`)
        } finally {
            setExecuting(false)
        }
    }

    const toggleSkill = (skillId: string) => {
        setFormData((prev: FormData) => ({
            ...prev,
            skills: prev.skills.includes(skillId)
                ? prev.skills.filter((s: string) => s !== skillId)
                : [...prev.skills, skillId]
        }))
    }

    return (
        <div className="flex-1 flex w-full bg-background h-full overflow-hidden">
            {/* Left Main Area */}
            <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-zinc-950">
                {/* Top Nav */}
                <div className="h-14 border-b flex items-center justify-between px-4">
                    <div className="flex items-center gap-2">
                        <div className="w-7 h-7 bg-black dark:bg-white rounded-md flex items-center justify-center text-white dark:text-black">
                            <span className="font-bold text-xs">{formData.name ? formData.name.charAt(0).toUpperCase() : 'A'}</span>
                        </div>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="font-semibold text-sm bg-transparent border-none outline-none focus:ring-0 p-0 w-[200px]"
                            placeholder="Agent Name"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" className="text-muted-foreground h-8 text-xs font-medium">
                            <Share className="w-3.5 h-3.5 mr-1.5"/> Share
                        </Button>
                        <Button variant="ghost" size="sm" className="text-muted-foreground h-8 text-xs font-medium">
                            <MessageSquare className="w-3.5 h-3.5 mr-1.5"/> Add to Slack
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 ml-2 text-muted-foreground">
                            <PanelRightClose className="w-4 h-4" />
                        </Button>
                    </div>
                </div>

                {/* Center Content */}
                <div className="flex-1 flex flex-col items-center justify-center p-8 relative overflow-y-auto">
                    {/* Floating icons graphic */}
                    <div className="relative w-40 h-40 flex items-center justify-center mb-10">
                        {/* Orbital items */}
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-4 w-9 h-9 rounded-full border bg-white flex items-center justify-center shadow-sm z-10">
                            <Activity className="w-4 h-4 text-blue-500" />
                        </div>
                        <div className="absolute bottom-6 left-0 -translate-x-2 w-9 h-9 rounded-full border bg-white flex items-center justify-center shadow-sm z-10">
                            <ImageIcon className="w-4 h-4 text-gray-500" />
                        </div>
                        <div className="absolute bottom-6 right-0 translate-x-2 w-9 h-9 rounded-full border bg-white flex items-center justify-center shadow-sm z-10">
                            <Globe className="w-4 h-4 text-gray-500" />
                        </div>

                        {/* Central Avatar */}
                        <div className="w-20 h-20 bg-[#111] dark:bg-white rounded-[24px] rotate-45 flex items-center justify-center shadow-md relative z-20">
                            <div className="-rotate-45 flex gap-1.5">
                                <div className="w-2.5 h-6 bg-white dark:bg-black rounded-full shadow-inner"></div>
                                <div className="w-2.5 h-6 bg-white dark:bg-black rounded-full shadow-inner"></div>
                            </div>
                        </div>
                        
                        {/* Orbital path placeholder (optional subtle ring) */}
                        <div className="absolute inset-0 border rounded-full opacity-20 scale-[1.15]"></div>
                    </div>

                    {!executionResult && !executing && (
                        <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-foreground mb-10 text-center">
                            {isEditing ? `Test ${formData.name}` : "Hi, how can I help you?"}
                        </h1>
                    )}

                    {(executing || executionResult) && (
                        <div className="w-full max-w-2xl mb-8 p-4 bg-muted/30 rounded-xl border">
                            {executing ? (
                                <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> Executing agent...</div>
                            ) : (
                                <div className="whitespace-pre-wrap text-sm font-medium">{executionResult}</div>
                            )}
                        </div>
                    )}

                    {/* Chat Input */}
                    <div className="w-full max-w-2xl relative">
                        <div className="relative border shadow-sm bg-card rounded-[18px] overflow-hidden p-3 flex flex-col min-h-[140px] focus-within:ring-1 focus-within:ring-ring transition-all">
                            <textarea
                                className="flex-1 w-full resize-none outline-none text-base placeholder:text-muted-foreground/70 bg-transparent px-1 mt-1 font-medium"
                                placeholder="Send a message to your agent"
                                value={msg}
                                onChange={e => setMsg(e.target.value)}
                            />
                            <div className="flex items-center justify-between mt-2">
                                <div className="flex items-center gap-1.5 text-muted-foreground">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
                                        <Paperclip className="w-4 h-4" />
                                    </Button>
                                    <Button variant="ghost" size="sm" className="h-8 text-xs font-semibold rounded-full px-3">
                                        <SquarePen className="w-3.5 h-3.5 mr-1.5" /> Skill
                                    </Button>
                                </div>
                                <Button 
                                    size="icon" 
                                    onClick={handleExecute}
                                    disabled={executing || !msg.trim()}
                                    className={`h-8 w-8 rounded-full transition-all duration-300 ${msg.length > 0 ? "bg-black text-white dark:bg-white dark:text-black" : "bg-gradient-to-tr from-rose-300 to-indigo-400 text-white"}`}
                                >
                                    {executing ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUp className="w-4 h-4" />}
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Config Panel */}
            <div className="w-[380px] border-l flex flex-col bg-zinc-50/50 dark:bg-zinc-950 overflow-hidden shrink-0">
                {/* Header Actions */}
                <div className="h-14 border-b flex items-center justify-between px-4 bg-white dark:bg-zinc-950 shrink-0">
                    <div className="flex gap-2 w-full">
                        <Button 
                            variant="secondary" 
                            className="flex-1 h-8 text-xs font-semibold bg-zinc-100 hover:bg-zinc-200 text-zinc-900 dark:text-zinc-100"
                            onClick={handleSave}
                            disabled={saving}
                        >
                            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> : "Save"} <kbd className="ml-2 font-mono text-[9px] bg-white/50 px-1.5 py-0.5 rounded shadow-sm text-zinc-500">⌘ S</kbd>
                        </Button>
                        <Button variant="ghost" className="flex-1 h-8 text-xs font-semibold text-zinc-400 hover:bg-zinc-100" onClick={() => router.back()}>
                            <Undo2 className="w-3.5 h-3.5 mr-1.5" /> Revert <kbd className="ml-2 font-mono text-[9px] border px-1.5 py-0.5 rounded shadow-sm">⌘ U</kbd>
                        </Button>
                    </div>
                </div>

                {/* Scrolled Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-6">
                    {/* Group: Agent Preferences */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm px-1">
                            <div className="flex items-center gap-1.5 font-semibold text-foreground">
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                                Agent Preferences <ExternalLink className="w-3 h-3 text-muted-foreground ml-0.5" />
                            </div>
                            <div className="flex items-center gap-1 text-xs text-muted-foreground font-medium cursor-pointer hover:text-foreground">
                                Advanced <Settings2 className="w-3.5 h-3.5" />
                            </div>
                        </div>

                        <div className="border rounded-xl bg-white dark:bg-zinc-900 shadow-sm overflow-hidden flex flex-col">
                            <div className="p-3.5 border-b flex items-center justify-between bg-zinc-50/50">
                                <div className="flex items-center gap-2 text-sm w-full">
                                    <Sparkles className="w-4 h-4 text-orange-500 fill-orange-500/20" />
                                    <span className="font-semibold text-[13px] mr-2">Model:</span>
                                    <select 
                                        className="flex-1 bg-transparent text-sm font-medium outline-none text-slate-700 dark:text-slate-300"
                                        value={formData.model}
                                        onChange={(e) => setFormData({...formData, model: e.target.value})}
                                    >
                                        {models.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                        {models.length === 0 && (
                                            <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet</option>
                                        )}
                                    </select>
                                </div>
                            </div>
                            <div className="p-3">
                                <textarea
                                    className="w-full outline-none resize-none text-[13px] min-h-[90px] bg-transparent placeholder:text-muted-foreground/60 focus:ring-0 font-medium"
                                    placeholder="Add instructions for the agent..."
                                    value={formData.instructions}
                                    onChange={e => setFormData({ ...formData, instructions: e.target.value })}
                                />
                            </div>
                            <div className="px-1 pb-1 pt-0 flex justify-end">
                              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="text-muted-foreground/30 mr-1 mb-1"><path d="M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M5 9H9V5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                            </div>
                        </div>

                        <div className="flex items-center justify-between px-2 py-1 mt-1">
                            <div className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
                                <FileEdit className="w-4 h-4 text-muted-foreground" /> Self-Improve Instructions
                            </div>
                            <Switch 
                                checked={formData.self_improve} 
                                onCheckedChange={v => setFormData({ ...formData, self_improve: v })} 
                            />
                        </div>
                    </div>

                    {/* Group: Tasks */}
                    <div className="space-y-3 pt-5 border-t">
                        <div className="flex items-center justify-between text-sm px-1">
                            <div className="flex items-center gap-1.5 font-semibold text-foreground">
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                                Tasks
                            </div>
                            <Button variant="outline" size="sm" className="h-[26px] px-2.5 rounded-full text-[11px] font-semibold bg-white">
                                <Plus className="w-3 h-3 mr-1" /> Task
                            </Button>
                        </div>
                        <div className="flex items-center justify-between px-2">
                            <div className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
                                <ListTodo className="w-4 h-4 text-muted-foreground" /> AI Task Editing & Creation
                            </div>
                            <Switch defaultChecked />
                        </div>
                    </div>

                    {/* Group: Tools */}
                    <div className="space-y-3 pt-5 border-t">
                        <div className="flex items-center justify-between text-sm px-1">
                            <div className="flex items-center gap-1.5 font-semibold text-foreground">
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                                Tools <ExternalLink className="w-3 h-3 text-muted-foreground ml-0.5" />
                            </div>
                            <div className="flex gap-1.5">
                                <Button variant="outline" size="sm" className="h-[26px] px-2.5 rounded-full text-[11px] font-semibold bg-white">
                                    <Plus className="w-3 h-3 mr-1" /> Workflow
                                </Button>
                                <Button variant="outline" size="sm" className="h-[26px] px-2.5 rounded-full text-[11px] font-semibold bg-white">
                                    <Plus className="w-3 h-3 mr-1" /> App
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-1 mt-2">
                            {connectors.map((conn: Connector) => (
                                <div key={conn.connector_id} className="space-y-1">
                                    <div className="flex items-center justify-between px-2 py-2 bg-zinc-100/30 rounded-lg">
                                        <div className="flex items-center gap-3 text-[13px]">
                                            <div className="w-7 h-7 bg-white rounded flex items-center justify-center shrink-0 border shadow-sm">
                                                <img src={conn.icon_url} className="w-4 h-4 object-contain" alt="" />
                                            </div>
                                            <span className="font-semibold">{conn.connector_name}</span>
                                        </div>
                                        <Switch 
                                            checked={formData.app_connections.includes(conn.connector_id)} 
                                            onCheckedChange={() => toggleAppConnection(conn.connector_id)} 
                                        />
                                    </div>
                                    <div className="pl-10 space-y-1 py-1">
                                        {conn.tools.map((tool: Tool) => (
                                            <div key={tool.name} className="flex items-center justify-between py-1 px-1 hover:bg-zinc-50 rounded transition-colors group">
                                                <span className="text-[12px] font-medium text-muted-foreground group-hover:text-foreground">{tool.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            {connectors.length === 0 && !loading && (
                                <div className="text-xs text-center text-muted-foreground py-4 italic">No connectors found</div>
                            )}
                            {loading && (
                                <div className="flex items-center justify-center py-4"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>
                            )}
                        </div>
                    </div>

                    {/* Group: Skills */}
                    <div className="space-y-3 pt-5 border-t">
                        <div className="flex items-center justify-between text-sm px-1">
                            <div className="flex items-center gap-1.5 font-semibold text-foreground">
                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                                Skills
                            </div>
                            <Button variant="outline" size="sm" className="h-[26px] px-2.5 rounded-full text-[11px] font-semibold bg-white">
                                <Plus className="w-3 h-3 mr-1" /> Skill
                            </Button>
                        </div>
                        {skills.map((skill: Skill) => (
                            <div key={skill.id} className="flex items-center justify-between px-2 py-1">
                                <div className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
                                    <Zap className="w-4 h-4 text-muted-foreground" /> {skill.name}
                                </div>
                                <Switch 
                                    checked={formData.skills.includes(skill.id)} 
                                    onCheckedChange={() => toggleSkill(skill.id)} 
                                />
                            </div>
                        ))}
                        {skills.length === 0 && !loading && (
                            <div className="text-xs text-center text-muted-foreground py-4 italic">No skills defined</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

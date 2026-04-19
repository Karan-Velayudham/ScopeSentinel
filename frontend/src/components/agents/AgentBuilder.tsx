import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { 
    Share, MessageSquare, PanelRightClose, Activity, Image as ImageIcon, 
    Globe, Paperclip, SquarePen, ArrowUp, Undo2, ChevronDown, 
    ExternalLink, Settings2, Sparkles, ChevronRight, FileEdit, 
    Plus, ListTodo, MoreVertical, Search, Zap, Hexagon, Loader2,
    Layers, Box, X, ToggleLeft, ToggleRight, Download, History
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { useApi } from "@/hooks/use-api"
import SkillPickerModal from "../chat/SkillPickerModal"
import AppPickerModal from "../chat/AppPickerModal"

interface Skill {
    id: string;
    name: string;
    content: string;
}

interface OAuthConnection {
    id: string;
    provider: string;
}

interface Connector {
    id: string;
    name: string;
    icon_url?: string;
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
    capabilities: {
        web_search: boolean;
        web_fetch: boolean;
        conversation_search: boolean;
        self_improve?: boolean;
    };
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
        capabilities?: {
            web_search?: boolean;
            web_fetch?: boolean;
            conversation_search?: boolean;
            self_improve?: boolean;
        } | null;
    };
    isEditing?: boolean;
}

export function AgentBuilder({ initialData, isEditing = false }: AgentBuilderProps) {
    const router = useRouter()
    const api = useApi()
    
    // Form State
    const [formData, setFormData] = useState<FormData>({
        name: initialData?.name || "",
        description: initialData?.description || "",
        instructions: initialData?.instructions || "",
        model: initialData?.model || "claude-3-5-sonnet-20240620",
        app_connections: initialData?.app_connections || [],
        skills: initialData?.skills || [],
        timeout_seconds: initialData?.timeout_seconds || 60,
        self_improve: initialData?.capabilities?.self_improve ?? true,
        capabilities: {
            web_search: initialData?.capabilities?.web_search ?? false,
            web_fetch: initialData?.capabilities?.web_fetch ?? false,
            conversation_search: initialData?.capabilities?.conversation_search ?? false,
        }
    })
    
    // UI states
    const [skillPickerOpen, setSkillPickerOpen] = useState(false)
    const [appPickerOpen, setAppPickerOpen] = useState(false)
    
    const [msg, setMsg] = useState("")
    const [executing, setExecuting] = useState(false)
    const [executionResult, setExecutionResult] = useState<string | null>(null)
    const [skills, setSkills] = useState<Skill[]>([])
    const [availableConnectors, setAvailableConnectors] = useState<Connector[]>([])
    const [oauthConnections, setOauthConnections] = useState<OAuthConnection[]>([])
    const [models, setModels] = useState<{value: string, label: string}[]>([])
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        if (!api.orgId) return;

        const fetchData = async () => {
            setLoading(true)
            try {
                const [skillsData, connectorsData, oauthData, modelsData] = await Promise.all([
                    api.get<{ items: Skill[] }>('/api/skills'),
                    api.get<Connector[]>('/api/connectors/available').catch(() => []),
                    api.get<OAuthConnection[]>('/api/oauth-connections/').catch(() => []),
                    api.get<{value: string, label: string}[]>('/api/models/').catch(() => [])
                ])
                setSkills(skillsData.items || [])
                setAvailableConnectors(connectorsData || [])
                setOauthConnections(oauthData || [])
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
        if (!formData.name.trim() || !formData.instructions.trim()) {
            alert("Agent name and instructions are required.");
            return;
        }
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
                    capabilities: {
                        ...formData.capabilities,
                        self_improve: formData.self_improve
                    },
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

    const handleAttachSkill = async (skillId: string) => {
        setFormData(prev => ({
            ...prev,
            skills: prev.skills.includes(skillId) ? prev.skills : [...prev.skills, skillId]
        }))
    }

    const handleDetachSkill = async (skillId: string) => {
        setFormData(prev => ({
            ...prev,
            skills: prev.skills.filter(id => id !== skillId)
        }))
    }

    const handleAttachApp = async (connectionId: string) => {
        setFormData(prev => ({
            ...prev,
            app_connections: prev.app_connections.includes(connectionId) ? prev.app_connections : [...prev.app_connections, connectionId]
        }))
    }

    const handleDetachApp = async (connectionId: string) => {
        setFormData(prev => ({
            ...prev,
            app_connections: prev.app_connections.filter(id => id !== connectionId)
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

    const connectorName = (connection: OAuthConnection) => {
        const c = availableConnectors.find((ac) => ac.id === connection.provider);
        return c?.name || connection.provider;
    };

    const connectorIcon = (connection: OAuthConnection) => {
        const c = availableConnectors.find((ac) => ac.id === connection.provider);
        return c?.icon_url;
    };

    const attachedSkills = skills.filter(s => formData.skills.includes(s.id));
    const attachedConnections = oauthConnections.filter(oc => formData.app_connections.includes(oc.id));

    return (
        <div className="flex-1 flex w-full bg-background h-full overflow-hidden">
            <SkillPickerModal
                open={skillPickerOpen}
                onClose={() => setSkillPickerOpen(false)}
                agentId={initialData?.id || ""}
                attachedSkillIds={formData.skills}
                onAttach={handleAttachSkill}
                onDetach={handleDetachSkill}
            />
            <AppPickerModal
                open={appPickerOpen}
                onClose={() => setAppPickerOpen(false)}
                agentId={initialData?.id || ""}
                attachedConnectionIds={formData.app_connections}
                onAttach={handleAttachApp}
                onDetach={handleDetachApp}
            />

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
                            className="font-semibold text-sm bg-transparent border-none outline-none focus:ring-0 p-0 w-[300px]"
                            placeholder="Enter agent name"
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
                            className="flex-1 h-8 text-xs font-semibold bg-zinc-100 hover:bg-zinc-200 text-zinc-900 dark:text-zinc-100 disabled:opacity-50"
                            onClick={handleSave}
                            disabled={saving || !formData.name.trim() || !formData.instructions.trim()}
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

                    {/* Skills */}
                    <div className="space-y-3 pt-5 border-t">
                        <div className="flex justify-between items-center">
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                                <Layers className="h-4 w-4" />
                                Skills
                            </h3>
                            <div className="flex items-center gap-2 text-xs">
                                <span className="text-slate-500">
                                    {attachedSkills.length} attached
                                </span>
                                <button
                                    onClick={() => setSkillPickerOpen(true)}
                                    className="text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 px-2 py-1 rounded-md font-medium border border-transparent hover:border-border transition-all"
                                >
                                    + Skill
                                </button>
                            </div>
                        </div>

                        {attachedSkills.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {attachedSkills.map((skill) => (
                                    <span
                                        key={skill.id}
                                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
                                    >
                                        <Layers className="h-3 w-3" />
                                        {skill.name}
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDetachSkill(skill.id);
                                            }}
                                            className="ml-0.5 hover:text-destructive transition-colors"
                                            title="Remove skill"
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-slate-400 italic px-1">
                                No skills attached. Click + Skill to add one.
                            </p>
                        )}
                    </div>

                    {/* Apps / Tools */}
                    <div className="space-y-3 pt-5 border-t">
                        <div className="flex justify-between items-center">
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                                <Box className="h-4 w-4" />
                                Apps &amp; Tools
                            </h3>
                            <div className="flex items-center gap-2 text-xs">
                                <span className="text-slate-500">
                                    {attachedConnections.length} connected
                                </span>
                                <button
                                    onClick={() => setAppPickerOpen(true)}
                                    className="text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 px-2 py-1 rounded-md font-medium border border-transparent hover:border-border transition-all"
                                >
                                    + App
                                </button>
                            </div>
                        </div>

                        {attachedConnections.length > 0 ? (
                            <div className="flex flex-col gap-1.5">
                                {attachedConnections.map((conn) => {
                                    const icon = connectorIcon(conn);
                                    return (
                                        <div
                                            key={conn.id}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 shadow-sm"
                                        >
                                            <div className="w-6 h-6 rounded-md border border-border flex items-center justify-center overflow-hidden bg-white flex-shrink-0">
                                                {icon ? (
                                                    // eslint-disable-next-line @next/next/no-img-element
                                                    <img
                                                        src={icon}
                                                        alt={conn.provider}
                                                        className="w-4 h-4 object-contain"
                                                        onError={(e) => {
                                                            (e.target as HTMLImageElement).style.display = "none";
                                                        }}
                                                    />
                                                ) : (
                                                    <Box className="h-3.5 w-3.5 text-slate-400" />
                                                )}
                                            </div>
                                            <span className="flex-1 text-sm font-medium capitalize truncate text-foreground">
                                                {connectorName(conn)}
                                            </span>
                                            <button
                                                onClick={() => handleDetachApp(conn.id)}
                                                className="text-slate-400 hover:text-destructive transition-colors ml-auto"
                                                title="Remove app"
                                            >
                                                <X className="h-3.5 w-3.5" />
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-xs text-slate-400 italic px-1">
                                No apps connected. Click + App to give this agent tools.
                            </p>
                        )}
                    </div>

                    {/* Built-in Capabilities */}
                    <div className="space-y-2 pb-8 pt-5 border-t">
                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                            Built-in Capabilities
                        </h3>

                        {/* Web Search */}
                        <button
                            onClick={() => setFormData({
                                ...formData,
                                capabilities: { ...formData.capabilities, web_search: !formData.capabilities.web_search }
                            })}
                            className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                        >
                            <div className="flex items-center gap-2.5">
                                <Globe className="h-4 w-4 text-blue-500" />
                                <div>
                                    <p className="text-sm font-medium text-foreground">Web Search</p>
                                    <p className="text-xs text-slate-400">Search the internet for current info</p>
                                </div>
                            </div>
                            {formData.capabilities.web_search ? (
                                <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                            ) : (
                                <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                            )}
                        </button>

                        {/* Web Fetch */}
                        <button
                            onClick={() => setFormData({
                                ...formData,
                                capabilities: { ...formData.capabilities, web_fetch: !formData.capabilities.web_fetch }
                            })}
                            className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                        >
                            <div className="flex items-center gap-2.5">
                                <Download className="h-4 w-4 text-emerald-500" />
                                <div>
                                    <p className="text-sm font-medium text-foreground">Web Fetch</p>
                                    <p className="text-xs text-slate-400">Fetch and read content from URLs</p>
                                </div>
                            </div>
                            {formData.capabilities.web_fetch ? (
                                <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                            ) : (
                                <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                            )}
                        </button>

                        {/* Conversation Search */}
                        <button
                            onClick={() => setFormData({
                                ...formData,
                                capabilities: { ...formData.capabilities, conversation_search: !formData.capabilities.conversation_search }
                            })}
                            className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                        >
                            <div className="flex items-center gap-2.5">
                                <History className="h-4 w-4 text-violet-500" />
                                <div>
                                    <p className="text-sm font-medium text-foreground">Search Past Conversations</p>
                                    <p className="text-xs text-slate-400">Let agent recall from prior chats</p>
                                </div>
                            </div>
                            {formData.capabilities.conversation_search ? (
                                <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                            ) : (
                                <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

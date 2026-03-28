"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { 
    Share, MessageSquare, PanelRightClose, Activity, Image as ImageIcon, 
    Globe, Paperclip, SquarePen, ArrowUp, Undo2, ChevronDown, 
    ExternalLink, Settings2, Sparkles, ChevronRight, FileEdit, 
    Plus, ListTodo, MoreVertical, Search, Zap, Hexagon
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"

export function AgentBuilder() {
    const router = useRouter()
    const [msg, setMsg] = useState("")

    return (
        <div className="flex-1 flex w-full bg-background h-full overflow-hidden">
            {/* Left Main Area */}
            <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-zinc-950">
                {/* Top Nav */}
                <div className="h-14 border-b flex items-center justify-between px-4">
                    <div className="flex items-center gap-2">
                        <div className="w-7 h-7 bg-black dark:bg-white rounded-md flex items-center justify-center text-white dark:text-black">
                            <span className="font-bold text-xs">O</span>
                        </div>
                        <span className="font-semibold text-sm">Ready Maker</span>
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

                    <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-foreground mb-10">Hi Karan, how can I help you?</h1>

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
                                    className={`h-8 w-8 rounded-full transition-all duration-300 ${msg.length > 0 ? "bg-black text-white" : "bg-gradient-to-tr from-rose-300 to-indigo-400 text-white"}`}
                                >
                                    <ArrowUp className="w-4 h-4 text-white" />
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
                        <Button variant="secondary" className="flex-1 h-8 text-xs font-semibold bg-zinc-100 hover:bg-zinc-200 text-zinc-400">
                            Save <kbd className="ml-2 font-mono text-[9px] bg-white/50 px-1.5 py-0.5 rounded shadow-sm text-zinc-500">⌘ S</kbd>
                        </Button>
                        <Button variant="ghost" className="flex-1 h-8 text-xs font-semibold text-zinc-400 hover:bg-zinc-100">
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
                            <div className="p-3.5 border-b flex items-center justify-between hover:bg-zinc-50 cursor-pointer">
                                <div className="flex items-center gap-2 text-sm">
                                    <Sparkles className="w-4 h-4 text-orange-500 fill-orange-500/20" />
                                    <span className="font-semibold text-[13px]">
                                        Recommended <span className="text-muted-foreground font-medium ml-1">(Claude 4.6 Sonnet)</span>
                                    </span>
                                </div>
                                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                            </div>
                            <div className="p-3">
                                <textarea
                                    className="w-full outline-none resize-none text-[13px] min-h-[90px] bg-transparent placeholder:text-muted-foreground/60 focus:ring-0 font-medium"
                                    placeholder="Add instructions for the agent..."
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
                            <Switch defaultChecked />
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
                            {/* Jira Tool */}
                            <div className="flex items-center justify-between px-2 py-2 hover:bg-white rounded-lg group transition-colors cursor-pointer border border-transparent hover:border-border hover:shadow-sm">
                                <div className="flex items-center gap-3 text-[13px]">
                                    <div className="w-7 h-7 bg-[#E8F0FE] rounded flex items-center justify-center shrink-0">
                                        <Activity className="w-4 h-4 text-blue-600" />
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="font-semibold">Jira</span>
                                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button variant="ghost" size="icon" className="w-7 h-7 text-muted-foreground"><MoreVertical className="w-4 h-4" /></Button>
                                </div>
                            </div>
                            
                            {/* Web Search */}
                            <div className="flex items-center justify-between px-2 py-2 hover:bg-white rounded-lg transition-colors cursor-pointer border border-transparent hover:border-border hover:shadow-sm">
                                <div className="flex items-center gap-3 text-[13px]">
                                    <div className="w-7 h-7 bg-zinc-100 dark:bg-zinc-800 rounded flex items-center justify-center shrink-0 border shadow-sm">
                                        <Globe className="w-4 h-4 text-zinc-600 dark:text-zinc-300" />
                                    </div>
                                    <span className="font-semibold">Web Search</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Switch defaultChecked />
                                    <Button variant="ghost" size="icon" className="w-7 h-7 text-muted-foreground -mr-1"><MoreVertical className="w-4 h-4" /></Button>
                                </div>
                            </div>

                            {/* Image Generation */}
                            <div className="flex items-center justify-between px-2 py-2 hover:bg-white rounded-lg transition-colors cursor-pointer border border-transparent hover:border-border hover:shadow-sm">
                                <div className="flex items-center gap-3 text-[13px]">
                                    <div className="w-7 h-7 bg-zinc-100 dark:bg-zinc-800 rounded flex items-center justify-center shrink-0 border shadow-sm">
                                        <ImageIcon className="w-4 h-4 text-zinc-600 dark:text-zinc-300" />
                                    </div>
                                    <span className="font-semibold">Image Generation</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Switch defaultChecked />
                                    <Button variant="ghost" size="icon" className="w-7 h-7 text-muted-foreground -mr-1"><MoreVertical className="w-4 h-4" /></Button>
                                </div>
                            </div>

                            {/* App Discovery */}
                            <div className="flex items-center justify-between px-2 py-2 hover:bg-white rounded-lg transition-colors cursor-pointer border border-transparent hover:border-border hover:shadow-sm">
                                <div className="flex items-center gap-3 text-[13px]">
                                    <div className="w-7 h-7 bg-zinc-100 dark:bg-zinc-800 rounded flex items-center justify-center shrink-0 border shadow-sm">
                                        <Search className="w-4 h-4 text-zinc-600 dark:text-zinc-300" />
                                    </div>
                                    <span className="font-semibold">App Discovery</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Switch defaultChecked />
                                    <div className="w-7" />{/* alignment placeholder */}
                                </div>
                            </div>
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
                        <div className="flex items-center justify-between px-2">
                            <div className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
                                <Zap className="w-4 h-4 text-muted-foreground" /> AI Skill Editing & Creation
                            </div>
                            <Switch defaultChecked />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

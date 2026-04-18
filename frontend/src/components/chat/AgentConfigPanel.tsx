"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Settings,
  ExternalLink,
  MessageSquare,
  Globe,
  Download,
  Layers,
  Box,
  X,
  ToggleLeft,
  ToggleRight,
  History,
  Search,
} from "lucide-react";
import { useApi } from "@/hooks/use-api";
import SkillPickerModal from "./SkillPickerModal";
import AppPickerModal from "./AppPickerModal";

interface Skill {
  id: string;
  name: string;
  description: string | null;
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

interface Agent {
  id: string;
  name: string;
  instructions: string;
  model: string;
  skills: string[];
  app_connections: string[];
  capabilities?: {
    web_search?: boolean;
    web_fetch?: boolean;
    conversation_search?: boolean;
  } | null;
}

export default function AgentConfigPanel({ agentId }: any) {
  const api = useApi();
  const [activeTab, setActiveTab] = useState("builder");
  const [agent, setAgent] = useState<Agent | null>(null);

  // Resolved objects from IDs
  const [attachedSkills, setAttachedSkills] = useState<Skill[]>([]);
  const [attachedConnections, setAttachedConnections] = useState<OAuthConnection[]>([]);
  const [availableConnectors, setAvailableConnectors] = useState<Connector[]>([]);

  // Modal open state
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [appPickerOpen, setAppPickerOpen] = useState(false);

  // Capability toggle state (derived from agent.capabilities)
  const [webSearch, setWebSearch] = useState(false);
  const [webFetch, setWebFetch] = useState(false);
  const [convSearch, setConvSearch] = useState(false);

  const fetchAgent = useCallback(async () => {
    if (!api.orgId || !agentId) return;
    const data = await api.get<Agent>(`/api/agents/${agentId}`);
    setAgent(data);
    setWebSearch(data.capabilities?.web_search ?? false);
    setWebFetch(data.capabilities?.web_fetch ?? false);
    setConvSearch(data.capabilities?.conversation_search ?? false);

    // Resolve skills
    if (data.skills?.length) {
      const all = await api.get<{ items: Skill[] }>("/api/skills/").catch(() => ({ items: [] }));
      setAttachedSkills((all.items || []).filter((s) => data.skills.includes(s.id)));
    } else {
      setAttachedSkills([]);
    }

    // Load OAuth connections + connectors
    const [oauths, connectors] = await Promise.all([
      api.get<OAuthConnection[]>("/api/oauth-connections/").catch(() => []),
      api.get<Connector[]>("/api/connectors/available").catch(() => []),
    ]);
    setAvailableConnectors(connectors || []);
    const conns = (oauths || []).filter((oc) => data.app_connections.includes(oc.id));
    setAttachedConnections(conns);
  }, [api.orgId, agentId]);

  useEffect(() => {
    fetchAgent().catch(console.error);
  }, [fetchAgent]);

  // ── Capability toggle helpers ──────────────────────────────────────────────

  const saveCapabilities = async (patch: Partial<{ web_search: boolean; web_fetch: boolean; conversation_search: boolean }>) => {
    if (!agent) return;
    const updated = {
      web_search: webSearch,
      web_fetch: webFetch,
      conversation_search: convSearch,
      ...patch,
    };
    try {
      await api.put(`/api/agents/${agentId}`, { capabilities: updated });
    } catch (e) {
      console.error("Failed to save capabilities", e);
    }
  };

  const toggleWebSearch = async () => {
    const next = !webSearch;
    setWebSearch(next);
    await saveCapabilities({ web_search: next });
  };

  const toggleWebFetch = async () => {
    const next = !webFetch;
    setWebFetch(next);
    await saveCapabilities({ web_fetch: next });
  };

  const toggleConvSearch = async () => {
    const next = !convSearch;
    setConvSearch(next);
    await saveCapabilities({ conversation_search: next });
  };

  // ── Skills attach/detach ───────────────────────────────────────────────────

  const handleAttachSkill = async (skillId: string) => {
    await api.post(`/api/agents/${agentId}/skills`, { skill_id: skillId });
    await fetchAgent();
  };

  const handleDetachSkill = async (skillId: string) => {
    await api.delete(`/api/agents/${agentId}/skills/${skillId}`);
    await fetchAgent();
  };

  // ── Apps attach/detach ─────────────────────────────────────────────────────

  const handleAttachApp = async (connectionId: string) => {
    await api.post(`/api/agents/${agentId}/apps`, { connection_id: connectionId });
    await fetchAgent();
  };

  const handleDetachApp = async (connectionId: string) => {
    await api.delete(`/api/agents/${agentId}/apps/${connectionId}`);
    await fetchAgent();
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

  const connectorName = (connection: OAuthConnection) => {
    const c = availableConnectors.find((ac) => ac.id === connection.provider);
    return c?.name || connection.provider;
  };

  const connectorIcon = (connection: OAuthConnection) => {
    const c = availableConnectors.find((ac) => ac.id === connection.provider);
    return c?.icon_url;
  };

  return (
    <>
      <SkillPickerModal
        open={skillPickerOpen}
        onClose={() => setSkillPickerOpen(false)}
        agentId={agentId}
        attachedSkillIds={agent?.skills || []}
        onAttach={handleAttachSkill}
        onDetach={handleDetachSkill}
      />
      <AppPickerModal
        open={appPickerOpen}
        onClose={() => setAppPickerOpen(false)}
        agentId={agentId}
        attachedConnectionIds={agent?.app_connections || []}
        onAttach={handleAttachApp}
        onDetach={handleDetachApp}
      />

      <div className="flex flex-col h-full overflow-y-auto w-full border-l border-border bg-slate-50/30 dark:bg-slate-900/30">
        {/* Header Tabs */}
        <div className="flex px-4 pt-2 border-b border-border sticky top-0 bg-background z-10 gap-4">
          {["builder", "chat details", "settings"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-primary text-slate-900 dark:text-slate-100"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {tab}
            </button>
          ))}
          <div className="ml-auto pb-2 flex gap-2">
            <button className="text-sm font-medium text-slate-500 hover:text-slate-900 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-md">
              Save
            </button>
          </div>
        </div>

        <div className="p-4 space-y-6">
          {activeTab === "builder" && (
            <>
              {/* Agent Preferences */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold flex justify-between items-center text-slate-700 dark:text-slate-300 group cursor-pointer">
                  <div className="flex items-center gap-1">
                    <span>Agent Preferences</span>
                    <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                  </div>
                  <span className="text-xs font-normal text-slate-500 hover:text-slate-900 flex items-center gap-1">
                    Advanced <Settings className="h-3 w-3" />
                  </span>
                </h3>
                <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between shadow-sm cursor-pointer">
                  <div className="flex items-center gap-2">
                    <span className="text-orange-500">✷</span>
                    <span className="text-sm font-medium">
                      Model{" "}
                      <span className="text-slate-500 font-normal">
                        ({agent?.model || "Loading..."})
                      </span>
                    </span>
                  </div>
                  <span className="text-slate-400">&gt;</span>
                </div>
                <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
                  <div className="text-sm font-medium mb-1"># {agent?.name || "Agent Identity"}</div>
                  <div className="text-xs text-slate-500 line-clamp-4 whitespace-pre-wrap">
                    {agent?.instructions || "Loading agent instructions..."}
                  </div>
                </div>
              </div>

              <hr className="border-border" />

              {/* Skills */}
              <div className="space-y-3">
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
                          onClick={() => handleDetachSkill(skill.id)}
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

              <hr className="border-border" />

              {/* Apps / Tools */}
              <div className="space-y-3">
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
                          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm"
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
                          <span className="flex-1 text-sm font-medium capitalize truncate">
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

              <hr className="border-border" />

              {/* Built-in Capabilities */}
              <div className="space-y-2 pb-8">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
                  Built-in Capabilities
                </h3>

                {/* Web Search */}
                <button
                  onClick={toggleWebSearch}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <Globe className="h-4 w-4 text-blue-500" />
                    <div>
                      <p className="text-sm font-medium">Web Search</p>
                      <p className="text-xs text-slate-400">Search the internet for current info</p>
                    </div>
                  </div>
                  {webSearch ? (
                    <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                  )}
                </button>

                {/* Web Fetch */}
                <button
                  onClick={toggleWebFetch}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <Download className="h-4 w-4 text-emerald-500" />
                    <div>
                      <p className="text-sm font-medium">Web Fetch</p>
                      <p className="text-xs text-slate-400">Fetch and read content from URLs</p>
                    </div>
                  </div>
                  {webFetch ? (
                    <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                  )}
                </button>

                {/* Conversation Search */}
                <button
                  onClick={toggleConvSearch}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-slate-300 transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <History className="h-4 w-4 text-violet-500" />
                    <div>
                      <p className="text-sm font-medium">Search Past Conversations</p>
                      <p className="text-xs text-slate-400">Let agent recall from prior chats</p>
                    </div>
                  </div>
                  {convSearch ? (
                    <ToggleRight className="h-5 w-5 text-primary flex-shrink-0" />
                  ) : (
                    <ToggleLeft className="h-5 w-5 text-slate-300 flex-shrink-0" />
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

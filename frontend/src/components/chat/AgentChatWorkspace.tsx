"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import ChatSidebar from "./ChatSidebar";
import ChatPanel from "./ChatPanel";
import AgentConfigPanel from "./AgentConfigPanel";
import { useApi } from "@/hooks/use-api";
import { Button } from "@/components/ui/button";

export default function AgentChatWorkspace({ agentId }: { agentId: string }) {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [agentName, setAgentName] = useState<string>("Agent");
  const [isChatSidebarOpen, setIsChatSidebarOpen] = useState(true);
  const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(true);
  const api = useApi();

  useEffect(() => {
    if (!agentId || !api.orgId) return;
    api.get<{ name: string }>(`/api/agents/${agentId}`)
      .then((data) => setAgentName(data.name || "Agent"))
      .catch(() => setAgentName("Agent"));
  }, [agentId, api.orgId]);

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      {/* Left Sidebar: Chat History & Files */}
      <div
        className={`shrink-0 bg-background flex flex-col border-r border-border transition-all duration-200 overflow-hidden ${
          isChatSidebarOpen ? "w-[260px]" : "w-0"
        }`}
      >
        <ChatSidebar
          agentId={agentId}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
        />
      </div>

      {/* Center Chat Panel: Active conversation */}
      <div className="flex-1 min-w-0 flex flex-col bg-slate-50/50 dark:bg-slate-950/50 relative">
        {/* Toggle buttons row */}
        <div className="absolute top-2 left-2 z-10 flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-full bg-background border border-border shadow-sm hover:bg-accent"
            onClick={() => setIsChatSidebarOpen((v) => !v)}
            title={isChatSidebarOpen ? "Collapse chat history" : "Expand chat history"}
          >
            {isChatSidebarOpen ? (
              <ChevronLeft className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </div>

        <div className="absolute top-2 right-2 z-10 flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 rounded-full bg-background border border-border shadow-sm hover:bg-accent"
            onClick={() => setIsConfigPanelOpen((v) => !v)}
            title={isConfigPanelOpen ? "Collapse config panel" : "Expand config panel"}
          >
            {isConfigPanelOpen ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        <ChatPanel
          agentId={agentId}
          agentName={agentName}
          sessionId={activeSessionId}
          onSessionCreated={setActiveSessionId}
        />
      </div>

      {/* Right Config Panel: Builder, Settings, Trigger */}
      <div
        className={`shrink-0 bg-background flex flex-col pt-2 border-l border-border transition-all duration-200 overflow-hidden ${
          isConfigPanelOpen ? "w-[340px]" : "w-0"
        }`}
      >
        <AgentConfigPanel agentId={agentId} />
      </div>
    </div>
  );
}

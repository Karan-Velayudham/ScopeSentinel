"use client";

import { useState } from "react";
import ChatSidebar from "./ChatSidebar";
import ChatPanel from "./ChatPanel";
import AgentConfigPanel from "./AgentConfigPanel";

export default function AgentChatWorkspace({ agentId }: { agentId: string }) {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      {/* Left Sidebar: Navigation & History & Files */}
      <div className="w-[280px] shrink-0 bg-background flex flex-col">
        <ChatSidebar 
          agentId={agentId} 
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
        />
      </div>
      
      {/* Center Chat Panel: Active conversation */}
      <div className="flex-1 min-w-[400px] border-l border-r border-border flex flex-col bg-slate-50/50 dark:bg-slate-950/50 relative">
        <ChatPanel 
          agentId={agentId} 
          sessionId={activeSessionId} 
          onSessionCreated={setActiveSessionId}
        />
      </div>

      {/* Right Config Panel: Builder, Settings, Trigger */}
      <div className="w-[350px] shrink-0 bg-background flex flex-col pt-2">
        <AgentConfigPanel agentId={agentId} />
      </div>
    </div>
  );
}

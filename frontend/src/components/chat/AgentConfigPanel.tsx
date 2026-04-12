"use client";

import { useState, useEffect } from "react";
import { Settings, Workflow, Blocks, ExternalLink, MessageSquare, Zap } from "lucide-react";
import { useApi } from "@/hooks/use-api";

export default function AgentConfigPanel({ agentId }: any) {
  const api = useApi();
  const [activeTab, setActiveTab] = useState("builder");
  const [agent, setAgent] = useState<any>(null);

  useEffect(() => {
    if (api.orgId && agentId) {
      api.get<any>(`/api/agents/${agentId}`).then(data => {
        setAgent(data);
      }).catch(console.error);
    }
  }, [api.orgId, agentId]);

  return (
    <div className="flex flex-col h-full overflow-y-auto w-full border-l border-border bg-slate-50/30 dark:bg-slate-900/30">
      
      {/* Header Tabs */}
      <div className="flex px-4 pt-2 border-b border-border sticky top-0 bg-background z-10 gap-4">
        {['builder', 'chat details', 'settings'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${activeTab === tab ? 'border-primary text-slate-900 dark:text-slate-100' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          >
            {tab}
          </button>
        ))}
        <div className="ml-auto pb-2 flex gap-2">
          <button className="text-sm font-medium text-slate-500 hover:text-slate-900 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-md">Save</button>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {activeTab === 'builder' && (
          <>
            {/* Setup Checklist */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold flex justify-between items-center text-slate-700 dark:text-slate-300">
                <span>Setup Checklist</span>
                <span className="text-[10px] text-slate-400 font-normal">Dismiss x</span>
              </h3>
              <div className="flex flex-col gap-2">
                <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between shadow-sm cursor-pointer hover:border-slate-300 transition-colors">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-medium">Connect to Slack</span>
                  </div>
                  <div className="h-4 w-4 rounded-full border border-slate-300"></div>
                </div>
                <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between shadow-sm cursor-pointer hover:border-slate-300 transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-medium text-sm">#</span>
                    <span className="text-sm font-medium">Add agent to a channel</span>
                  </div>
                  <div className="h-4 w-4 rounded-full border border-slate-300"></div>
                </div>
              </div>
            </div>

            <hr className="border-border" />

            {/* Agent Preferences */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold flex justify-between items-center text-slate-700 dark:text-slate-300 group cursor-pointer">
                <div className="flex items-center gap-1">
                  <span>Agent Preferences</span>
                  <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                </div>
                <span className="text-xs font-normal text-slate-500 hover:text-slate-900 flex items-center gap-1">Advanced <Settings className="h-3 w-3"/></span>
              </h3>
              <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between shadow-sm cursor-pointer">
                <div className="flex items-center gap-2">
                  <span className="text-orange-500">✷</span>
                  <span className="text-sm font-medium">Model <span className="text-slate-500 font-normal">({agent?.model || 'Loading...'})</span></span>
                </div>
                <span className="text-slate-400">&gt;</span>
              </div>
              <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm">
                <div className="text-sm font-medium mb-1"># {agent?.name || 'Agent Identity'}</div>
                <div className="text-xs text-slate-500 line-clamp-4 whitespace-pre-wrap">
                  {agent?.instructions || 'Loading agent instructions...'}
                </div>
              </div>
            </div>

            <hr className="border-border" />

            {/* Triggers */}
            <div className="space-y-3">
              <div className="flex justify-between items-center group cursor-pointer">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  Triggers
                </h3>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">AI Managed: ON</span>
                  <button className="text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 px-2 py-1 rounded-md font-medium border border-transparent hover:border-border transition-all">+ Trigger</button>
                </div>
              </div>
            </div>

            <hr className="border-border" />

            {/* Tools */}
            <div className="space-y-3">
              <div className="flex justify-between items-center group cursor-pointer">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  Tools <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
                </h3>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">AI Discovery: OFF</span>
                  <button className="text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 px-2 py-1 rounded-md font-medium border border-transparent hover:border-border transition-all">+ App</button>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-600 font-medium pb-2">
                <div className="flex -space-x-1">
                  <div className="h-6 w-6 rounded bg-blue-500 shrink-0"></div>
                  <div className="h-6 w-6 rounded bg-green-500 shrink-0"></div>
                  <div className="h-6 w-6 rounded bg-blue-600 shrink-0"></div>
                </div>
                <span className="ml-2 hover:underline cursor-pointer">{(agent?.app_connections?.length) || 0} Apps Connected &gt;</span>
              </div>
              <div className="text-sm flex justify-between items-center text-slate-600 py-1">
                <span className="flex items-center gap-2"><Workflow className="h-4 w-4"/> Web Search <span className="text-slate-400">· ON</span></span>
                <span className="text-slate-400">⋮</span>
              </div>
            </div>

            <hr className="border-border" />

            {/* Skills */}
            <div className="space-y-3 pb-8">
              <div className="flex justify-between items-center group cursor-pointer">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  Skills
                </h3>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500">{(agent?.skills?.length) || 0} Attached</span>
                  <button className="text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 px-2 py-1 rounded-md font-medium border border-transparent hover:border-border transition-all">+ Skill</button>
                </div>
              </div>
            </div>
            
          </>
        )}
      </div>
    </div>
  );
}

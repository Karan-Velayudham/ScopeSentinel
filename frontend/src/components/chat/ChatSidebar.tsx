"use client";

import { useState, useEffect } from "react";
import { Plus, Search, FileText, Download, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";

export default function ChatSidebar({ agentId, activeSessionId, onSelectSession }: any) {
  const api = useApi();
  const [recentChats, setRecentChats] = useState<any[]>([]);
  const [generatedFiles, setGeneratedFiles] = useState<any[]>([]);

  useEffect(() => {
    if (api.orgId) {
      api.get<{ items: any[] }>('/api/chats').then(data => {
        const agentChats = (data.items || []).filter(c => c.agent_id === agentId);
        setRecentChats(agentChats);
      }).catch(console.error);
    }
  }, [api.orgId, agentId, activeSessionId]);

  useEffect(() => {
    if (activeSessionId && api.orgId) {
      api.get<any[]>(`/api/chats/${activeSessionId}/files`).then(data => {
        setGeneratedFiles(data || []);
      }).catch(console.error);
    } else {
      setGeneratedFiles([]);
    }
  }, [activeSessionId, api.orgId]);

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/files/${fileId}/download`, {
        headers: { 'X-ScopeSentinel-Org-ID': api.orgId || '' }
      });
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto w-full p-4 gap-6">
      <Button variant="outline" className="w-full justify-start gap-2 h-10 px-4 mt-2 font-medium" onClick={() => onSelectSession(null)}>
        <Plus className="h-4 w-4" />
        New Chat
      </Button>
      
      {/* Files Section */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold flex items-center gap-2 px-1 text-slate-700 dark:text-slate-300">
          <FileText className="h-4 w-4" />
          Files Generated
        </h3>
        {generatedFiles.length > 0 ? (
          <div className="flex flex-col gap-1">
            {generatedFiles.map(file => (
              <div key={file.id} className="text-sm px-3 py-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer flex items-center justify-between group">
                <span className="truncate max-w-[150px]">{file.filename || file.name}</span>
                <Download 
                  className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-slate-900" 
                  onClick={() => handleDownload(file.id, file.filename || file.name)} 
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-slate-500 px-2 italic">No files yet</div>
        )}
      </div>

      {/* Recents Section */}
      <div className="space-y-3 flex-1">
        <h3 className="text-sm font-semibold px-1 text-slate-700 dark:text-slate-300">Recents</h3>
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search" className="pl-9 bg-transparent" />
        </div>
        
        <div className="flex flex-col gap-1 mt-4">
          {recentChats.map(chat => (
            <div 
              key={chat.id} 
              onClick={() => onSelectSession(chat.id)}
              className={`text-sm px-3 py-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer flex items-center gap-2 ${activeSessionId === chat.id ? 'bg-slate-100 dark:bg-slate-800 font-medium' : 'text-slate-600 dark:text-slate-400'}`}
            >
              <MessageSquare className="h-4 w-4 shrink-0" />
              <span className="truncate">{chat.title}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Paperclip, Workflow } from "lucide-react";
import { Button } from "@/components/ui/button";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useApi } from "@/hooks/use-api";

export default function ChatPanel({ agentId, sessionId, onSessionCreated }: any) {
  const api = useApi();
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId && api.orgId) {
      fetchMessages(sessionId);
    } else {
      setMessages([]);
    }
  }, [sessionId, api.orgId]);

  const fetchMessages = async (chatId: string) => {
    try {
      const data = await api.get<{ items: any[] }>(`/api/chats/${chatId}/messages`);
      setMessages(data.items || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!input.trim() || loading || !api.orgId) return;
    const currentInput = input;
    setInput("");
    
    // Add user message optimistically
    const tempMessage = { id: Date.now().toString(), role: "USER", content: currentInput, message_type: "TEXT" };
    setMessages(prev => [...prev, tempMessage]);
    setLoading(true);

    try {
      let chatId = sessionId;
      // create session first if needed
      if (!chatId) {
        const chat = await api.post<any>('/api/chats', { agent_id: agentId, title: currentInput.substring(0, 30) });
        chatId = chat.id;
        onSessionCreated(chatId);
      }

      await api.post<any>(`/api/chats/${chatId}/messages`, { content: currentInput });
      await fetchMessages(chatId);
    } catch (e) {
      console.error(e);
      // Remove optimistic message if failure
      setMessages(prev => prev.filter(m => m.id !== tempMessage.id));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col max-w-4xl mx-auto w-full">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex flex-col ${(msg.role === 'USER' || msg.role === 'user') ? 'items-end' : 'items-start'} max-w-[85%]`}>
            {(msg.role === 'AGENT' || msg.role === 'agent') && (
              <span className="text-xs font-semibold text-slate-500 mb-1 ml-1">ScopeSentinel Agent</span>
            )}
            <div 
              className={`p-4 rounded-xl shadow-sm ${(msg.role === 'USER' || msg.role === 'user') ? 'bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-br-none' : 'bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-bl-none w-full prose prose-sm dark:prose-invert prose-slate'}`}
            >
              {(msg.role === 'USER' || msg.role === 'user') ? (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              ) : (
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
            {(msg.role === 'USER' || msg.role === 'user') && (
               <span className="text-xs font-medium text-slate-400 mt-1 mr-1">You</span>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex flex-col items-start max-w-[85%]">
            <span className="text-xs font-semibold text-slate-500 mb-1 ml-1">ScopeSentinel Agent generates...</span>
            <div className="p-4 rounded-xl shadow-sm bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-bl-none flex gap-1">
              <div className="h-2 w-2 bg-slate-300 rounded-full animate-bounce delay-100"></div>
              <div className="h-2 w-2 bg-slate-300 rounded-full animate-bounce delay-200"></div>
              <div className="h-2 w-2 bg-slate-300 rounded-full animate-bounce delay-300"></div>
            </div>
          </div>
        )}
        <div ref={scrollRef} className="h-4" />
      </div>

      <div className="p-4 bg-background/80 backdrop-blur-sm border-t border-border mt-auto">
        <div className="max-w-4xl mx-auto flex flex-col gap-2 relative shadow-sm border border-border rounded-xl bg-background overflow-hidden p-3 pt-4 focus-within:ring-1 focus-within:ring-ring">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={loading ? "Agent is typing..." : "Send a message to your agent..."}
            className="w-full resize-none border-none outline-none bg-transparent min-h-[60px] max-h-[200px]"
            rows={2}
          />
          <div className="flex justify-between items-center mt-2">
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900">
                <Paperclip className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" className="h-8 px-2 text-slate-500 hover:text-slate-900 text-xs gap-1 font-medium">
                <Workflow className="h-4 w-4" />
                Skill
              </Button>
            </div>
            <Button size="icon" className="h-8 w-8 rounded-full" onClick={handleSend} disabled={!input.trim() || loading}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="text-center mt-2 text-[10px] text-slate-400">
          Agent output may contain hallucinated or generated structures.
        </div>
      </div>
    </>
  );
}

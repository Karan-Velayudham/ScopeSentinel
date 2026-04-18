"use client";

import { useState, useEffect } from "react";
import { X, Search, Check, Link as LinkIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";

interface Connector {
  id: string;
  name: string;
  description: string;
  icon_url?: string;
  auth_type: string;
}

interface OAuthConnection {
  id: string;
  provider: string;
}

interface AppPickerModalProps {
  open: boolean;
  onClose: () => void;
  agentId: string;
  attachedConnectionIds: string[];
  onAttach: (connectionId: string) => Promise<void>;
  onDetach: (connectionId: string) => Promise<void>;
}

export default function AppPickerModal({
  open,
  onClose,
  agentId,
  attachedConnectionIds,
  onAttach,
  onDetach,
}: AppPickerModalProps) {
  const api = useApi();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [oauthConnections, setOauthConnections] = useState<OAuthConnection[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !api.orgId) return;
    setLoading(true);
    Promise.all([
      api.get<Connector[]>("/api/connectors/available"),
      api.get<OAuthConnection[]>("/api/oauth-connections/"),
    ])
      .then(([avail, oauth]) => {
        setConnectors(avail || []);
        setOauthConnections(oauth || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [open, api.orgId]);

  if (!open) return null;

  const filtered = connectors.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.description.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = async (connector: Connector) => {
    // Find the OAuth connection id for this connector
    const oauthConn = oauthConnections.find((oc) => oc.provider === connector.id);
    if (!oauthConn) {
      // Not connected at all — redirect to integrations
      window.open("/integrations", "_blank");
      return;
    }
    const isAttached = attachedConnectionIds.includes(oauthConn.id);
    setPending(connector.id);
    try {
      if (isAttached) {
        await onDetach(oauthConn.id);
      } else {
        await onAttach(oauthConn.id);
      }
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 bg-background border rounded-xl shadow-2xl w-full max-w-md mx-4 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 pb-3 border-b border-border">
          <div>
            <h2 className="text-base font-semibold">Connect Apps</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Attach connected apps to give this agent access to tools
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search apps..."
              className="pl-9 h-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* App list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="py-10 text-center text-sm text-muted-foreground">Loading apps...</div>
          ) : filtered.length === 0 ? (
            <div className="py-10 flex flex-col items-center gap-2 text-sm text-muted-foreground">
              <p>{search ? "No apps match your search." : "No apps available."}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open("/integrations", "_blank")}
              >
                Connect an app
              </Button>
            </div>
          ) : (
            filtered.map((connector) => {
              const oauthConn = oauthConnections.find((oc) => oc.provider === connector.id);
              const isConnectedToOrg = !!oauthConn;
              const isAttachedToAgent = oauthConn
                ? attachedConnectionIds.includes(oauthConn.id)
                : false;
              const isPending = pending === connector.id;

              return (
                <button
                  key={connector.id}
                  onClick={() => toggle(connector)}
                  disabled={isPending}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors border-b border-border last:border-0 ${
                    isPending ? "opacity-60" : ""
                  }`}
                >
                  {/* Icon */}
                  <div className="flex-shrink-0 w-9 h-9 rounded-lg border border-border flex items-center justify-center bg-white overflow-hidden">
                    {connector.icon_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={connector.icon_url}
                        alt={connector.name}
                        className="w-6 h-6 object-contain"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <LinkIcon className="h-4 w-4 text-slate-400" />
                    )}
                  </div>

                  {/* Name + status */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm font-medium truncate">{connector.name}</p>
                      {!isConnectedToOrg && (
                        <span className="text-[10px] text-slate-400 font-normal">Not connected</span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{connector.description}</p>
                  </div>

                  {/* Attached state */}
                  <div
                    className={`flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isAttachedToAgent
                        ? "bg-primary border-primary"
                        : isConnectedToOrg
                        ? "border-slate-300 dark:border-slate-600"
                        : "border-dashed border-slate-300 opacity-50"
                    }`}
                  >
                    {isAttachedToAgent && <Check className="h-3 w-3 text-white" />}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground"
            onClick={() => window.open("/integrations", "_blank")}
          >
            Manage apps →
          </Button>
          <Button variant="outline" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}

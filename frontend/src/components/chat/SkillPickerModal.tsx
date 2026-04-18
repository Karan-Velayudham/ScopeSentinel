"use client";

import { useState, useEffect } from "react";
import { X, Search, Check, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";

interface Skill {
  id: string;
  name: string;
  description: string | null;
  instructions: string;
}

interface SkillPickerModalProps {
  open: boolean;
  onClose: () => void;
  agentId: string;
  attachedSkillIds: string[];
  onAttach: (skillId: string) => Promise<void>;
  onDetach: (skillId: string) => Promise<void>;
}

export default function SkillPickerModal({
  open,
  onClose,
  agentId,
  attachedSkillIds,
  onAttach,
  onDetach,
}: SkillPickerModalProps) {
  const api = useApi();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !api.orgId) return;
    setLoading(true);
    api
      .get<{ items: Skill[] }>("/api/skills/")
      .then((data) => setSkills(data.items || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [open, api.orgId]);

  if (!open) return null;

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      (s.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const toggle = async (skill: Skill) => {
    const isAttached = attachedSkillIds.includes(skill.id);
    setPending(skill.id);
    try {
      if (isAttached) {
        await onDetach(skill.id);
      } else {
        await onAttach(skill.id);
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
            <h2 className="text-base font-semibold">Add Skills</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Select skills to attach to this agent
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search skills..."
              className="pl-9 h-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Skill list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Loading skills...
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              {search ? "No skills match your search." : "No skills found. Create one first."}
            </div>
          ) : (
            filtered.map((skill) => {
              const isAttached = attachedSkillIds.includes(skill.id);
              const isPending = pending === skill.id;
              return (
                <button
                  key={skill.id}
                  onClick={() => toggle(skill)}
                  disabled={isPending}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/50 transition-colors border-b border-border last:border-0 ${
                    isPending ? "opacity-60" : ""
                  }`}
                >
                  <div className="flex-shrink-0 w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center">
                    <Layers className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{skill.name}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {skill.description ||
                        skill.instructions.slice(0, 60) +
                          (skill.instructions.length > 60 ? "..." : "")}
                    </p>
                  </div>
                  <div
                    className={`flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                      isAttached
                        ? "bg-primary border-primary"
                        : "border-slate-300 dark:border-slate-600"
                    }`}
                  >
                    {isAttached && <Check className="h-3 w-3 text-white" />}
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <Button variant="outline" className="w-full" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}

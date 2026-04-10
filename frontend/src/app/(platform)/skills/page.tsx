"use client"

import { useState, useEffect, useCallback } from "react"
import { Layers, Plus, Search, Filter, MoreHorizontal, Pencil, Trash2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApi } from "@/hooks/use-api"

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} hour${hrs === 1 ? "" : "s"} ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`
  const weeks = Math.floor(days / 7)
  if (weeks < 5) return `${weeks} week${weeks === 1 ? "" : "s"} ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`
  return `${Math.floor(months / 12)} year${Math.floor(months / 12) === 1 ? "" : "s"} ago`
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface Skill {
  id: string
  org_id: string
  name: string
  description: string | null
  instructions: string
  version: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// ─── Create Skill Modal ────────────────────────────────────────────────────────

interface CreateSkillModalProps {
  open: boolean
  onClose: () => void
  onCreated: (skill: Skill) => void
  editingSkill?: Skill | null
}

function CreateSkillModal({ open, onClose, onCreated, editingSkill }: CreateSkillModalProps) {
  const api = useApi()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [instructions, setInstructions] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isEditing = !!editingSkill

  useEffect(() => {
    if (editingSkill) {
      setName(editingSkill.name)
      setDescription(editingSkill.description ?? "")
      setInstructions(editingSkill.instructions)
    } else {
      setName("")
      setDescription("")
      setInstructions("")
    }
    setError(null)
  }, [editingSkill, open])

  const handleSubmit = async () => {
    if (!name.trim() || !instructions.trim()) {
      setError("Name and instructions are required.")
      return
    }
    setSaving(true)
    setError(null)
    try {
      let result: Skill
      if (isEditing && editingSkill) {
        result = await api.patch<Skill>(`/api/skills/${editingSkill.id}`, {
          name: name.trim(),
          description: description.trim() || null,
          instructions: instructions.trim(),
        })
      } else {
        result = await api.post<Skill>("/api/skills/", {
          name: name.trim(),
          description: description.trim() || null,
          instructions: instructions.trim(),
        })
      }
      onCreated(result)
      onClose()
    } catch (e: any) {
      setError(e?.message || "Failed to save skill.")
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 bg-background border rounded-xl shadow-2xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight">
              {isEditing ? "Edit Skill" : "Add a Skill"}
            </h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Write a name, description, and instructions for the skill.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded border hover:bg-muted transition-colors ml-4 flex-shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 pb-2 flex flex-col gap-5">
          {/* Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold">Name</label>
            <Input
              id="skill-name"
              placeholder="Enter a name for the skill..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={saving}
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold">Description</label>
            <Input
              id="skill-description"
              placeholder="Enter a description for the skill..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={saving}
            />
          </div>

          {/* Instructions */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold">Instructions</label>
            <textarea
              id="skill-instructions"
              placeholder="Enter instructions for the skill..."
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              disabled={saving}
              rows={12}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 pt-4">
          <Button
            id="skill-submit-btn"
            className="w-full bg-foreground text-background hover:bg-foreground/90 font-semibold py-3 h-auto"
            onClick={handleSubmit}
            disabled={saving}
          >
            {saving ? "Saving..." : isEditing ? "Save Changes" : "Create"}
          </Button>
        </div>
      </div>
    </div>
  )
}

// ─── Skills Page ──────────────────────────────────────────────────────────────

export default function SkillsPage() {
  const api = useApi()
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [modalOpen, setModalOpen] = useState(false)
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)

  const fetchSkills = useCallback(async () => {
    if (!api.orgId) return
    try {
      const data = await api.get<{ items: Skill[] }>("/api/skills/")
      setSkills(data.items || [])
    } catch (e) {
      console.error("Failed to fetch skills", e)
    } finally {
      setLoading(false)
    }
  }, [api.orgId])

  useEffect(() => {
    if (api.orgId) fetchSkills()
  }, [api.orgId])

  // Close menu on outside click
  useEffect(() => {
    const handler = () => setOpenMenuId(null)
    document.addEventListener("click", handler)
    return () => document.removeEventListener("click", handler)
  }, [])

  const handleCreated = (skill: Skill) => {
    if (editingSkill) {
      setSkills((prev) => prev.map((s) => (s.id === skill.id ? skill : s)))
    } else {
      setSkills((prev) => [skill, ...prev])
    }
    setEditingSkill(null)
  }

  const handleEdit = (skill: Skill) => {
    setEditingSkill(skill)
    setModalOpen(true)
    setOpenMenuId(null)
  }

  const handleDelete = async (skill: Skill) => {
    setOpenMenuId(null)
    if (!confirm(`Delete skill "${skill.name}"?`)) return
    try {
      await api.delete(`/api/skills/${skill.id}`)
      setSkills((prev) => prev.filter((s) => s.id !== skill.id))
    } catch {
      alert("Failed to delete skill.")
    }
  }

  const openCreate = () => {
    setEditingSkill(null)
    setModalOpen(true)
  }

  const filteredSkills = skills.filter((s) => {
    const q = searchQuery.toLowerCase()
    return (
      s.name.toLowerCase().includes(q) ||
      (s.description ?? "").toLowerCase().includes(q) ||
      s.instructions.toLowerCase().includes(q)
    )
  })

  return (
    <>
      <CreateSkillModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditingSkill(null) }}
        onCreated={handleCreated}
        editingSkill={editingSkill}
      />

      <div className="flex flex-col gap-6">
        {/* Page Header */}
        <div className="flex items-center justify-between border-b pb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Skills</h1>
            <p className="text-muted-foreground mt-1">
              Reusable instruction sets that shape how agents and workflows behave.
            </p>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-lg">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="skills-search"
              placeholder="Search skills"
              className="pl-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="outline" className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </Button>
          <Button
            id="create-skill-btn"
            className="flex items-center gap-2"
            onClick={openCreate}
          >
            Create Skill
          </Button>
        </div>

        {/* Table */}
        {loading ? (
          <div className="py-12 text-center text-muted-foreground">Loading skills...</div>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-[1fr_160px_140px_40px] px-4 py-3 bg-muted/30 border-b text-xs font-medium text-muted-foreground uppercase tracking-wide">
              <span>Skills • {filteredSkills.length}</span>
              <span>App(s)</span>
              <span>Last Edited</span>
              <span />
            </div>

            {/* Rows */}
            {filteredSkills.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="p-4 rounded-full bg-muted/30">
                  <Layers className="h-8 w-8 text-muted-foreground opacity-40" />
                </div>
                <p className="font-medium">No skills found</p>
                <p className="text-sm text-muted-foreground">
                  {searchQuery ? "Try a different search term." : "Create your first skill to get started."}
                </p>
                {!searchQuery && (
                  <Button variant="outline" onClick={openCreate} className="mt-1">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Skill
                  </Button>
                )}
              </div>
            ) : (
              filteredSkills.map((skill, idx) => (
                <div
                  key={skill.id}
                  className={`grid grid-cols-[1fr_160px_140px_40px] px-4 py-4 items-center hover:bg-muted/20 transition-colors ${idx < filteredSkills.length - 1 ? "border-b" : ""}`}
                >
                  {/* Name + Description */}
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center">
                      <Layers className="h-4 w-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-sm truncate">{skill.name}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-lg">
                        {skill.description
                          ? skill.description
                          : skill.instructions.slice(0, 80) + (skill.instructions.length > 80 ? "..." : "")}
                      </p>
                    </div>
                  </div>

                  {/* App(s) — placeholder */}
                  <span className="text-sm text-muted-foreground">—</span>

                  {/* Last Edited */}
                  <span className="text-sm text-muted-foreground">
                    {timeAgo(skill.updated_at)}
                  </span>

                  {/* Actions menu */}
                  <div className="relative flex justify-end">
                    <button
                      id={`skill-menu-${skill.id}`}
                      className="p-1 rounded hover:bg-muted transition-colors"
                      onClick={(e) => {
                        e.stopPropagation()
                        setOpenMenuId(openMenuId === skill.id ? null : skill.id)
                      }}
                    >
                      <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                    </button>

                    {openMenuId === skill.id && (
                      <div
                        className="absolute right-0 top-7 z-20 w-36 rounded-md border bg-popover shadow-md py-1"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-muted transition-colors"
                          onClick={() => handleEdit(skill)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit
                        </button>
                        <button
                          className="flex w-full items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                          onClick={() => handleDelete(skill)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Pagination footer (static for now) */}
        {filteredSkills.length > 0 && (
          <div className="flex items-center justify-between text-sm text-muted-foreground px-1">
            <div className="flex items-center gap-2">
              <span>Rows per page</span>
              <select className="border rounded px-2 py-1 text-sm bg-background">
                <option>20</option>
                <option>50</option>
                <option>100</option>
              </select>
            </div>
            <span>Page 1 of 1</span>
            <div className="flex items-center gap-1">
              {["«", "‹", "›", "»"].map((ch) => (
                <button key={ch} className="w-7 h-7 rounded border hover:bg-muted transition-colors flex items-center justify-center text-xs">
                  {ch}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

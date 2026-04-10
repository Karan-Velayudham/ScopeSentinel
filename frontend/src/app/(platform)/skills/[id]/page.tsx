"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Layers, Trash2, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useApi } from "@/hooks/use-api"
import Link from "next/link"

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

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return `${Math.floor(days / 7)}w ago`
}

export default function SkillDetailPage() {
  const api = useApi()
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [skill, setSkill] = useState<Skill | null>(null)
  const [loading, setLoading] = useState(true)

  // Editable state
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [instructions, setInstructions] = useState("")

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!api.orgId) return
    const load = async () => {
      try {
        const data = await api.get<Skill>(`/api/skills/${id}`)
        setSkill(data)
        setName(data.name)
        setDescription(data.description ?? "")
        setInstructions(data.instructions)
      } catch {
        setSkill(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, api.orgId])

  const isDirty =
    skill &&
    (name.trim() !== skill.name ||
      (description.trim() || null) !== skill.description ||
      instructions.trim() !== skill.instructions)

  const handleSave = async () => {
    if (!skill || !name.trim() || !instructions.trim()) return
    setSaving(true)
    setSaveError(null)
    try {
      // API uses PUT, not PATCH
      const updated = await api.fetch(`/api/skills/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          instructions: instructions.trim(),
        }),
      })
      if (!updated.ok) {
        const err = await updated.json().catch(() => ({}))
        throw new Error(err?.detail || `Error ${updated.status}`)
      }
      const data: Skill = await updated.json()
      setSkill(data)
      setName(data.name)
      setDescription(data.description ?? "")
      setInstructions(data.instructions)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: any) {
      setSaveError(e?.message || "Failed to save.")
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Delete skill "${skill?.name}"? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await api.delete(`/api/skills/${id}`)
      router.push("/skills")
    } catch {
      alert("Failed to delete skill.")
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-muted-foreground">
        Loading skill…
      </div>
    )
  }

  if (!skill) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <p className="text-muted-foreground">Skill not found.</p>
        <Link href="/skills">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Skills
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between border-b pb-4 mb-6 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/skills">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Layers className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight leading-tight">{skill.name}</h1>
            <p className="text-xs text-muted-foreground">
              Version {skill.version} · Last edited {timeAgo(skill.updated_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {saveError && (
            <span className="text-xs text-destructive">{saveError}</span>
          )}
          <Button
            variant="outline"
            size="sm"
            className="text-destructive border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
            onClick={handleDelete}
            disabled={deleting || saving}
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            {deleting ? "Deleting…" : "Delete"}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving || !isDirty}
            className="min-w-[90px]"
          >
            <Save className="h-3.5 w-3.5 mr-1.5" />
            {saving ? "Saving…" : saved ? "Saved ✓" : "Save"}
          </Button>
        </div>
      </div>

      {/* ── Body: left sidebar + right instructions ── */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1">

        {/* Left: Name, Description, Metadata */}
        <div className="lg:w-80 flex-shrink-0 flex flex-col gap-5">
          <div className="rounded-lg border bg-card p-5 flex flex-col gap-5 shadow-sm">

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Name
              </label>
              <Input
                id="skill-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter a name…"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Description
              </label>
              <Input
                id="skill-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter a description…"
              />
            </div>

            {/* Read-only meta */}
            <div className="pt-3 border-t flex flex-col gap-2 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Version</span>
                <span className="font-medium text-foreground">{skill.version}</span>
              </div>
              <div className="flex justify-between">
                <span>Status</span>
                <span className={`font-medium ${skill.is_active ? "text-green-600" : "text-muted-foreground"}`}>
                  {skill.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Created</span>
                <span className="font-medium text-foreground">{timeAgo(skill.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span>Updated</span>
                <span className="font-medium text-foreground">{timeAgo(skill.updated_at)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Instructions */}
        <div className="flex-1 rounded-lg border bg-card p-5 shadow-sm flex flex-col gap-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Instructions
          </label>
          <textarea
            id="skill-instructions"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Enter instructions for the skill…"
            rows={20}
            className="flex-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none font-mono leading-relaxed"
          />
        </div>
      </div>
    </div>
  )
}

"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Check, Edit2, X } from "lucide-react"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

const MOCK_PLAN = `
### Proposed Changes
We plan to update the authentication module.
1. Add Keycloak OpenID integration in \`src/auth.ts\`
2. Remove legacy JWT manual validation.
`

export function PlanReviewPanel({ runId }: { runId: string }) {
    const [isModifying, setIsModifying] = useState(false)
    const [feedback, setFeedback] = useState("")
    const [status, setStatus] = useState<"pending" | "approved" | "rejected" | "modifying">("pending")

    if (status === "approved") {
        return (
            <Card className="border-green-500/50 bg-green-500/5">
                <CardContent className="pt-6 flex items-center gap-3">
                    <Check className="h-5 w-5 text-green-500" />
                    <span className="font-medium">Plan Approved</span>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="border-yellow-500/50">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <span>Action Required: Review Plan</span>
                </CardTitle>
                <CardDescription>
                    The agent has proposed a plan. Please review it before execution proceeds.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="bg-muted/50 p-4 rounded-md prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {MOCK_PLAN}
                    </ReactMarkdown>
                </div>

                {isModifying && (
                    <div className="space-y-2 mt-4">
                        <Textarea
                            placeholder="Provide feedback on what needs to change..."
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            className="min-h-[100px]"
                        />
                        <div className="flex gap-2 justify-end">
                            <Button variant="ghost" size="sm" onClick={() => setIsModifying(false)}>Cancel</Button>
                            <Button size="sm" onClick={() => {
                                setStatus("modifying")
                                setIsModifying(false)
                            }}>
                                Submit Feedback
                            </Button>
                        </div>
                    </div>
                )}
            </CardContent>
            {!isModifying && (
                <CardFooter className="flex gap-2">
                    <Button variant="default" className="bg-green-600 hover:bg-green-700 text-white" onClick={() => setStatus("approved")}>
                        <Check className="mr-2 h-4 w-4" /> Approve
                    </Button>
                    <Button variant="destructive" onClick={() => setStatus("rejected")}>
                        <X className="mr-2 h-4 w-4" /> Reject
                    </Button>
                    <Button variant="outline" onClick={() => setIsModifying(true)}>
                        <Edit2 className="mr-2 h-4 w-4" /> Request Changes
                    </Button>
                </CardFooter>
            )}
        </Card>
    )
}

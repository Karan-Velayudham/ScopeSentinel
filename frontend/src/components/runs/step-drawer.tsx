import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function StepDrawer({ stepId, open, onOpenChange }: { stepId: string | null, open: boolean, onOpenChange: (open: boolean) => void }) {
    if (!stepId) return null;

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[600px] w-[90vw] overflow-y-auto">
                <SheetHeader className="mb-6">
                    <SheetTitle>Step Details: {stepId}</SheetTitle>
                    <SheetDescription>
                        Detailed input and output payloads for this step execution.
                    </SheetDescription>
                </SheetHeader>

                <Tabs defaultValue="output" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="input">Input</TabsTrigger>
                        <TabsTrigger value="output">Output</TabsTrigger>
                    </TabsList>
                    <TabsContent value="input" className="mt-4">
                        <div className="bg-muted p-4 rounded-md overflow-x-auto text-xs font-mono">
                            <pre>
                                {`{
  "taskId": "task-678",
  "agentName": "PlannerAgent",
  "toolCall": "generate_plan",
  "ticketId": "SCRUM-8"
}`}
                            </pre>
                        </div>
                    </TabsContent>
                    <TabsContent value="output" className="mt-4">
                        <div className="bg-muted p-4 rounded-md overflow-x-auto text-xs font-mono">
                            <pre>
                                {`{
  "status": "success",
  "result": {
    "planGenerated": true,
    "filesAffected": [
      "src/main.py",
      "src/models.py"
    ]
  },
  "metrics": {
    "durationMs": 25000,
    "tokens": 4502
  }
}`}
                            </pre>
                        </div>
                    </TabsContent>
                </Tabs>
            </SheetContent>
        </Sheet>
    )
}

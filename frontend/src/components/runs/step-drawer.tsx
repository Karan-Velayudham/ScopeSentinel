import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function StepDrawer({ step, open, onOpenChange }: { step: any, open: boolean, onOpenChange: (open: boolean) => void }) {
    if (!step) return null;

    const parseJson = (str: string | null) => {
        if (!str) return "{}";
        try {
            return JSON.stringify(JSON.parse(str), null, 2);
        } catch (e) {
            return str;
        }
    };

    return (
        <Sheet open={open} onOpenChange={onOpenChange}>
            <SheetContent className="sm:max-w-[800px] w-[90vw] overflow-y-auto">
                <SheetHeader className="mb-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <SheetTitle>{step.step_name}</SheetTitle>
                            <SheetDescription>
                                Details for {step.step_id.slice(0, 8)} • {step.status}
                            </SheetDescription>
                        </div>
                        {step.total_tokens > 0 && (
                            <div className="text-right">
                                <span className="text-xs font-medium text-muted-foreground block">Usage</span>
                                <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                                    {step.total_tokens.toLocaleString()} tokens
                                </span>
                            </div>
                        )}
                    </div>
                </SheetHeader>

                <Tabs defaultValue="output" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="input">Input Payload</TabsTrigger>
                        <TabsTrigger value="output">Output Result</TabsTrigger>
                    </TabsList>
                    <TabsContent value="input" className="mt-4">
                        <div className="bg-muted p-4 rounded-md overflow-x-auto text-xs font-mono border">
                            <pre className="whitespace-pre-wrap">
                                {parseJson(step.input_json)}
                            </pre>
                        </div>
                    </TabsContent>
                    <TabsContent value="output" className="mt-4">
                        <div className="bg-muted p-4 rounded-md overflow-x-auto text-xs font-mono border">
                            <pre className="whitespace-pre-wrap">
                                {parseJson(step.output_json)}
                            </pre>
                        </div>
                        {step.error_message && (
                            <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-md text-sm">
                                <p className="font-bold mb-1">Error Message:</p>
                                <pre className="whitespace-pre-wrap text-xs">{step.error_message}</pre>
                            </div>
                        )}
                    </TabsContent>
                </Tabs>
            </SheetContent>
        </Sheet>
    )
}

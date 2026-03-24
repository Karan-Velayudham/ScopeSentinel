"use client"

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface CapabilitiesDialogProps {
    isOpen: boolean
    onClose: () => void
    connectorName: string
    capabilities: any[]
}

export function CapabilitiesDialog({ isOpen, onClose, connectorName, capabilities }: CapabilitiesDialogProps) {
    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Capabilities: {connectorName}</DialogTitle>
                    <DialogDescription>
                        These tools are dynamically discovered and available for agents to use when this integration is connected.
                    </DialogDescription>
                </DialogHeader>

                <div className="mt-4">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Tool Name</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead>Required Scopes</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {capabilities.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                                        No capabilities discovered yet.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                capabilities.map((cap, idx) => (
                                    <TableRow key={idx}>
                                        <TableCell className="font-mono text-xs">{cap.name}</TableCell>
                                        <TableCell className="text-sm">{cap.description}</TableCell>
                                        <TableCell>
                                            {cap.scopes_required?.map((s: string) => (
                                                <Badge key={s} variant="outline" className="mr-1 text-[10px]">
                                                    {s}
                                                </Badge>
                                            ))}
                                            {!cap.scopes_required?.length && <span className="text-muted-foreground text-xs italic">none</span>}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            </DialogContent>
        </Dialog>
    )
}

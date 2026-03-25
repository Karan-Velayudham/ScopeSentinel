"use client";

import { useEffect, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { UserPlus, Trash2, Key, Shield } from "lucide-react";

interface User {
    id: string;
    email: string;
    role: string;
    has_api_key: boolean;
    org_id: string;
}

export default function TeamSettingsPage() {
    const api = useApi();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Invite state
    const [inviteOpen, setInviteOpen] = useState(false);
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviteRole, setInviteRole] = useState("developer");
    const [inviting, setInviting] = useState(false);

    const fetchUsers = async () => {
        if (!api.orgId) return;
        setLoading(true);
        try {
            const data = await api.get<User[]>("/api/users");
            setUsers(data || []);
            setError(null);
        } catch (e: any) {
            setError(e.message || "Failed to load users");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (api.orgId) {
            fetchUsers();
        }
    }, [api.orgId]);

    const handleInvite = async () => {
        if (!inviteEmail.trim() || !api.orgId) return;
        setInviting(true);
        try {
            await api.post("/api/users/invite", { email: inviteEmail.trim(), role: inviteRole });
            setInviteOpen(false);
            setInviteEmail("");
            setInviteRole("developer");
            await fetchUsers();
        } catch (e: any) {
            alert(`Failed to invite user: ${e.message}`);
        } finally {
            setInviting(false);
        }
    };

    const handleRoleChange = async (userId: string, newRole: string) => {
        try {
            await api.patch(`/api/users/${userId}/role`, { role: newRole });
            setUsers(users.map(u => (u.id === userId ? { ...u, role: newRole } : u)));
        } catch (e: any) {
            alert(`Failed to update role: ${e.message}`);
        }
    };

    const handleRemoveUser = async (userId: string) => {
        if (!confirm("Are you sure you want to remove this user from the organization?")) return;
        try {
            await api.delete(`/api/users/${userId}`);
            setUsers(users.filter(u => u.id !== userId));
        } catch (e: any) {
            alert(`Failed to remove user: ${e.message}`);
        }
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Team & Roles</h1>
                    <p className="text-muted-foreground mt-1">Manage members of your organization and their access levels.</p>
                </div>
                <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                    <DialogTrigger>
                        <Button>
                            <UserPlus className="h-4 w-4 mr-2" />
                            Invite User
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Invite a New Team Member</DialogTitle>
                            <DialogDescription>
                                They will be added to your current organization.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="py-4 space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">Email Address</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="colleague@company.com"
                                    value={inviteEmail}
                                    onChange={(e) => setInviteEmail(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="role">Role</Label>
                                <Select value={inviteRole} onValueChange={(val) => setInviteRole(val || "developer")}>
                                    <SelectTrigger id="role">
                                        <SelectValue placeholder="Select a role" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="admin">Admin (Full Access)</SelectItem>
                                        <SelectItem value="developer">Developer (Can Trigger Runs)</SelectItem>
                                        <SelectItem value="reviewer">Reviewer (Can Approve HITL)</SelectItem>
                                        <SelectItem value="viewer">Viewer (Read-only)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setInviteOpen(false)} disabled={inviting}>
                                Cancel
                            </Button>
                            <Button onClick={handleInvite} disabled={!inviteEmail.trim() || inviting}>
                                {inviting ? "Inviting..." : "Send Invite"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            {error && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm p-4 rounded-md">
                    {error}
                </div>
            )}

            <Card>
                <CardHeader>
                    <CardTitle>Organization Members</CardTitle>
                    <CardDescription>
                        Users who have access to this organization and their current roles.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">Loading team members...</div>
                    ) : users.length === 0 ? (
                        <div className="text-sm text-muted-foreground py-8 text-center">
                            No users found.
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>User</TableHead>
                                    <TableHead>Role</TableHead>
                                    <TableHead>API Key</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {users.map((user) => (
                                    <TableRow key={user.id}>
                                        <TableCell>
                                            <div className="font-medium">{user.email}</div>
                                            <div className="text-xs text-muted-foreground font-mono mt-0.5">{user.id}</div>
                                        </TableCell>
                                        <TableCell>
                                            <Select
                                                value={user.role}
                                                onValueChange={(val) => handleRoleChange(user.id, val || "viewer")}
                                            >
                                                <SelectTrigger className="w-[140px] h-8 text-xs">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="admin">Admin</SelectItem>
                                                    <SelectItem value="developer">Developer</SelectItem>
                                                    <SelectItem value="reviewer">Reviewer</SelectItem>
                                                    <SelectItem value="viewer">Viewer</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            {user.has_api_key ? (
                                                <div className="flex items-center text-xs text-emerald-600 dark:text-emerald-400">
                                                    <Key className="h-3 w-3 mr-1" /> Configured
                                                </div>
                                            ) : (
                                                <span className="text-xs text-muted-foreground">None</span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 px-2"
                                                onClick={() => handleRemoveUser(user.id)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                                <span className="sr-only">Remove</span>
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

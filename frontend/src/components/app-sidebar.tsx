"use client"

import * as React from "react"
import {
    Activity,
    Box,
    LayoutDashboard,
    Settings2,
    Workflow,
    LogOut,
    Bot,
    Users,
    ShieldCheck,
    CreditCard,
} from "lucide-react"
import { useSession, signIn, signOut } from "next-auth/react"
import { ThemeToggle } from "@/components/theme-toggle"

import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarRail,
} from "@/components/ui/sidebar"
import { Button } from "./ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"

const data = {
    navMain: [
        {
            title: "Dashboard",
            url: "/",
            icon: LayoutDashboard,
        },
        {
            title: "Runs",
            url: "/runs",
            icon: Activity,
        },
        {
            title: "Workflows",
            url: "/workflows",
            icon: Workflow,
        },
        {
            title: "Agents",
            url: "/agents",
            icon: Bot,
        },
        {
            title: "Integrations",
            url: "/integrations",
            icon: Box,
        },
        {
            title: "Settings",
            url: "/settings",
            icon: Settings2,
        },
        {
            title: "Team & Roles",
            url: "/settings/team",
            icon: Users,
        },
        {
            title: "Audit Log",
            url: "/audit",
            icon: ShieldCheck,
        },
        {
            title: "Billing & Usage",
            url: "/billing",
            icon: CreditCard,
        },
    ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    const { data: session } = useSession()

    return (
        <Sidebar collapsible="icon" {...props}>
            <SidebarHeader>
                <div className="flex items-center justify-between p-2">
                    <div className="flex items-center gap-2 font-semibold">
                        <span className="truncate">ScopeSentinel</span>
                    </div>
                    <ThemeToggle />
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarMenu>
                    {data.navMain.map((item) => (
                        <SidebarMenuItem key={item.title}>
                            <SidebarMenuButton tooltip={item.title} render={<a href={item.url} />}>
                                <item.icon />
                                <span>{item.title}</span>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    ))}
                </SidebarMenu>
            </SidebarContent>
            <SidebarFooter>
                <SidebarMenu>
                    <SidebarMenuItem>
                        {session?.user ? (
                            <div className="flex items-center justify-between w-full p-2">
                                <div className="flex items-center gap-2">
                                    <Avatar className="h-8 w-8">
                                        <AvatarImage src={session.user.image ?? ""} alt={session.user.name ?? "User"} />
                                        <AvatarFallback>{session.user.name?.[0]?.toUpperCase() ?? "U"}</AvatarFallback>
                                    </Avatar>
                                    <span className="truncate text-sm font-medium">
                                        {session.user.name}
                                    </span>
                                </div>
                                <Button variant="ghost" size="icon" onClick={() => signOut()}>
                                    <LogOut className="h-4 w-4" />
                                </Button>
                            </div>
                        ) : (
                            <Button variant="default" className="w-full" onClick={() => signIn("mock", { callbackUrl: "/" })}>
                                Sign In (Dev Mode)
                            </Button>
                        )}
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
            <SidebarRail />
        </Sidebar>
    )
}

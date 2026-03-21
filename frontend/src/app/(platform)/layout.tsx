import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { HitlBanner } from "@/components/hitl-banner";

export default function PlatformLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <SidebarProvider>
            <AppSidebar />
            <div className="flex flex-col flex-1 w-full bg-background min-h-screen">
                <header className="flex h-16 shrink-0 items-center justify-between border-b px-4 lg:hidden">
                    <div className="flex items-center gap-2 font-semibold">
                        <SidebarTrigger />
                        <span className="truncate">ScopeSentinel</span>
                    </div>
                </header>
                <HitlBanner />
                <main className="flex-1 p-6 md:p-8">
                    {children}
                </main>
            </div>
        </SidebarProvider>
    );
}

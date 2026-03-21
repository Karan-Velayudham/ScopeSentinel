"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { SessionProvider } from "next-auth/react"
import { TooltipProvider } from "@/components/ui/tooltip"

export function Providers({ children, ...props }: React.ComponentProps<typeof NextThemesProvider>) {
    const [queryClient] = React.useState(() => new QueryClient())

    return (
        <NextThemesProvider {...props}>
            <SessionProvider>
                <QueryClientProvider client={queryClient}>
                    <TooltipProvider>
                        {children}
                    </TooltipProvider>
                </QueryClientProvider>
            </SessionProvider>
        </NextThemesProvider>
    )
}

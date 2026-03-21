"use client"

import { useTheme } from "next-themes"
import dynamic from 'next/dynamic'
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"

const SyntaxHighlighter = dynamic(
    () => import('react-syntax-highlighter').then((mod) => mod.Prism),
    { ssr: false }
)

export function DiffViewer({ code, language = "typescript" }: { code: string, language?: string }) {
    const { resolvedTheme } = useTheme()

    return (
        <div className="rounded-md border overflow-hidden text-sm">
            <SyntaxHighlighter
                language={language}
                style={vscDarkPlus}
                customStyle={{ margin: 0, padding: '1rem', background: resolvedTheme === 'dark' ? '#09090b' : '#18181b' }}
            >
                {code}
            </SyntaxHighlighter>
        </div>
    )
}

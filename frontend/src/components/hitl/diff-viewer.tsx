"use client"

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

export function DiffViewer({ code, language = "typescript" }: { code: string, language?: string }) {
    const { resolvedTheme } = useTheme()
    const [mounted, setMounted] = useState(false)

    useEffect(() => setMounted(true), [])
    if (!mounted) return null

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

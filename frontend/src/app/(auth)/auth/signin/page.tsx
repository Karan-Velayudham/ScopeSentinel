"use client"

import { signIn } from "next-auth/react"
import { Github, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function SignInPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-sky-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-4">
            <div className="absolute inset-0 z-0 opacity-30 dark:opacity-10 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] pointer-events-none"></div>

            <Card className="w-full max-w-[440px] shadow-2xl border-white/50 dark:border-slate-800/50 backdrop-blur-xl bg-white/70 dark:bg-slate-900/70 z-10 transition-all duration-500 hover:shadow-indigo-500/10 dark:hover:shadow-indigo-500/5">
                <CardHeader className="text-center pt-10 pb-6">
                    <div className="mb-4 flex justify-center">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-sky-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                            <span className="text-white text-3xl font-bold italic tracking-tighter">S</span>
                        </div>
                    </div>
                    <CardTitle className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white mb-2">
                        Create an account
                    </CardTitle>
                    <CardDescription className="text-slate-500 dark:text-slate-400 text-base">
                        Choose your preferred sign-in method
                    </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 pb-10 px-8">
                    <Button
                        variant="outline"
                        size="lg"
                        className="w-full h-14 text-base font-medium border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all active:scale-[0.98]"
                        onClick={() => signIn("google", { callbackUrl: "/" })}
                    >
                        <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5 mr-3" />
                        Continue with Google
                    </Button>

                    <Button
                        variant="outline"
                        size="lg"
                        className="w-full h-14 text-base font-medium border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all active:scale-[0.98]"
                        onClick={() => signIn("microsoft-entra-id", { callbackUrl: "/" })}
                    >
                        <img src="https://www.microsoft.com/favicon.ico" alt="Microsoft" className="w-5 h-5 mr-3" />
                        Continue with Microsoft
                    </Button>

                    <Button
                        variant="outline"
                        size="lg"
                        className="w-full h-14 text-base font-medium border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all active:scale-[0.98]"
                        onClick={() => signIn("github", { callbackUrl: "/" })}
                    >
                        <Github className="w-5 h-5 mr-3" />
                        Continue with GitHub
                    </Button>

                    <div className="text-center pt-6 space-y-4">
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            Have an account already? <span className="text-pink-500 font-semibold cursor-pointer hover:underline">Sign in</span>
                        </p>

                        <p className="text-xs text-slate-400 dark:text-slate-500 px-6 leading-relaxed">
                            By signing up, you agree to our <br />
                            <span className="text-pink-500/80 font-medium cursor-pointer hover:underline">Terms of Service</span> &amp; <span className="text-pink-500/80 font-medium cursor-pointer hover:underline">Privacy Policy</span>
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}

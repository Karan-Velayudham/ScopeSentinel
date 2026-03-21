import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import GitHub from "next-auth/providers/github"
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id"

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        Google({
            clientId: process.env.AUTH_GOOGLE_ID,
            clientSecret: process.env.AUTH_GOOGLE_SECRET,
        }),
        GitHub({
            clientId: process.env.AUTH_GITHUB_ID,
            clientSecret: process.env.AUTH_GITHUB_SECRET,
        }),
        MicrosoftEntraID({
            clientId: process.env.AUTH_MICROSOFT_ENTRA_ID_ID,
            clientSecret: process.env.AUTH_MICROSOFT_ENTRA_ID_SECRET,
            issuer: `https://login.microsoftonline.com/${process.env.AUTH_MICROSOFT_ENTRA_ID_TENANT_ID}/v2.0`,
        }),
    ],
    pages: {
        signIn: "/auth/signin",
    },
    callbacks: {
        authorized({ auth, request: { nextUrl } }) {
            const isLoggedIn = !!auth?.user
            const isOnAuthPage = nextUrl.pathname.startsWith("/auth")
            if (!isLoggedIn && !isOnAuthPage) {
                return false // Redirect to login
            }
            return true
        },
    },
})

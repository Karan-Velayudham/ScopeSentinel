import NextAuth from "next-auth"
import Keycloak from "next-auth/providers/keycloak"
import Credentials from "next-auth/providers/credentials"

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        Keycloak({
            clientId: process.env.KEYCLOAK_CLIENT_ID,
            clientSecret: process.env.KEYCLOAK_CLIENT_SECRET,
            issuer: process.env.KEYCLOAK_ISSUER,
        }),
        Credentials({
            id: "mock",
            name: "Mock Account",
            credentials: {
                username: { label: "Username", type: "text", placeholder: "admin" },
                password: { label: "Password", type: "password" }
            },
            async authorize(credentials) {
                // For development, allow any login with 'admin' or no credentials
                return {
                    id: "1",
                    name: "Admin User",
                    email: "admin@scopesentinel.local",
                    image: "https://github.com/shadcn.png",
                }
            }
        })
    ],
})

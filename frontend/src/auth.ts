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
        async signIn({ user }) {
            if (!user.email) return false;
            try {
                // Call the API sync endpoint to ensure Org/User exist
                const api_url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                const res = await fetch(`${api_url}/api/auth/sync`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: user.email,
                        name: user.name || user.email.split('@')[0],
                    })
                });
                if (!res.ok) return false;
                return true;
            } catch (e) {
                console.error("Auth sync failed", e);
                return false;
            }
        },
        async authorized({ auth, request: { nextUrl } }) {
            const isLoggedIn = !!auth?.user
            const isOnAuthPage = nextUrl.pathname.startsWith("/auth")
            if (!isLoggedIn && !isOnAuthPage) {
                return false // Redirect to login
            }
            return true
        },
        async jwt({ token, user, trigger }) {
            if (user && user.email) {
                // Initial sign in or user update
                try {
                    const api_url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                    const res = await fetch(`${api_url}/api/auth/sync`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            email: user.email,
                            name: user.name || user.email.split('@')[0],
                        })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        token.org_id = data.org_id;
                    }
                } catch (e) {
                    console.error("JWT sync failed", e);
                }
            }
            return token;
        },
        async session({ session, token }) {
            if (token.org_id) {
                session.user.org_id = token.org_id as string;
            }
            
            // Generate a backend-compatible JWT using the secret
            try {
                const { SignJWT } = await import('jose');
                const secretString = process.env.AUTH_SECRET || "dev-secret-123";
                const secret = new TextEncoder().encode(secretString);
                const backendToken = await new SignJWT({ 
                    email: session.user.email,
                    org_id: session.user.org_id,
                    name: session.user.name
                })
                .setProtectedHeader({ alg: 'HS256' })
                .setIssuedAt()
                .setExpirationTime('24h')
                .sign(secret);
                
                (session as any).accessToken = backendToken;
            } catch (e) {
                console.error("Failed to generate backend token", e);
            }
            
            return session;
        },
    },
})

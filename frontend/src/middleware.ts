import { auth } from "./auth"

export default auth((req) => {
    const { nextUrl } = req
    const isLoggedIn = !!req.auth
    const isAuthRoute = nextUrl.pathname.startsWith("/auth")

    if (!isLoggedIn && !isAuthRoute) {
        return Response.redirect(new URL("/auth/signin", nextUrl))
    }
})

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}

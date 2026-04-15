export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: [
    "/projects/:path*",
    "/registry/:path*",
    "/settings/:path*",
    "/admin/:path*",
  ],
};

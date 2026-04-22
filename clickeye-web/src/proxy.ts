import { auth } from "@/lib/auth";

export default auth;

export const config = {
  matcher: [
    "/projects/:path*",
    "/registry/:path*",
    "/settings/:path*",
    "/admin/:path*",
  ],
};

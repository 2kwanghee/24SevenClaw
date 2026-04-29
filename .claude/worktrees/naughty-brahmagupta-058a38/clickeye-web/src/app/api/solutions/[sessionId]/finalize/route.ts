import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";

const INTERNAL_API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> },
) {
  const session = await auth();
  if (!session?.accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const { sessionId } = await params;
  const body = (await req.json()) as {
    project_name: string;
    description?: string | null;
    wizard_data?: unknown;
  };

  const { wizard_data, ...finalizeBody } = body;

  try {
    const res = await fetch(
      `${INTERNAL_API_URL}/api/v1/prototype-sessions/${sessionId}/finalize`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.accessToken}`,
        },
        body: JSON.stringify(finalizeBody),
      },
    );

    const data = (await res.json().catch(() => ({}))) as {
      project_id?: string;
      detail?: string;
    };

    if (!res.ok) {
      console.error(`[finalize proxy] FastAPI ${res.status}:`, JSON.stringify(data));
      return NextResponse.json(data, { status: res.status });
    }

    // wizard_data를 별도 config 엔드포인트로 저장 (ZIP 재다운로드용)
    if (data.project_id && wizard_data) {
      await fetch(
        `${INTERNAL_API_URL}/api/v1/projects/${data.project_id}/config`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.accessToken}`,
          },
          body: JSON.stringify({ wizard_data }),
        },
      ).catch((err: unknown) => {
        console.warn("[finalize proxy] wizard config 저장 실패:", err);
      });
    }

    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { detail: "API 서버 연결에 실패했습니다" },
      { status: 503 },
    );
  }
}

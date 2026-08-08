const evidenceIdPattern = /^ev\d{3,}$/;

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ evidenceId: string }> },
) {
  const { evidenceId } = await params;
  if (!evidenceIdPattern.test(evidenceId)) {
    return Response.json(
      { detail: { code: "INVALID_ID", resource: "evidence", id: evidenceId } },
      { status: 400 },
    );
  }

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const upstream = await fetch(
      `${apiBaseUrl}/api/v1/evidence/${encodeURIComponent(evidenceId)}`,
      {
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
      },
    );
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": upstream.headers.get("Content-Type") ?? "application/json; charset=utf-8",
      },
    });
  } catch {
    return Response.json(
      { detail: { code: "UPSTREAM_UNAVAILABLE", resource: "evidence", id: evidenceId } },
      { status: 502 },
    );
  }
}

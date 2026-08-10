export const dynamic = "force-dynamic";

const MAX_QUERY_BYTES = 16_384;

export async function POST(request: Request) {
  const contentType = request.headers.get("content-type")?.toLowerCase() ?? "";
  if (!contentType.startsWith("application/json")) {
    return Response.json(
      { detail: { code: "INVALID_CONTENT_TYPE", resource: "parena_solver", id: null } },
      { status: 415 },
    );
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_QUERY_BYTES) {
    return Response.json(
      { detail: { code: "QUERY_TOO_LARGE", resource: "parena_solver", id: null } },
      { status: 413 },
    );
  }
  try {
    JSON.parse(body);
  } catch {
    return Response.json(
      { detail: { code: "INVALID_JSON", resource: "parena_solver", id: null } },
      { status: 400 },
    );
  }

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const upstream = await fetch(`${apiBaseUrl}/api/v1/solver/parena`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": upstream.headers.get("Content-Type") ?? "application/json; charset=utf-8",
      },
    });
  } catch {
    return Response.json(
      { detail: { code: "UPSTREAM_UNAVAILABLE", resource: "parena_solver", id: null } },
      { status: 502 },
    );
  }
}

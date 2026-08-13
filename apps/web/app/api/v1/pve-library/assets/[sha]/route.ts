const assetShaPattern = /^[0-9a-f]{64}$/;

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ sha: string }> },
) {
  const { sha } = await params;
  if (!assetShaPattern.test(sha)) {
    return Response.json(
      { error: { code: "INVALID_ASSET_SHA", message: "Portrait asset SHA-256 is invalid." } },
      { status: 400 },
    );
  }

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const upstream = await fetch(
      `${apiBaseUrl}/api/v1/pve-library/assets/${encodeURIComponent(sha)}`,
      { cache: "no-store", signal: AbortSignal.timeout(5_000) },
    );
    const contentType = upstream.headers.get("Content-Type") ?? "application/octet-stream";
    if (upstream.ok && !contentType.toLowerCase().startsWith("image/")) {
      return Response.json(
        { error: { code: "INVALID_ASSET_RESPONSE", message: "Portrait endpoint did not return an image." } },
        { status: 502 },
      );
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Cache-Control": "private, no-store",
        "Content-Type": contentType,
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return Response.json(
      { error: { code: "UPSTREAM_UNAVAILABLE", message: "Portrait asset is temporarily unavailable." } },
      { status: 502 },
    );
  }
}

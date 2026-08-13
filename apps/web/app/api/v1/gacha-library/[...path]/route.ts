const assetShaPattern = /^[0-9a-f]{64}$/;
const allowedAssetContentTypes = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const target = resolveTarget(path);
  if (!target) {
    return Response.json(
      { error: { code: "GACHA_LIBRARY_ROUTE_NOT_FOUND", message: "Private Gacha route was not found." } },
      { status: 404 },
    );
  }

  const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const upstream = await fetch(`${apiBaseUrl}${target.path}`, {
      headers: { Accept: target.kind === "asset" ? "image/*" : "application/json" },
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(5_000),
    });
    const contentType = upstream.headers.get("Content-Type") ?? "application/octet-stream";
    if (upstream.status >= 300 && upstream.status < 400) {
      return invalidUpstreamResponse("UPSTREAM_REDIRECT_REJECTED", target.kind);
    }
    if (upstream.ok) {
      if (!isExpectedSuccessContentType(target.kind, contentType)) {
        return invalidUpstreamResponse("INVALID_GACHA_LIBRARY_RESPONSE", target.kind);
      }
    } else if (!isJsonContentType(contentType)) {
      return invalidUpstreamResponse("INVALID_GACHA_LIBRARY_ERROR_RESPONSE", target.kind);
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
      {
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: "Private Gacha library is temporarily unavailable.",
        },
      },
      { status: 502 },
    );
  }
}

function resolveTarget(path: string[]): { kind: "json" | "asset"; path: string } | null {
  if (path.length === 1 && path[0] === "forecasts") {
    return { kind: "json", path: "/api/v1/gacha-library/forecasts" };
  }
  if (path.length === 2 && path[0] === "assets" && assetShaPattern.test(path[1] ?? "")) {
    return {
      kind: "asset",
      path: `/api/v1/gacha-library/assets/${encodeURIComponent(path[1])}`,
    };
  }
  return null;
}

function isExpectedSuccessContentType(
  kind: "json" | "asset",
  contentType: string,
): boolean {
  const normalized = normalizedContentType(contentType);
  return kind === "asset"
    ? allowedAssetContentTypes.has(normalized)
    : normalized === "application/json";
}

function isJsonContentType(contentType: string): boolean {
  return normalizedContentType(contentType) === "application/json";
}

function normalizedContentType(contentType: string): string {
  return contentType.split(";", 1)[0]?.trim().toLowerCase() ?? "";
}

function invalidUpstreamResponse(
  code:
    | "UPSTREAM_REDIRECT_REJECTED"
    | "INVALID_GACHA_LIBRARY_RESPONSE"
    | "INVALID_GACHA_LIBRARY_ERROR_RESPONSE",
  kind: "json" | "asset",
): Response {
  return Response.json(
    {
      error: {
        code,
        message: `Private Gacha ${kind} endpoint returned an unsafe response.`,
      },
    },
    {
      status: 502,
      headers: {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      },
    },
  );
}

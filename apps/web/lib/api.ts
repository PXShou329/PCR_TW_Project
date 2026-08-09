import "server-only";

import { createApiClient } from "@pcr-tw/api-client";

export function serverApi() {
  return createApiClient({
    baseUrl: process.env.API_BASE_URL ?? "http://127.0.0.1:8000",
  });
}

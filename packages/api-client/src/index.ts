export * from "./types";

import type {
  ApiEnvelope,
  ApiProblem,
  Baseline,
  Claim,
  Evidence,
  PvpCounter,
  StageDetail,
  StageSummary,
  TeamDetail,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly problem?: ApiProblem,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiClientOptions {
  baseUrl: string;
  fetchImpl?: typeof fetch;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

export function createApiClient({ baseUrl, fetchImpl = fetch }: ApiClientOptions) {
  const origin = trimTrailingSlash(baseUrl);

  async function get<T>(path: string): Promise<ApiEnvelope<T>> {
    const response = await fetchImpl(`${origin}${path}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      let problem: ApiProblem | undefined;
      try {
        problem = (await response.json()) as ApiProblem;
      } catch {
        problem = undefined;
      }
      throw new ApiError(
        problem?.detail?.code ?? `API request failed with ${response.status}`,
        response.status,
        problem,
      );
    }

    return (await response.json()) as ApiEnvelope<T>;
  }

  return {
    getBaseline: () => get<Baseline>("/api/v1/baseline"),
    getStages: () => get<StageSummary[]>("/api/v1/stages"),
    getStage: (guideId: string) =>
      get<StageDetail>(`/api/v1/stages/${encodeURIComponent(guideId)}`),
    getTeam: (teamId: string) =>
      get<TeamDetail>(`/api/v1/teams/${encodeURIComponent(teamId)}`),
    getEvidence: (evidenceId: string) =>
      get<Evidence>(`/api/v1/evidence/${encodeURIComponent(evidenceId)}`),
    getClaim: (claimId: string) =>
      get<Claim>(`/api/v1/claims/${encodeURIComponent(claimId)}`),
    getPvpCounters: (defenseSignature?: string) => {
      const query = defenseSignature
        ? `?defense_signature=${encodeURIComponent(defenseSignature)}`
        : "";
      return get<PvpCounter[]>(`/api/v1/pvp/counters${query}`);
    },
  };
}

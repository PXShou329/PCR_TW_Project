export * from "./types";

import type {
  ApiEnvelope,
  ApiProblem,
  Baseline,
  Claim,
  Evidence,
  GachaCommunitySource,
  GachaLibraryEnvelope,
  GachaLibraryForecastData,
  GachaTimelineEvent,
  PvpCharacter,
  PvpCounter,
  ParenaEnvironment,
  ParenaSolveData,
  ParenaSolveRequest,
  PveLibraryEnvelope,
  PveLibraryStageFilters,
  PveStageDetail,
  PveStageListData,
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

  async function getEnvelope<T>(path: string): Promise<T> {
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
        problem?.detail?.code ??
          problem?.error?.code ??
          `API request failed with ${response.status}`,
        response.status,
        problem,
      );
    }

    return (await response.json()) as T;
  }

  async function get<T>(path: string): Promise<ApiEnvelope<T>> {
    return getEnvelope<ApiEnvelope<T>>(path);
  }

  async function post<T>(path: string, body: unknown): Promise<ApiEnvelope<T>> {
    const response = await fetchImpl(`${origin}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
        problem?.detail?.code ??
          problem?.error?.code ??
          `API request failed with ${response.status}`,
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
    getGachaTimeline: () =>
      get<GachaTimelineEvent[]>("/api/v1/gacha/timeline"),
    getGachaCommunitySources: () =>
      get<GachaCommunitySource[]>("/api/v1/gacha/community-sources"),
    getGachaLibraryForecasts: (): Promise<
      GachaLibraryEnvelope<GachaLibraryForecastData>
    > =>
      getEnvelope<GachaLibraryEnvelope<GachaLibraryForecastData>>(
        "/api/v1/gacha-library/forecasts",
      ),
    getPvpCharacters: () => get<PvpCharacter[]>("/api/v1/pvp/characters"),
    getPvpCounters: (defenseSignature?: string) => {
      const query = defenseSignature
        ? `?defense_signature=${encodeURIComponent(defenseSignature)}`
        : "";
      return get<PvpCounter[]>(`/api/v1/pvp/counters${query}`);
    },
    getParenaEnvironments: () =>
      get<ParenaEnvironment[]>("/api/v1/parena/environments"),
    solveParena: (request: ParenaSolveRequest) =>
      post<ParenaSolveData>("/api/v1/solver/parena", request),
    getPveLibraryStages: (
      filters: PveLibraryStageFilters = {},
    ): Promise<PveLibraryEnvelope<PveStageListData>> => {
      const query = new URLSearchParams();
      if (filters.mode !== undefined) query.set("mode", filters.mode);
      if (filters.element !== undefined) query.set("element", filters.element);
      if (filters.area !== undefined) query.set("area", String(filters.area));
      if (filters.stage !== undefined) query.set("stage", String(filters.stage));
      const suffix = query.size > 0 ? `?${query.toString()}` : "";
      return getEnvelope<PveLibraryEnvelope<PveStageListData>>(
        `/api/v1/pve-library/stages${suffix}`,
      );
    },
    getPveLibraryStage: (
      stageId: string,
    ): Promise<PveLibraryEnvelope<PveStageDetail>> =>
      getEnvelope<PveLibraryEnvelope<PveStageDetail>>(
        `/api/v1/pve-library/stages/${encodeURIComponent(stageId)}`,
      ),
  };
}

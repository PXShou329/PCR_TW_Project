import type { ParenaEnvironment, PvpCharacter } from "@pcr-tw/api-client";
import { ParenaPlanner } from "../../components/parena-planner";
import { serverApi } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ParenaPage() {
  const api = serverApi();
  const [charactersResult, environmentsResult] = await Promise.allSettled([
    api.getPvpCharacters(),
    api.getParenaEnvironments(),
  ]);
  const characters: PvpCharacter[] = charactersResult.status === "fulfilled"
    ? charactersResult.value.data.filter((row) => row.tw_availability_status === "AVAILABLE")
    : [];
  const environments: ParenaEnvironment[] = environmentsResult.status === "fulfilled"
    ? environmentsResult.value.data
    : [];
  const warnings = environmentsResult.status === "fulfilled"
    ? environmentsResult.value.meta.warnings
    : ["NO_PARENA_MATERIALIZATION"];

  return <ParenaPlanner characters={characters} environments={environments} initialWarnings={warnings} />;
}

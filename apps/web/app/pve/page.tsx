import { redirect } from "next/navigation";

type Query = Record<string, string | string[] | undefined>;

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function appendIfPresent(target: URLSearchParams, query: Query, name: string) {
  const value = firstValue(query[name])?.trim();
  if (value) target.set(name, value);
}

export default async function LegacyPveLibraryPage(
  { searchParams }: { searchParams: Promise<Query> },
) {
  const query = await searchParams;
  const mode = firstValue(query.mode)?.trim().toUpperCase();
  const nextQuery = new URLSearchParams();

  if (mode === "REMEMBRANCE") {
    appendIfPresent(nextQuery, query, "element");
    redirect(`/pve/remembrance${nextQuery.size ? `?${nextQuery}` : ""}`);
  }

  if (mode === "LUNA_TOWER") redirect("/pve/luna-tower");

  appendIfPresent(nextQuery, query, "element");
  appendIfPresent(nextQuery, query, "area");
  appendIfPresent(nextQuery, query, "stage");
  redirect(`/pve/deep${nextQuery.size ? `?${nextQuery}` : ""}`);
}

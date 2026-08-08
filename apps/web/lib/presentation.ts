import type { OperationMode, StrategyStatus } from "@pcr-tw/api-client";

export function statusLabel(status: StrategyStatus | string): string {
  const labels: Record<string, string> = {
    VERIFIED: "已驗證通關",
    PROVISIONAL: "暫定攻略",
    IN_RESEARCH: "研究中",
    PENDING: "待重現",
    PASS: "台服可用",
    SOURCE_GAP: "來源缺口",
  };
  return labels[status] ?? status;
}

export function operationLabel(mode: OperationMode | string): string {
  const labels: Record<string, string> = {
    AUTO: "全自動",
    SEMI_AUTO: "半自動",
    MANUAL: "手動",
    SOURCE_CONFLICT: "來源操作聲明衝突",
  };
  return labels[mode] ?? mode;
}

export function statusTone(status: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (status === "VERIFIED" || status === "PASS") return "success";
  if (status === "PROVISIONAL" || status === "PENDING" || status === "SOURCE_CONFLICT") {
    return "warning";
  }
  if (status === "IN_RESEARCH" || status === "SOURCE_GAP") return "info";
  return "neutral";
}

export function requirementLabel(value: string | undefined): string {
  if (!value || value === "UNKNOWN") return "未確認";
  return value;
}

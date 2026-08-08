import type { SlotRequirement, TeamMember, TeamRequirements } from "@pcr-tw/api-client";
import { Badge } from "@pcr-tw/ui";

const fields: Array<[keyof SlotRequirement, string]> = [
  ["star", "星數"],
  ["rank", "RANK"],
  ["ue1", "專用裝備 1"],
  ["ue2", "專用裝備 2"],
  ["six_star", "六星"],
  ["connect_rank", "連結品級"],
  ["element_boost", "屬性強化"],
];
const slotKeys = ["slot1", "slot2", "slot3", "slot4", "slot5"] as const;

export function RequirementsMatrix({
  members,
  requirements,
}: {
  members: TeamMember[];
  requirements: TeamRequirements;
}) {
  return (
    <div className="requirements-grid">
      {members.map((member, index) => {
        const slotKey = slotKeys[member.slot - 1] ?? slotKeys[index] ?? "slot1";
        const slot = requirements.slots[slotKey];
        return (
          <article className="requirement-card" key={`${slotKey}-${member.unit_key}`}>
            <div className="requirement-card__heading">
              <span className="slot-number">{index + 1}</span>
              <div>
                <h3>{member.tw_name}</h3>
                <code>{member.unit_key}</code>
              </div>
            </div>
            <dl>
              {fields.map(([key, label]) => {
                const value = slot?.[key];
                const unknown = !value || value === "UNKNOWN";
                return (
                  <div key={key}>
                    <dt>{label}</dt>
                    <dd>{unknown ? <Badge tone="warning">未確認</Badge> : value}</dd>
                  </div>
                );
              })}
            </dl>
          </article>
        );
      })}
    </div>
  );
}

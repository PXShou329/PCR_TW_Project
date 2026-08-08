import type { TeamMember } from "@pcr-tw/api-client";
import { Badge } from "@pcr-tw/ui";

export function TeamRoster({ members }: { members: TeamMember[] }) {
  return (
    <ol className="roster" aria-label="隊伍角色">
      {members.map((member, index) => (
        <li key={`${member.slot}-${member.unit_key}`}>
          <span className="roster__slot">{index + 1}</span>
          <span className="roster__avatar" aria-hidden="true">
            {member.tw_name.slice(0, 1)}
          </span>
          <span className="roster__name">
            <strong>{member.tw_name}</strong>
            <code>{member.unit_key}</code>
          </span>
          {member.is_borrowed ? <Badge tone="info">借角</Badge> : null}
        </li>
      ))}
    </ol>
  );
}

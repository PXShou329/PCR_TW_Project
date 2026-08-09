import type { ArenaMember } from "@pcr-tw/api-client";

export function ArenaRoster({
  label,
  members,
}: {
  label: string;
  members: ArenaMember[];
}) {
  return (
    <ol className="roster arena-roster" aria-label={label}>
      {members.map((member) => (
        <li key={`${member.slot}-${member.unit_key}`}>
          <span className="roster__slot">{member.slot}</span>
          <span className="roster__avatar" aria-hidden="true">
            {member.display_name.slice(0, 1)}
          </span>
          <span className="roster__name">
            <strong>{member.display_name}</strong>
            <code>{member.unit_key}</code>
            <small className="arena-roster__source">
              {member.display_name_source === "TW_OFFICIAL" ? "台服官方名" : "日服官方名"}
            </small>
          </span>
        </li>
      ))}
    </ol>
  );
}

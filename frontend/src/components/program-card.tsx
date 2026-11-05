"use client";

import { ArrowUpRight, Banknote, Check, Clock3, MapPin } from "lucide-react";
import type { Program } from "@/lib/types";
import { euro } from "@/lib/types";

export function ProgramMark({
  program,
  size = "normal",
}: {
  program: Program;
  size?: "normal" | "small";
}) {
  return (
    <div
      className={`program-mark ${program.id.split("-")[0]} ${size}`}
      aria-hidden="true"
    >
      <span>
        {program.university
          .split(" ")
          .slice(0, 2)
          .map((part) => part[0])
          .join("")}
      </span>
      <i />
      <i />
      <i />
    </div>
  );
}

export function ProgramCard({
  program,
  selected = false,
  onCompare,
  onDetails,
}: {
  program: Program;
  selected?: boolean;
  onCompare?: () => void;
  onDetails?: () => void;
}) {
  return (
    <article className="program-card">
      <div className="program-card-top">
        <ProgramMark program={program} />
        <span className="tag">Synthetic program</span>
      </div>
      <p className="eyebrow muted">
        <MapPin size={12} /> {program.city}, {program.country}
      </p>
      <h3>{program.university}</h3>
      <p className="program-title">{program.program}</p>
      <div className="program-tags">
        <span>
          <Clock3 size={13} />
          {program.duration_months} months
        </span>
        <span>{program.language}</span>
      </div>
      <div className="card-cost">
        <span>
          <Banknote size={16} />
          Annual total <small>tuition + living</small>
        </span>
        <strong>{euro(program.tuition_eur + program.living_cost_eur)}</strong>
      </div>
      <div className="program-card-actions">
        {onCompare && (
          <button
            className={`button button-small ${selected ? "button-soft" : "button-outline"}`}
            onClick={onCompare}
            aria-pressed={selected}
          >
            {selected ? (
              <>
                <Check size={15} />
                Selected
              </>
            ) : (
              "Compare"
            )}
          </button>
        )}
        <button className="text-button" onClick={onDetails}>
          View details <ArrowUpRight size={15} />
        </button>
      </div>
    </article>
  );
}

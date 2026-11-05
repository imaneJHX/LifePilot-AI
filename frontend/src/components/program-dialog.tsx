"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { ProgramMark } from "./program-card";
import { DemoNotice } from "./ui";
import { euro, type Program } from "@/lib/types";

export function ProgramDialog({
  program,
  close,
}: {
  program: Program;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className="program-dialog"
      onClose={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
      aria-labelledby="program-dialog-title"
    >
      <div className="dialog-content">
        <div className="dialog-top">
          <ProgramMark program={program} />
          <button
            className="icon-button"
            onClick={close}
            aria-label="Close program details"
          >
            <X size={22} />
          </button>
        </div>
        <span className="eyebrow">
          {program.city} · {program.country}
        </span>
        <h2 id="program-dialog-title">{program.university}</h2>
        <p className="dialog-program">{program.program}</p>
        <div className="detail-grid">
          <div>
            <span>Tuition / year</span>
            <strong>{euro(program.tuition_eur)}</strong>
          </div>
          <div>
            <span>Living / year</span>
            <strong>{euro(program.living_cost_eur)}</strong>
          </div>
          <div>
            <span>Annual total</span>
            <strong>
              {euro(program.tuition_eur + program.living_cost_eur)}
            </strong>
          </div>
          <div>
            <span>Duration & language</span>
            <strong>
              {program.duration_months} months · {program.language}
            </strong>
          </div>
        </div>
        <h3>Illustrative curriculum</h3>
        <div className="program-tags">
          {program.curriculum.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
        <h3>Synthetic decision indices</h3>
        <p className="muted">
          Academic intensity {program.academic_index}/100 · Career{" "}
          {program.career_index}/100 · Student experience{" "}
          {program.experience_index}/100
        </p>
        <DemoNotice />
        <p className="provenance">{program.provenance}</p>
      </div>
    </dialog>
  );
}

"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Search } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import type { RealProgram, RealProgramCatalog } from "@/lib/types";
import { ErrorNotice, Loading } from "./ui";

const unavailable = "Information unavailable";
const fold = (value: string) => value.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase().replace(/\s+/g, " ").trim();
const publishedDate = (value: string) => new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
}).format(new Date(`${value}T12:00:00Z`));

function RealProgramCard({ program }: { program: RealProgram }) {
  const deadlineLabels = {
    expired: "Expired deadline", upcoming: "Future deadline", today: "Deadline today", unknown: "Date not confirmed",
  };
  return (
    <article className="panel real-program-card">
      <div className="real-program-heading">
        <span className="tag">{program.verification_status === "verified" ? "Verified" : "Not verified"}</span>
        <span className="real-study-field">{program.study_area ?? unavailable}</span>
      </div>
      <p className="real-university">{program.university_name ?? unavailable}</p>
      <h2>{program.program_name ?? unavailable}</h2>
      <dl className="real-program-facts">
        <div><dt>Country</dt><dd>{program.country ?? unavailable}</dd></div>
        <div><dt>Degree</dt><dd>{program.degree_type ?? unavailable}</dd></div>
        <div><dt>Teaching language</dt><dd>{program.teaching_language ?? program.teaching_languages?.join(", ") ?? unavailable}</dd></div>
        <div><dt>Duration</dt><dd>{program.duration ?? (program.duration_months !== null ? `${program.duration_months} months` : unavailable)}</dd></div>
        <div><dt>Tuition</dt><dd>{program.tuition_fees ? (
          <details className="real-source-text">
            <summary>View published tuition information</summary>
            <p>{program.tuition_fees}</p>
            <p>Published fees may cover different applicant groups or study modes. Confirm your fee category with the university.</p>
          </details>
        ) : unavailable}</dd></div>
        <div><dt>Fee currency</dt><dd>{program.currency ?? unavailable}</dd></div>
        <div><dt>Academic year</dt><dd>{program.academic_year ?? unavailable}</dd></div>
        <div><dt>Application deadline</dt><dd>
          {program.application_deadline_date ? <>
            <span>{publishedDate(program.application_deadline_date)}</span>
            <strong className={`deadline-badge ${program.deadline_status}`}>{deadlineLabels[program.deadline_status]}</strong>
          </> : unavailable}
        </dd></div>
      </dl>
      <details className="real-source-text real-details">
        <summary>Requirements and source details</summary>
        <dl>
          <div><dt>Description</dt><dd>{program.description ?? unavailable}</dd></div>
          <div><dt>Admission requirements</dt><dd>{program.admission_requirements ?? unavailable}</dd></div>
          <div><dt>English-language requirements</dt><dd>{program.english_language_requirements ?? unavailable}</dd></div>
          <div><dt>Published application information</dt><dd>{program.application_deadline ?? unavailable}</dd></div>
          <div><dt>Application opening date</dt><dd>{program.application_opening_date ? publishedDate(program.application_opening_date) : unavailable}</dd></div>
          <div><dt>City</dt><dd>{program.city ?? unavailable}</dd></div>
          <div><dt>Source retrieved</dt><dd>{publishedDate(program.retrieval_date.slice(0, 10))}</dd></div>
        </dl>
      </details>
      {program.official_program_url ? (
        <a className="button button-outline" href={program.official_program_url} target="_blank" rel="noopener noreferrer">
          Official program page <ArrowUpRight size={16} />
        </a>
      ) : <p>Official program link: {unavailable}</p>}
    </article>
  );
}

export function RealProgramExplorer() {
  const [catalog, setCatalog] = useState<RealProgramCatalog | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [country, setCountry] = useState("");
  const [university, setUniversity] = useState("");
  const [field, setField] = useState("");
  const [query, setQuery] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api.realPrograms(controller.signal).then((data) => {
      if (!controller.signal.aborted) setCatalog(data);
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setError(errorMessage(error));
    }).finally(() => {
      if (!controller.signal.aborted) setBusy(false);
    });
    return () => controller.abort();
  }, [attempt]);
  const filtered = (catalog?.programs ?? []).filter((program) =>
    (!country || program.country === country) &&
    (!university || program.university_name === university) &&
    (!field || program.study_area === field) &&
    fold([program.university_name, program.program_name, program.country, program.city, program.study_area, program.degree_type].join(" ")).includes(fold(query)),
  );
  const clear = () => { setCountry(""); setUniversity(""); setField(""); setQuery(""); };
  return (
    <section aria-labelledby="real-programs-title">
      <div className="page-heading">
        <div>
          <span className="eyebrow">RESEARCH YOUR NEXT CHAPTER</span>
          <h1 id="real-programs-title">Real Programs</h1>
          <p>Explore source-linked university programs and check the published details.</p>
        </div>
      </div>
      <div className="real-program-notice">
        <strong>Research records — verification required.</strong>
        <p>Unreviewed records are marked “Not verified”. Check official pages for current details. Real programs are not included in demo recommendations.</p>
      </div>
      {error && <ErrorNotice message={error} retry={() => { setBusy(true); setError(null); setAttempt((value) => value + 1); }} />}
      {busy ? <Loading text="Loading real university programs…" /> : !error && catalog && <>
        <div className="real-program-filters">
          <label className="search-input"><Search size={18} /><span className="sr-only">Search real programs</span>
            <input value={query} maxLength={100} onChange={(event) => setQuery(event.target.value)} placeholder="Program, university, or keyword" />
          </label>
          <label>Country<select aria-label="Real country" value={country} onChange={(event) => setCountry(event.target.value)}>
            <option value="">All countries</option>{catalog.countries.map((value) => <option key={value}>{value}</option>)}
          </select></label>
          <label>University<select aria-label="Real university" value={university} onChange={(event) => setUniversity(event.target.value)}>
            <option value="">All universities</option>{catalog.universities.map((value) => <option key={value}>{value}</option>)}
          </select></label>
          <label>Study field<select aria-label="Real study field" value={field} onChange={(event) => setField(event.target.value)}>
            <option value="">All study fields</option>{catalog.study_areas.map((value) => <option key={value}>{value}</option>)}
          </select></label>
        </div>
        <div className="real-results-bar">
          <p role="status"><strong>{filtered.length}</strong> real {filtered.length === 1 ? "program" : "programs"}{catalog.total ? ` of ${catalog.total}` : ""}</p>
          <button type="button" className="text-button" onClick={clear}>Clear real-program filters</button>
        </div>
        <p className="real-deadline-note">Deadline dates checked as of {publishedDate(catalog.as_of_date)} (UTC). A future date does not confirm applications are open. Undated application text is not treated as a confirmed deadline.</p>
        {filtered.length ? <div className="real-program-grid">{filtered.map((program) => <RealProgramCard key={program.id} program={program} />)}</div> : (
          <div className="empty-panel">
            <h2>{catalog.total ? "No programs match these filters." : "No real programs are available yet."}</h2>
            <p>{catalog.total ? "Try a different country, university, study field, or keyword." : "The real-program catalog is empty. Demo Recommendations remains available."}</p>
          </div>
        )}
      </>}
    </section>
  );
}

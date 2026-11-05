"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  Compass,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import Link from "next/link";
import { ProgramCard } from "@/components/program-card";
import { ProgramDialog } from "@/components/program-dialog";
import { DemoNotice, ErrorNotice, Loading, Reveal } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { countries, euro, studyAreas, type Program } from "@/lib/types";

export default function DemoProgramExplorer() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("");
  const [field, setField] = useState("");
  const [sort, setSort] = useState("recommended");
  const [selected, setSelected] = useState<Program[]>([]);
  const [details, setDetails] = useState<Program | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [selectionMessage, setSelectionMessage] = useState("");
  const load = useCallback(async () => {
    try {
      setPrograms(await api.programs());
      setError(null);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    api
      .programs(controller.signal)
      .then((result) => {
        setPrograms(result);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, []);
  const filtered = programs.filter(
    (p) =>
      (!country || p.country === country) &&
      (!field || p.study_area === field) &&
      `${p.university} ${p.program} ${p.city}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  if (sort === "cost")
    filtered.sort(
      (a, b) =>
        a.tuition_eur + a.living_cost_eur - (b.tuition_eur + b.living_cost_eur),
    );
  if (sort === "name")
    filtered.sort((a, b) => a.university.localeCompare(b.university));
  const toggle = (program: Program) => {
    setSelectionMessage("");
    if (selected.some((p) => p.id === program.id))
      setSelected(selected.filter((p) => p.id !== program.id));
    else if (selected.length < 3) setSelected([...selected, program]);
    else
      setSelectionMessage(
        "Your comparison has three programs. Remove one to add another.",
      );
  };
  return (
    <Reveal>
      <div className="page-heading">
        <div>
          <span className="eyebrow">OPEN UP THE POSSIBILITIES</span>
          <h1>Demo Recommendations</h1>
          <p>
            Explore, look closer, and compare the details that matter to you.
          </p>
        </div>
        <Link className="button button-outline button-small" href="/dashboard">
          My recommendations <ArrowRight size={15} />
        </Link>
      </div>
      <DemoNotice />
      <div className="explore-toolbar">
        <label className="search-input">
          <Search size={18} />
          <span className="sr-only">
            Search programs, universities or cities
          </span>
          <input
            placeholder="A program, a university, a possibility…"
            maxLength={100}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <label className="filter-select">
          <SlidersHorizontal size={16} />
          <span className="sr-only">Country</span>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="filter-select">
          <span className="sr-only">Study area</span>
          <select value={field} onChange={(e) => setField(e.target.value)}>
            <option value="">All study areas</option>
            {studyAreas.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="explore-results-bar">
        <p aria-live="polite">
          <strong>{filtered.length}</strong> demonstration programs{" "}
          <span>· A starting point for exploration</span>
        </p>
        <label className="sort-select">
          <ArrowDownUp size={14} />
          <span className="sr-only">Sort programs</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="recommended">Catalog order</option>
            <option value="cost">Annual cost: low to high</option>
            <option value="name">University: A to Z</option>
          </select>
        </label>
      </div>
      {error && <ErrorNotice message={error} retry={() => void load()} />}
      {busy ? (
        <Loading text="Opening up the possibilities…" />
      ) : (
        <div className="program-grid">
          {filtered.map((p) => (
            <ProgramCard
              key={p.id}
              program={p}
              selected={selected.some((s) => s.id === p.id)}
              onCompare={() => toggle(p)}
              onDetails={() => setDetails(p)}
            />
          ))}
        </div>
      )}
      {!busy && !error && filtered.length === 0 && (
        <div className="empty-panel">
          <Compass size={35} />
          <h2>A wider search might help.</h2>
          <p>No demonstration programs match these filters.</p>
          <button
            className="button button-outline button-small"
            onClick={() => {
              setQuery("");
              setCountry("");
              setField("");
            }}
          >
            Clear filters
          </button>
        </div>
      )}
      <p className="selection-message" role="status">
        {selectionMessage}
      </p>
      {selected.length > 0 && (
        <div className="comparison-tray">
          <div>
            <strong>{selected.length} of 3 programs selected</strong>
            <span>
              {selected.map((p) => p.university.split(" ")[0]).join(" · ")}
            </span>
          </div>
          <button
            className="text-button"
            onClick={() => {
              setSelected([]);
              setCompareOpen(false);
            }}
          >
            Clear
          </button>
          <button
            disabled={selected.length < 2}
            className="button button-primary button-small"
            onClick={() => {
              setCompareOpen(true);
              setTimeout(
                () =>
                  document
                    .getElementById("comparison")
                    ?.scrollIntoView({
                      behavior: window.matchMedia(
                        "(prefers-reduced-motion: reduce)",
                      ).matches
                        ? "instant"
                        : "smooth",
                      block: "start",
                    }),
                0,
              );
            }}
          >
            Compare side by side <ArrowRight size={15} />
          </button>
        </div>
      )}
      {compareOpen && selected.length >= 2 && (
        <section
          className="panel comparison-section"
          id="comparison"
          tabIndex={-1}
        >
          <div className="section-bar">
            <h2>A closer look, side by side.</h2>
            <button
              className="icon-button"
              onClick={() => setCompareOpen(false)}
              aria-label="Close comparison"
            >
              <X size={20} />
            </button>
          </div>
          <p className="comparison-scroll-hint">Swipe across to compare every program.</p>
          <div className="table-scroll" role="region" aria-label="Program comparison" tabIndex={0}>
            <table>
              <caption>
                Fictional programs. All financial figures and indices are
                synthetic.
              </caption>
              <thead>
                <tr>
                  <th scope="col">What matters</th>
                  {selected.map((p) => (
                    <th scope="col" key={p.id}>
                      {p.university}
                      <small>{p.program}</small>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    label: "Destination",
                    value: (p: Program) => `${p.city}, ${p.country}`,
                  },
                  {
                    label: "Annual tuition",
                    value: (p: Program) => euro(p.tuition_eur),
                  },
                  {
                    label: "Annual living costs",
                    value: (p: Program) => euro(p.living_cost_eur),
                  },
                  {
                    label: "Annual total",
                    value: (p: Program) =>
                      euro(p.tuition_eur + p.living_cost_eur),
                  },
                  {
                    label: "Duration",
                    value: (p: Program) => `${p.duration_months} months`,
                  },
                  { label: "Language", value: (p: Program) => p.language },
                  {
                    label: "Academic intensity (synthetic)",
                    value: (p: Program) => `${p.academic_index}/100`,
                  },
                  {
                    label: "Career index (synthetic)",
                    value: (p: Program) => `${p.career_index}/100`,
                  },
                  {
                    label: "Experience index (synthetic)",
                    value: (p: Program) => `${p.experience_index}/100`,
                  },
                ].map(({ label, value }) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    {selected.map((p) => (
                      <td key={p.id}>{value(p)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {details && (
        <ProgramDialog program={details} close={() => setDetails(null)} />
      )}
    </Reveal>
  );
}

"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Banknote,
  Check,
  ChevronDown,
  Compass,
  GraduationCap,
  Info,
  LoaderCircle,
  MapPin,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Target,
} from "lucide-react";
import { useProfile } from "@/components/providers";
import { ProgramMark } from "@/components/program-card";
import { DemoNotice, ErrorNotice, Loading, Reveal } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import {
  euro,
  priorityLabels,
  sampleProfile,
  type Profile,
  type Recommendations,
  type Weights,
} from "@/lib/types";

const ComparisonChart = dynamic(() => import("@/components/comparison-chart"), {
  ssr: false,
  loading: () => <div className="chart-placeholder">Loading comparison…</div>,
});

export default function DashboardPage() {
  const { profile, loading, save } = useProfile();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const demo = async () => {
    setBusy(true);
    setError(null);
    try {
      await save(sampleProfile);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };
  if (loading) return <Loading text="Opening your workspace…" />;
  if (!profile)
    return (
      <Reveal>
        <div className="page-heading">
          <div>
            <span className="eyebrow">A WORLD OF POSSIBILITY</span>
            <h1>Your next chapter starts here.</h1>
            <p>A thoughtful workspace for one of your biggest decisions.</p>
          </div>
        </div>
        <div className="welcome-panel">
          <div className="welcome-compass">
            <Compass size={88} strokeWidth={1} />
          </div>
          <span className="eyebrow">LET’S GET YOUR BEARINGS</span>
          <h2>Make room for a clearer direction.</h2>
          <p>
            Tell us what you want to study and what matters to you. We’ll help
            you explore the tradeoffs, with a ranking you can understand.
          </p>
          <div className="hero-actions">
            <Link href="/profile" className="button button-primary">
              Build my profile <ArrowRight size={17} />
            </Link>
            <button
              disabled={busy}
              onClick={demo}
              className="button button-outline"
            >
              {busy ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <Sparkles size={17} />
              )}
              Try a sample profile
            </button>
          </div>
          <DemoNotice />
        </div>
        {error && <ErrorNotice message={error} />}
      </Reveal>
    );
  return <PersonalDashboard key={profile.id} profile={profile} />;
}

function PersonalDashboard({ profile }: { profile: Profile }) {
  const [data, setData] = useState<Recommendations | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weights, setWeights] = useState<Weights>({ ...profile.weights });
  const [editing, setEditing] = useState(false);
  const [openRank, setOpenRank] = useState<number | null>(1);
  const load = useCallback(
    async (next?: Weights) => {
      try {
        setData(await api.recommend(profile.id, next));
        setError(null);
      } catch (error) {
        setError(errorMessage(error));
      } finally {
        setBusy(false);
      }
    },
    [profile.id],
  );
  useEffect(() => {
    let active = true;
    api
      .recommend(profile.id)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((error: unknown) => {
        if (active) setError(errorMessage(error));
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [profile.id]);
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  const refresh = (next?: Weights) => {
    setBusy(true);
    setError(null);
    void load(next);
  };
  const apply = async () => {
    setBusy(true);
    setError(null);
    await load(weights);
    setEditing(false);
  };
  const best = data?.results[0];
  return (
    <Reveal>
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR NEXT CHAPTER, IN FOCUS</span>
          <h1>A little more clarity, {profile.name}.</h1>
          <p>
            Here’s how your study possibilities line up with what matters to
            you.
          </p>
        </div>
        <Link href="/profile" className="button button-outline button-small">
          <SlidersHorizontal size={15} />
          Edit my profile
        </Link>
      </div>
      <div className="journey-banner">
        <div className="journey-icon">
          <Compass size={27} strokeWidth={1.4} />
        </div>
        <div>
          <span className="eyebrow">YOUR DIRECTION</span>
          <h2>
            {profile.study_area} <span>abroad</span>
          </h2>
          <p>
            {profile.countries.length
              ? profile.countries.join(" · ")
              : "Open to all six demonstration destinations"}
          </p>
        </div>
        <Link href="/explore" className="button button-white button-small">
          Keep exploring <ArrowUpRight size={16} />
        </Link>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <span>
            <GraduationCap size={17} />
            Within your criteria
          </span>
          <strong>
            {data ? data.considered.toString().padStart(2, "0") : "—"}
            <small>programs</small>
          </strong>
          <p>Field, destination & budget matched</p>
        </div>
        <div className="stat-card">
          <span>
            <Banknote size={17} />
            Your annual budget
          </span>
          <strong>
            {euro(profile.annual_budget_eur)}
            <small>EUR / year</small>
          </strong>
          <p>Tuition and living costs combined</p>
        </div>
        <div className="stat-card">
          <span>
            <Target size={17} />
            Top decision-ranking score
          </span>
          <strong>
            {best ? (best.score * 100).toFixed(1) : "—"}
            <small>/ 100</small>
          </strong>
          <p>Relative fit · not an admission probability</p>
        </div>
      </div>
      {error && <ErrorNotice message={error} retry={() => refresh(weights)} />}
      <div className="dashboard-grid">
        <section className="ranking-section">
          <div className="section-bar">
            <div>
              <h2>Your shortlist, with perspective.</h2>
              <p>Ranked around your priorities. Explained along the way.</p>
            </div>
            <button
              className="icon-button"
              aria-label="Refresh rankings"
              disabled={busy}
              onClick={() => refresh(weights)}
            >
              <RefreshCw size={17} className={busy ? "spin" : ""} />
            </button>
          </div>
          <DemoNotice compact />
          {busy && <Loading text="Weighing your possibilities…" />}
          {!busy && data?.results.length === 0 && (
            <div className="empty-panel">
              <Compass size={32} />
              <h3>Let’s widen the horizon.</h3>
              <p>
                No programs fit all your filters. Try another destination, a
                different field, or a higher annual budget.
              </p>
              <p>
                {data.excluded_over_budget} field and destination matches exceed
                your annual cap.
              </p>
              <Link
                className="button button-primary button-small"
                href="/profile"
              >
                Adjust my profile <ArrowRight size={15} />
              </Link>
            </div>
          )}
          {!busy &&
            data?.results.map((item) => (
              <article
                className={`rank-card ${item.rank === 1 ? "top-rank" : ""}`}
                key={item.program.id}
              >
                <div className="rank-card-head">
                  <span className="rank-number">
                    {String(item.rank).padStart(2, "0")}
                  </span>
                  <ProgramMark program={item.program} size="small" />
                  <div className="rank-title">
                    <h3>{item.program.university}</h3>
                    <p>{item.program.program}</p>
                    <span>
                      <MapPin size={12} />
                      {item.program.city}, {item.program.country}
                    </span>
                  </div>
                  <div className="rank-score">
                    <strong>
                      {(item.score * 100).toFixed(1)}
                      <small>/100</small>
                    </strong>
                    <span>Decision score</span>
                  </div>
                </div>
                <div className="rank-card-meta">
                  <span>
                    <Banknote size={14} />
                    <strong>{euro(item.annual_cost_eur)}</strong> / year
                  </span>
                  <span className="within-budget">
                    <Check size={13} />
                    {euro(item.budget_remaining_eur)} below cap
                  </span>
                  <button
                    className="text-button"
                    aria-expanded={openRank === item.rank}
                    aria-controls={`rank-details-${item.rank}`}
                    onClick={() =>
                      setOpenRank(openRank === item.rank ? null : item.rank)
                    }
                  >
                    Why this fit{" "}
                    <ChevronDown
                      size={14}
                      className={openRank === item.rank ? "rotate" : ""}
                    />
                  </button>
                </div>
                {openRank === item.rank && (
                  <div
                    className="rank-explanation"
                    id={`rank-details-${item.rank}`}
                  >
                    <span className="eyebrow">THE FACTORS BEHIND THE FIT</span>
                    {item.factors
                      .filter((f) => f.weight > 0)
                      .map((factor) => (
                        <div className="factor" key={factor.criterion}>
                          <span className="factor-dot" />
                          <div>
                            <strong>
                              {factor.label}{" "}
                              <small>
                                {Math.round(factor.weight * 100)}% priority
                              </small>
                            </strong>
                            <p>{factor.explanation}</p>
                          </div>
                        </div>
                      ))}
                    <p className="factor-note">
                      Ordered by weighted closeness to the ideal, relative to
                      the worst option. Costs and indices are illustrative.
                    </p>
                  </div>
                )}
              </article>
            ))}
          {data && (
            <p className="results-footnote">
              <Info size={14} />
              {data.excluded_over_budget} excluded by budget ·{" "}
              {data.excluded_preferences} excluded by field or destination ·{" "}
              <Link href="/methodology">See methodology</Link>
            </p>
          )}
        </section>
        <aside className="dashboard-aside">
          <section className="panel priorities-panel">
            <div className="section-bar">
              <h2>Your decision lens</h2>
              <button
                className="icon-button"
                aria-label="Adjust ranking priorities"
                onClick={() => setEditing(!editing)}
                aria-expanded={editing}
              >
                <SlidersHorizontal size={17} />
              </button>
            </div>
            <p>What you value shapes what rises to the top.</p>
            {editing ? (
              <div className="priority-sliders">
                {(Object.keys(priorityLabels) as (keyof Weights)[]).map(
                  (key) => (
                    <label key={key}>
                      <span>
                        {priorityLabels[key]}
                        <strong>
                          {total ? Math.round((weights[key] / total) * 100) : 0}
                          %
                        </strong>
                      </span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={weights[key]}
                        onChange={(e) =>
                          setWeights({
                            ...weights,
                            [key]: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  ),
                )}
                <button
                  className="button button-primary button-small"
                  disabled={busy || total === 0}
                  onClick={() => void apply()}
                >
                  Recalculate <ArrowRight size={14} />
                </button>
                <button
                  className="text-button"
                  onClick={() => {
                    setWeights({ ...profile.weights });
                    refresh();
                    setEditing(false);
                  }}
                >
                  Restore profile priorities
                </button>
                <small>
                  Adjustments apply to this view. Save defaults in your profile.
                </small>
              </div>
            ) : (
              <div className="priority-bars">
                {(Object.keys(priorityLabels) as (keyof Weights)[]).map(
                  (key, i) => (
                    <div key={key}>
                      <span>
                        {priorityLabels[key]}
                        <strong>
                          {Math.round(
                            (data?.weights[key] ??
                              profile.weights[key] /
                                Object.values(profile.weights).reduce(
                                  (a, b) => a + b,
                                  0,
                                )) * 100,
                          )}
                          %
                        </strong>
                      </span>
                      <div className="bar-track">
                        <span
                          className={`bar-fill priority-${i}`}
                          style={{
                            width: `${(data?.weights[key] ?? profile.weights[key] / Object.values(profile.weights).reduce((a, b) => a + b, 0)) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  ),
                )}
              </div>
            )}
          </section>
          {data && data.results.length > 0 && (
            <section className="panel budget-panel">
              <div className="section-bar">
                <h2>The budget picture</h2>
                <span className="tag">EUR / year</span>
              </div>
              <p>Annual cost, side by side.</p>
              <ComparisonChart
                results={data.results}
                budget={profile.annual_budget_eur}
              />
              <div className="chart-legend">
                <span>
                  <i className="legend-tuition" />
                  Tuition
                </span>
                <span>
                  <i className="legend-living" />
                  Living costs
                </span>
              </div>
            </section>
          )}
          <section className="assistant-prompt">
            <span className="step-icon">
              <Sparkles size={21} />
            </span>
            <h3>Talk through your next step.</h3>
            <p>
              Need help making sense of the tradeoffs? Your local AI assistant
              is here to think it through.
            </p>
            <Link className="text-button" href="/assistant">
              Let’s talk it through <ArrowUpRight size={16} />
            </Link>
          </section>
        </aside>
      </div>
    </Reveal>
  );
}

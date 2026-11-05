"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  CircleUserRound,
  Compass,
  Globe2,
  LoaderCircle,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { useProfile } from "@/components/providers";
import { DemoNotice, ErrorNotice, Loading, Reveal } from "@/components/ui";
import {
  countries,
  euro,
  priorityLabels,
  sampleProfile,
  studyAreas,
  type ProfileInput,
  type Weights,
} from "@/lib/types";
import { errorMessage } from "@/lib/api";

export default function ProfilePage() {
  const { profile, loading, save, forget } = useProfile();
  if (loading) return <Loading text="Opening your profile…" />;
  return (
    <ProfileForm
      key={profile?.id ?? "new"}
      initial={profile ?? { ...sampleProfile, name: "", goals: "" }}
      hasProfile={!!profile}
      save={save}
      forget={forget}
    />
  );
}

function ProfileForm({
  initial,
  hasProfile,
  save,
  forget,
}: {
  initial: ProfileInput;
  hasProfile: boolean;
  save: (input: ProfileInput) => Promise<unknown>;
  forget: () => void;
}) {
  const router = useRouter();
  const [form, setForm] = useState<ProfileInput>({
    name: initial.name,
    study_area: initial.study_area,
    gpa: initial.gpa,
    annual_budget_eur: initial.annual_budget_eur,
    countries: [...initial.countries],
    goals: initial.goals,
    weights: { ...initial.weights },
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const update = <K extends keyof ProfileInput>(
    key: K,
    value: ProfileInput[K],
  ) => setForm((old) => ({ ...old, [key]: value }));
  const totalWeight = Object.values(form.weights).reduce((a, b) => a + b, 0);
  const submit = async (event: React.SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (totalWeight <= 0) {
      setError("Give at least one priority a value above zero.");
      return;
    }
    setBusy(true);
    try {
      await save({ ...form, name: form.name.trim(), goals: form.goals.trim() });
      router.push("/dashboard");
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Reveal>
      <div className="page-heading">
        <div>
          <span className="eyebrow">IT ALL STARTS WITH YOU</span>
          <h1>Your ambition. Your direction.</h1>
          <p>
            A few details help us turn possibilities into a more personal
            shortlist.
          </p>
        </div>
        <button
          className="button button-outline button-small"
          type="button"
          onClick={() =>
            setForm({
              ...sampleProfile,
              weights: { ...sampleProfile.weights },
              countries: [],
            })
          }
        >
          <Sparkles size={15} />
          Use sample profile
        </button>
      </div>
      <div className="profile-layout">
        <form onSubmit={submit} className="profile-form">
          <section className="panel form-section">
            <div className="form-section-title">
              <span className="step-icon">
                <CircleUserRound size={21} />
              </span>
              <div>
                <h2>A little about you</h2>
                <p>Your academic starting point.</p>
              </div>
              <span className="section-index">01</span>
            </div>
            <div className="form-grid">
              <label>
                Your first name
                <input
                  required
                  maxLength={80}
                  placeholder="e.g. Alex"
                  autoComplete="given-name"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                />
              </label>
              <label>
                Field of interest
                <select
                  value={form.study_area}
                  onChange={(e) =>
                    update(
                      "study_area",
                      e.target.value as ProfileInput["study_area"],
                    )
                  }
                >
                  {studyAreas.map((area) => (
                    <option key={area}>{area}</option>
                  ))}
                </select>
              </label>
              <label>
                GPA <span className="label-hint">on a 4.0 scale</span>
                <input
                  required
                  type="number"
                  min="0"
                  max="4"
                  step="0.01"
                  value={form.gpa}
                  onChange={(e) => update("gpa", e.target.valueAsNumber)}
                />
                <small>
                  Convert your grade to a 4.0 scale before entering it.
                </small>
              </label>
              <label>
                Annual budget <span className="label-hint">EUR</span>
                <input
                  required
                  type="number"
                  min="1000"
                  max="200000"
                  step="100"
                  value={form.annual_budget_eur}
                  onChange={(e) =>
                    update("annual_budget_eur", e.target.valueAsNumber)
                  }
                />
                <small>Include tuition and living expenses for one year.</small>
              </label>
            </div>
          </section>
          <section className="panel form-section">
            <div className="form-section-title">
              <span className="step-icon">
                <Globe2 size={21} />
              </span>
              <div>
                <h2>Where could you see yourself?</h2>
                <p>Select destinations, or leave all open.</p>
              </div>
              <span className="section-index">02</span>
            </div>
            <fieldset className="country-fieldset">
              <legend className="sr-only">Preferred countries</legend>
              <div className="country-options">
                {countries.map((country) => (
                  <label
                    className={`country-option ${form.countries.includes(country) ? "selected" : ""}`}
                    key={country}
                  >
                    <input
                      type="checkbox"
                      checked={form.countries.includes(country)}
                      onChange={(e) =>
                        update(
                          "countries",
                          e.target.checked
                            ? [...form.countries, country]
                            : form.countries.filter((c) => c !== country),
                        )
                      }
                    />
                    <span>{country}</span>
                    <Check size={15} />
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="goals-label">
              What does your next chapter look like?{" "}
              <span className="label-hint">optional</span>
              <textarea
                maxLength={1000}
                rows={3}
                placeholder="A research career? A new industry? Tell your assistant what you’re working toward…"
                value={form.goals}
                onChange={(e) => update("goals", e.target.value)}
              />
              <small>
                Shared with your local AI assistant. Goals do not change the
                mathematical ranking.
              </small>
            </label>
          </section>
          <section className="panel form-section">
            <div className="form-section-title">
              <span className="step-icon">
                <SlidersHorizontal size={21} />
              </span>
              <div>
                <h2>What matters most?</h2>
                <p>We normalize these priorities to a total of 100%.</p>
              </div>
              <span className="section-index">03</span>
            </div>
            <div className="priority-sliders">
              {(Object.keys(priorityLabels) as (keyof Weights)[]).map((key) => (
                <label key={key}>
                  <span>
                    {priorityLabels[key]}
                    <strong>
                      {totalWeight
                        ? Math.round((form.weights[key] / totalWeight) * 100)
                        : 0}
                      %
                    </strong>
                  </span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={form.weights[key]}
                    onChange={(e) =>
                      update("weights", {
                        ...form.weights,
                        [key]: Number(e.target.value),
                      })
                    }
                  />
                </label>
              ))}
            </div>
          </section>
          {error && <ErrorNotice message={error} />}
          <div className="form-bottom">
            <span>
              <ShieldCheck size={16} />
              Saved in your local backend
            </span>
            <button
              disabled={busy}
              className="button button-primary"
              type="submit"
            >
              {busy ? (
                <>
                  <LoaderCircle size={17} className="spin" />
                  Saving your profile…
                </>
              ) : (
                <>
                  {hasProfile ? "Update my direction" : "Find my direction"}
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </div>
        </form>
        <aside className="profile-aside">
          <div className="profile-compass-card">
            <Compass size={44} strokeWidth={1.2} />
            <span className="eyebrow">A PROFILE, NOT A BOX.</span>
            <h2>
              A good fit starts
              <br />
              with what matters
              <br />
              to you.
            </h2>
            <p>
              There’s no universal “best” program. There’s a set of tradeoffs
              that makes sense for your next chapter.
            </p>
            <div className="profile-summary">
              <span>YOUR ANNUAL BUDGET</span>
              <strong>
                {Number.isFinite(form.annual_budget_eur)
                  ? euro(form.annual_budget_eur)
                  : "—"}
              </strong>
              <small>Tuition + living expenses</small>
            </div>
          </div>
          <DemoNotice />
          <p className="privacy-note">
            This local MVP has no accounts. Your browser remembers only a
            profile ID. Use sample details on a shared machine.
          </p>
          {hasProfile && (
            <button type="button" className="text-button" onClick={forget}>
              Forget profile on this browser
            </button>
          )}
        </aside>
      </div>
    </Reveal>
  );
}

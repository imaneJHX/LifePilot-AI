"use client";

import Link from "next/link";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronRight,
  Compass,
  Globe2,
  GraduationCap,
  Layers3,
  Scale,
  Sparkles,
} from "lucide-react";
import { Brand, DemoNotice, Reveal, ThemeToggle } from "@/components/ui";

export default function Home() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Brand />
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link href="/explore">Explore programs</Link>
          <Link href="/methodology">Our approach</Link>
        </nav>
        <div className="header-actions">
          <ThemeToggle />
          <Link href="/dashboard" className="button button-dark button-small">
            Open workspace <ArrowUpRight size={15} />
          </Link>
        </div>
      </header>
      <main id="main-content">
        <section className="hero">
          <Reveal className="hero-copy">
            <span className="pill">
              <span className="status-dot" />A little direction. A world of
              possibility.
            </span>
            <h1>
              Your next chapter.
              <br />
              <span>A clearer direction.</span>
            </h1>
            <p className="hero-description">
              Big decisions deserve more than a search bar. Discover master’s
              programs abroad that align with your ambitions, your priorities,
              and your budget.
            </p>
            <div className="hero-actions">
              <Link href="/profile" className="button button-primary">
                Find my direction <ArrowRight size={18} />
              </Link>
              <Link href="/explore" className="button button-outline">
                Explore possibilities
              </Link>
            </div>
            <div className="hero-reassurance">
              <span>
                <Check size={14} />
                Your priorities come first
              </span>
              <span>
                <Check size={14} />
                Every ranking explained
              </span>
            </div>
            <div className="hero-footnote">
              <span className="small-line" /> Built for the decision, and the
              person behind it.
            </div>
          </Reveal>
          <Reveal className="hero-visual" delay={0.15}>
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="visual-grid" />
            <span className="orbit-label label-berlin">
              Berlin <span>52.52° N</span>
            </span>
            <span className="orbit-label label-porto">
              Porto <span>41.16° N</span>
            </span>
            <span className="orbit-point point-one" />
            <span className="orbit-point point-two" />
            <div className="direction-card">
              <div className="direction-top">
                <span>
                  <Compass size={17} /> YOUR STUDY COMPASS
                </span>
                <Sparkles size={17} />
              </div>
              <div className="compass-visual">
                <div className="compass-ring">
                  <span className="north">N</span>
                  <span className="east">E</span>
                  <span className="south">S</span>
                  <span className="west">W</span>
                  <div className="compass-cross" />
                  <div className="compass-needle" />
                  <div className="compass-center" />
                </div>
                <span className="compass-dot dot-a" />
                <span className="compass-dot dot-b" />
              </div>
              <h3>Possibility, with perspective.</h3>
              <p>
                Connect where you are
                <br />
                with where you want to go.
              </p>
              <div className="direction-bottom">
                <span>
                  <span className="status-dot" /> Guided by your priorities
                </span>
                <ArrowUpRight size={17} />
              </div>
            </div>
            <div className="floating-note note-top">
              <span className="floating-icon">
                <GraduationCap size={20} />
              </span>
              <div>
                <strong>Your ambition, in focus.</strong>
                <small>Find the right academic direction</small>
              </div>
            </div>
            <div className="floating-note note-bottom">
              <span className="floating-icon lilac">
                <Scale size={20} />
              </span>
              <div>
                <strong>See the tradeoffs.</strong>
                <small>Understand the why behind the fit</small>
              </div>
              <CheckCheck size={19} className="accent-text" />
            </div>
            <span className="visual-caption">
              A NEW WAY TO NAVIGATE WHAT’S NEXT
            </span>
          </Reveal>
        </section>
        <div className="landing-proof">
          <span>
            THOUGHTFUL DECISIONS,
            <br />
            <strong>FROM EVERY ANGLE.</strong>
          </span>
          <div>
            <Globe2 size={21} />
            <span>Explore across borders</span>
          </div>
          <div>
            <Layers3 size={21} />
            <span>Compare what matters</span>
          </div>
          <div>
            <Scale size={21} />
            <span>Understand every tradeoff</span>
          </div>
          <a href="#how-it-works" aria-label="See how it works">
            <ArrowDown size={20} />
          </a>
        </div>
        <section className="how-section" id="how-it-works">
          <div className="section-heading">
            <div>
              <span className="eyebrow">LESS OVERWHELM. MORE DIRECTION.</span>
              <h2>
                A big decision.
                <br />A more thoughtful process.
              </h2>
            </div>
            <p>
              Bring your ambition. We’ll help you put the possibilities into
              perspective, one clear step at a time.
            </p>
          </div>
          <div className="steps-grid">
            {[
              {
                step: "01",
                icon: Compass,
                title: "Start with you",
                copy: "Your background, your budget, your ideal next chapter. Set the priorities that make a decision yours.",
                link: "/profile",
                cta: "Build your profile",
              },
              {
                step: "02",
                icon: Globe2,
                title: "Open up the possibilities",
                copy: "Explore programs across countries, look closer at the details, and compare your shortlist side by side.",
                link: "/explore",
                cta: "Explore programs",
              },
              {
                step: "03",
                icon: Scale,
                title: "Make sense of the tradeoffs",
                copy: "See a transparent ranking based on what matters to you, with the reasoning behind every recommendation.",
                link: "/dashboard",
                cta: "See your workspace",
              },
            ].map(({ step, icon: Icon, title, copy, link, cta }) => (
              <article className="step-card" key={step}>
                <div>
                  <span className="step-icon">
                    <Icon size={24} />
                  </span>
                  <span className="step-number">{step}</span>
                </div>
                <h3>{title}</h3>
                <p>{copy}</p>
                <Link href={link}>
                  {cta}
                  <ChevronRight size={16} />
                </Link>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <span className="eyebrow">YOUR FUTURE IS PERSONAL.</span>
          <h2>Your decision support should be, too.</h2>
          <p>
            A clearer picture of your options starts with a little about you.
          </p>
          <Link href="/profile" className="button button-primary">
            Let’s find your direction <ArrowRight size={18} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <div>
          <Brand />
          <p>Clarity for your next chapter.</p>
        </div>
        <DemoNotice compact />
        <Link href="/methodology">
          Transparent by design <ArrowUpRight size={14} />
        </Link>
      </footer>
    </div>
  );
}

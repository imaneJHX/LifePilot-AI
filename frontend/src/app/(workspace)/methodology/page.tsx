import Link from "next/link";
import { ArrowRight, Scale } from "lucide-react";
import { DemoNotice } from "@/components/ui";

export default function Methodology() {
  return (
    <div className="methodology-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">TRANSPARENT BY DESIGN</span>
          <h1>You deserve to understand the why.</h1>
          <p>A clear look at how your priorities become a ranked shortlist.</p>
        </div>
      </div>
      <DemoNotice />
      <section className="panel prose-panel">
        <span className="step-icon">
          <Scale size={25} />
        </span>
        <h2>A decision-ranking score, explained.</h2>
        <p>
          LifePilot uses TOPSIS: the Technique for Order Preference by
          Similarity to Ideal Solution. It compares programs against the best
          and worst combinations of criteria in your current candidate set.
        </p>
        <ol>
          <li>
            <strong>Start with your constraints.</strong> We keep programs in
            your study area and selected countries whose annual tuition plus
            living costs fit your budget. An empty country selection means all
            six demonstration destinations.
          </li>
          <li>
            <strong>Build the comparison matrix.</strong> Annual cost is a cost
            criterion (less is better). Academic alignment, career outlook, and
            student experience are benefit criteria (more is better).
          </li>
          <li>
            <strong>Put criteria on a comparable scale.</strong> Divide each
            value by the Euclidean length of its column, then apply your
            priorities normalized to sum to one. A zero column contributes zero.
          </li>
          <li>
            <strong>Measure the tradeoffs.</strong> For each program, calculate
            Euclidean distances to the weighted ideal and worst points.
          </li>
          <li>
            <strong>Calculate the relative score.</strong> Distance from worst
            divided by the sum of both distances produces a value from 0 to 1,
            shown on a 100-point scale. Closer to the ideal means a higher
            score.
          </li>
        </ol>
        <div className="formula">
          score = distance from worst ÷ (distance to ideal + distance from
          worst)
        </div>
        <h3>What the criteria actually mean</h3>
        <p>
          <strong>Academic alignment</strong> is an illustrative formula: the
          GPA produces an intensity target of 60 + 10 × GPA. Alignment is 100
          minus the absolute difference between the program’s fictional
          academic-intensity index and that target. It is not a measure of
          academic eligibility or admission likelihood.
        </p>
        <p>
          <strong>Career and student-experience indices</strong> are synthetic
          fixture values. They do not represent employment statistics, surveys,
          or real university rankings. Your written goals are assistant context;
          they are not analyzed by TOPSIS.
        </p>
        <h3>How to read your result</h3>
        <p>
          A score of 85 means 0.85 relative closeness in this comparison. It
          does not mean an 85% chance of acceptance or an absolute 85% fit.
          Scores change with the comparison set and weights. Identical or single
          options score 50; tied options retain catalog order.
        </p>
        <p>
          Explanations show the input values, priority weights, and the leading
          weighted strengths. The API also returns each criterion’s distance
          components for inspection. Zero-weight criteria have no effect.
        </p>
        <h3>Costs and practical limits</h3>
        <p>
          All costs are illustrative annual amounts in EUR. Budget filtering
          includes tuition and living expenses for one year, rather than the
          full degree. Travel, visa fees, deposits, inflation, exchange rates,
          and scholarships are not modeled.
        </p>
        <p>
          This first version uses no live retrieval and makes no verified claims
          about real institutions. The AI assistant is separate from
          deterministic ranking and cannot modify your profile or run tools.
        </p>
        <Link href="/profile" className="button button-primary button-small">
          Set your priorities <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}

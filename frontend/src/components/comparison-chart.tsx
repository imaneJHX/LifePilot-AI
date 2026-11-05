"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { euro, type RankedProgram } from "@/lib/types";

export default function ComparisonChart({
  results,
  budget,
}: {
  results: RankedProgram[];
  budget: number;
}) {
  const data = results
    .slice(0, 6)
    .map((item) => ({
      name: item.program.university.split(" ")[0],
      tuition: item.program.tuition_eur,
      living: item.program.living_cost_eur,
    }));
  return (
    <div
      className="chart-container"
      role="img"
      aria-label={`Annual tuition and living cost comparison against your ${euro(budget)} budget. Exact values appear in the ranked program list.`}
    >
      <ResponsiveContainer width="100%" height={235} minWidth={0}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 4, left: -20, bottom: 2 }}
          barSize={22}
          accessibilityLayer
        >
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="name"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--muted)", fontSize: 10 }}
            interval={0}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--muted)", fontSize: 10 }}
            tickFormatter={(value: number) => `${value / 1000}k`}
            domain={[0, (max: number) => Math.max(max, budget) * 1.12]}
          />
          <Tooltip
            cursor={{ fill: "var(--surface-hover)" }}
            contentStyle={{
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              fontSize: 12,
            }}
            formatter={(value, name) => [
              euro(Number(value)),
              name === "tuition" ? "Tuition" : "Living costs",
            ]}
          />
          <ReferenceLine
            y={budget}
            stroke="var(--accent)"
            strokeDasharray="4 4"
            label={{
              value: "Your cap",
              position: "insideTopRight",
              fill: "var(--accent)",
              fontSize: 10,
            }}
          />
          <Bar dataKey="living" stackId="cost" fill="#c6d5e2" />
          <Bar
            dataKey="tuition"
            stackId="cost"
            fill="#247d71"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

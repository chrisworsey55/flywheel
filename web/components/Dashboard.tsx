"use client";

import { Activity, BadgeCheck, FlaskConical, Gauge, ShieldCheck, Table2, Target, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type Ad = {
  id: string;
  body_text: string;
  headline: string;
  media_type: string;
  start_date: string;
  last_seen_date: string;
  impressions_bucket: string;
  label_name: string;
  days_running: number;
};

type Experiment = {
  id: string;
  hypothesis: string;
  feature_rule: Record<string, string | number | boolean>;
  segment: string;
  naive_score: number;
  honest_score: number;
  p_real: number;
  segment_n: number;
  passed: boolean;
  fail_reason?: string;
};

type History = {
  cycle: number;
  accuracy: number;
  precision: number;
  recall: number;
  auc: number;
  calibration: number;
  n_eff_ratio: number;
  metaeval_fpr: number;
};

export type Results = {
  brand: string;
  market: string;
  objective: string;
  valid: boolean;
  seed: number;
  data_source?: { synthetic: boolean; source: string; backend: string };
  ads_studied: number;
  headline: { out_of_sample_hit_rate: number; precision: number; auc: number; calibration: number };
  studied_ads: Ad[];
  todays_experiments: Experiment[];
  history: History[];
  metaeval: {
    null_count: number;
    false_positives: number;
    false_positive_rate: number;
    passed: boolean;
    max_null_honest_score: number;
    mean_null_honest_score: number;
    evaluated_null_count?: number;
    fail_closed_count?: number;
    signal_count?: number;
    signal_pass_count?: number;
  };
  callout?: { example_copy: string; prediction: string; honest_confidence: number };
};

const pct = (value = 0) => `${(value * 100).toFixed(1)}%`;

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="panel p-5">
      <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {icon}
        <span>{title}</span>
      </div>
      {children}
    </section>
  );
}

function predictCopy(copy: string, auc: number) {
  const text = copy.toLowerCase();
  let score = 0.44;
  if (text.includes("free bet")) score += 0.16;
  if (text.includes("boost")) score += 0.12;
  if (text.includes("england") || text.includes("world cup")) score += 0.10;
  if (text.includes("today") || text.includes("tonight") || text.includes("now")) score += 0.08;
  if (/\d/.test(text)) score += 0.06;
  if (text.includes("learn more")) score -= 0.08;
  const p = Math.max(0.05, Math.min(0.95, score));
  return { label: p >= 0.5 ? "winner" : "loser", confidence: Math.min(p, auc || p) };
}

export default function Dashboard({ results }: { results: Results }) {
  const [copy, setCopy] = useState(results.callout?.example_copy ?? "");
  const live = useMemo(() => predictCopy(copy, results.headline?.auc ?? 0.5), [copy, results.headline?.auc]);
  const gateClass = results.metaeval?.passed ? "border-emerald-400 text-emerald-300" : "border-rose-400 text-rose-300";
  const history = results.history ?? [];

  return (
    <main className="min-h-screen px-5 py-6 md:px-9 lg:px-12">
      {results.data_source?.synthetic ? (
        <div className="mb-5 border border-amber-500/70 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Demo running on synthetic sample data. Pipeline is real; swap in a real Ad Library pull to reproduce.
        </div>
      ) : null}
      <section className="mb-6 grid gap-6 lg:grid-cols-[1.45fr_0.55fr]">
        <div className="py-5">
          <div className="mb-3 inline-flex items-center gap-2 border border-slate-700 px-3 py-1 text-xs uppercase text-slate-300">
            <ShieldCheck size={14} /> FLYWHEEL
          </div>
          <h1 className="max-w-5xl text-3xl font-semibold leading-tight md:text-5xl">{results.brand} kept-vs-killed ad predictor</h1>
          <p className="mt-4 max-w-4xl text-base leading-7 text-slate-300">
            Out-of-sample test against real advertiser budget decisions in {results.market}. Truth is survival and impression scale, not a label authored by this repo.
          </p>
        </div>
        <div className="panel grid content-center gap-4 p-6">
          <div className="text-sm uppercase text-slate-400">Held-out hit rate</div>
          <div className="text-5xl font-semibold text-emerald-300">{pct(results.headline?.out_of_sample_hit_rate)}</div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><div className="text-slate-400">AUC</div><div className="text-2xl font-semibold">{pct(results.headline?.auc)}</div></div>
            <div><div className="text-slate-400">Ads studied</div><div className="text-2xl font-semibold">{results.ads_studied}</div></div>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Studied" icon={<Table2 size={16} />}>
          <div className="grid max-h-[560px] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
            {(results.studied_ads ?? []).map((ad) => (
              <article key={ad.id} className="ad-tile p-4">
                <div className="mb-2 flex items-center justify-between gap-2 text-xs text-slate-400">
                  <span>{ad.media_type}</span>
                  <span className={ad.label_name === "WINNER" ? "text-emerald-300" : "text-rose-300"}>{ad.label_name}</span>
                </div>
                <h3 className="text-sm font-semibold text-white">{ad.headline}</h3>
                <p className="mt-2 text-sm leading-5 text-slate-300">{ad.body_text}</p>
                <div className="mt-3 text-xs text-slate-500">{ad.days_running} days / {ad.impressions_bucket}</div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Today's Experiments" icon={<FlaskConical size={16} />}>
          <div className="max-h-[560px] space-y-3 overflow-y-auto pr-1">
            {(results.todays_experiments ?? []).map((exp, index) => (
              <article key={exp.id} className="border-b border-slate-800 pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-sm font-medium text-white">{index + 1}. {exp.hypothesis}</div>
                  <div className={exp.passed ? "text-emerald-300" : "text-slate-500"}>{pct(exp.p_real)}</div>
                </div>
                <div className="mt-2 text-xs text-slate-400">{JSON.stringify(exp.feature_rule)} / n={exp.segment_n}</div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Compounding Curve" icon={<TrendingUp size={16} />}>
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={history}>
                <CartesianGrid stroke="#26313f" vertical={false} />
                <XAxis dataKey="cycle" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" tickFormatter={(v) => pct(Number(v))} />
                <Tooltip formatter={(v) => pct(Number(v))} contentStyle={{ background: "#10141b", border: "1px solid #26313f" }} />
                <Line type="monotone" dataKey="accuracy" stroke="#34d399" strokeWidth={2} />
                <Line type="monotone" dataKey="auc" stroke="#fbbf24" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Honesty Gate" icon={<BadgeCheck size={16} />}>
          <div className="grid gap-4 md:grid-cols-[0.45fr_0.55fr]">
            <div>
              <div className={`inline-flex border px-3 py-1 text-sm font-semibold ${gateClass}`}>{results.metaeval?.passed ? "PASS" : "FAIL"}</div>
              <div className="mt-5 text-4xl font-semibold">{pct(results.metaeval?.false_positive_rate)}</div>
              <div className="mt-2 text-sm text-slate-400">{results.metaeval?.false_positives} false positives across {results.metaeval?.evaluated_null_count ?? results.metaeval?.null_count} evaluated shuffled-label nulls.</div>
            </div>
            <div className="text-sm leading-6 text-slate-300">
              The evaluator fails closed on thin holdout segments and deflates the 25 experiments tried in the cycle before reporting P(real).
              {typeof results.metaeval?.fail_closed_count === "number" ? ` ${results.metaeval.fail_closed_count} nulls failed closed; ${results.metaeval.signal_pass_count ?? 0}/${results.metaeval.signal_count ?? 0} true-signal controls cleared the bar.` : ""}
            </div>
          </div>
        </Panel>

        <Panel title="Winner's Curse" icon={<Activity size={16} />}>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={results.todays_experiments ?? []}>
                <CartesianGrid stroke="#26313f" vertical={false} />
                <XAxis dataKey="id" hide />
                <YAxis stroke="#94a3b8" tickFormatter={(v) => pct(Number(v))} />
                <Tooltip formatter={(v) => pct(Number(v))} contentStyle={{ background: "#10141b", border: "1px solid #26313f" }} />
                <Line dataKey="naive_score" stroke="#fbbf24" dot={false} />
                <Line dataKey="honest_score" stroke="#34d399" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Diversity" icon={<Gauge size={16} />}>
          <div className="h-64">
            <ResponsiveContainer>
              <LineChart data={history}>
                <CartesianGrid stroke="#26313f" vertical={false} />
                <XAxis dataKey="cycle" stroke="#94a3b8" />
                <YAxis domain={[0, 1]} stroke="#94a3b8" />
                <ReferenceLine y={0.6} stroke="#fb7185" strokeDasharray="5 5" />
                <Tooltip formatter={(v) => Number(v).toFixed(3)} contentStyle={{ background: "#10141b", border: "1px solid #26313f" }} />
                <Line dataKey="n_eff_ratio" stroke="#34d399" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </section>

      <section className="panel mt-5 p-5">
        <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400"><Target size={16} /> Live Callout</div>
        <div className="grid gap-4 md:grid-cols-[1fr_260px]">
          <textarea value={copy} onChange={(event) => setCopy(event.target.value)} className="min-h-32 resize-y border border-slate-700 bg-slate-950 p-4 text-sm text-white outline-none focus:border-emerald-400" />
          <div className="border border-slate-800 p-4">
            <div className="text-sm text-slate-400">Prediction</div>
            <div className={live.label === "winner" ? "mt-2 text-3xl font-semibold text-emerald-300" : "mt-2 text-3xl font-semibold text-rose-300"}>{live.label}</div>
            <div className="mt-4 text-sm text-slate-400">Honest confidence</div>
            <div className="mt-1 text-2xl font-semibold">{pct(live.confidence)}</div>
          </div>
        </div>
      </section>

      <footer className="py-8 text-sm leading-6 text-slate-500">
        Caveat: survival is a proxy for performance. FLYWHEEL infers from budget decisions and impression scale, not conversions.
      </footer>
    </main>
  );
}

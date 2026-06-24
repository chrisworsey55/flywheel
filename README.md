# FLYWHEEL

**A self-improving growth engine. Born from ATLAS.**

> It doesn't just generate growth ideas. It runs a roster of specialized agents that
> hypothesize, test against reality, reflect, and rewrite themselves - and it can prove
> which of its own findings are real instead of fooling itself.

---

## Lineage

FLYWHEEL is the second application of an architecture first built as **ATLAS** - a
self-improving, multi-agent *trading* system. ATLAS's insight was never "AI picks
stocks." It was **validation honesty**: a leakage-free, deflated evaluator that stops
a self-improving system from lying to itself about its own results. The market was the
adversary; you don't get to write its answers.

That exact failure mode is the dirty secret of every growth org on earth. They don't
lack ideas - they lack the ability to *trust their own measurement*. Leaky A/B tests,
attribution theatre, creative that wins in the test and dies in production.

FLYWHEEL repoints the ATLAS engine from markets to growth. Same loop. Same moat. New
substrate.

---

## The agents

Growth isn't one job, so it isn't one agent. FLYWHEEL runs a swarm of specialists,
each owning one stage of the loop:

| Agent | Owns | What it does |
|-------|------|--------------|
| **SCOUT** | Data | Studies real, un-authored signal - which campaigns a company *kept running vs. killed* - and turns it into features. No labels it could cheat from. |
| **AUGUR** | Hypotheses | Generates growth experiments: readable bets about which offers, framings, and segments win. 25 per cycle. |
| **GAMBIT** | Testing | Runs each hypothesis as an *out-of-sample prediction* against reality that already exists - no waiting for conversions. |
| **ARBITER** | Truth | The moat. A leakage-free, multiple-testing-deflated evaluator that *fails closed* - returns null rather than guess. Scores which findings are real. |
| **SCRIBE** | Reflection | Reads what hit and what missed, and rewrites the prompts/strategies of the agents that were wrong. This is how the swarm learns. |
| **WARDEN** | Honesty | Stress-tests ARBITER itself - "backtest the backtester" - by feeding it known-null experiments and measuring how often it's fooled. |
| **CURATOR** | Diversity | Keeps the swarm from collapsing into one idea (N_eff/N floor). Diverse hypotheses, not echo chambers. |

---

## The loop

```text
SCOUT      ->  feed real data (kept vs. killed signal)

AUGUR      ->  generate growth hypotheses

GAMBIT     ->  test them out-of-sample against reality

ARBITER    ->  score honestly (fail-closed, deflated)

SCRIBE     ->  reflect, rewrite the agents that were wrong

^__________________________________________________|

the swarm self-improves each cycle
```

**Self-improvement is defined as rising prediction accuracy on fresh, held-out *real*
data - not a number climbing on a function we wrote.** That distinction is the whole
point. Anyone can make a chart go up against their own answer key. FLYWHEEL gets
graded by reality.

---

## The moat: validation honesty

Every "AI for growth" tool generates ideas. FLYWHEEL is the only one built to **prove
which of its own ideas are real** before you spend on them:

- **Leakage-free.** Train on the past, freeze, predict the held-out future. The
  evaluator never sees what it's being tested on.
- **Deflated.** Corrects for the number of experiments tried - no winner's curse, no
  "we ran 25 things and one looked great."
- **Fail-closed.** Too little data? It returns *null*, not a confident guess.
- **Self-audited.** WARDEN feeds ARBITER pure-noise experiments and measures the
  false-positive rate. If the evaluator leaks, the run halts.

The provocation for any growth team: *point this at the experiments you already think
are working, and see how many survive honest validation.*

---

## Where it is today (honest status)

This repo is a working, runnable demonstration of the architecture. Being precise
about what's wired vs. what's next, because honesty is the product:

**Running now:**

- The full loop: study -> suggest -> test out-of-sample -> score -> select -> breed.
- ARBITER (honest, fail-closed, deflated evaluator) and WARDEN (backtest-the-backtester).
- CURATOR diversity control.
- Self-improvement via **evolutionary selection** - agents with different priors,
  bred by mutation/crossover across cycles, selected on held-out accuracy.
- Default substrate: ad-survival data (which ads a company kept alive vs. killed),
  pulled from the Meta Ad Library.

**Designed, next on the roadmap:**

- SCRIBE's full form: agents as LLMs that **rewrite their own prompts** on reflection,
  rather than evolving parameters. The evolutionary version is the proof-of-loop; the
  prompt-rewriting version is the upgrade.

**On the sample data:** the committed `data/raw/*.json` is a **synthetic fixture** so
the demo runs offline with zero credentials. The pipeline is real; swap in a real Ad
Library pull (`make fetch BRAND=...`) to reproduce on live data. Reported metrics on
the fixture (AUC, FPR) prove the pipeline computes correctly - they are not claims
about any real advertiser.

---

## Run it yourself

```bash
git clone https://github.com/<your-username>/flywheel.git
cd flywheel
make demo          # runs the engine on the synthetic sample, then the dashboard
make demo SEED=random   # proves results hold across draws, not cherry-picked
```

Point it at any advertiser with a public kept-vs-killed signal:

```bash
make fetch BRAND="Fanatics Sportsbook" MARKET="GB"
make run
```

---

## Where else the loop runs

FLYWHEEL needs only one thing: **real, un-authored outcome labels.** Anywhere a
public "kept vs. killed" signal exists, the loop applies:

- **Ad creative** - which ads survived 60+ days / scaled (Meta Ad Library).
- **App store** - which app updates and screenshots a publisher kept.
- **Pricing & landing pages** - which A/B variants survived (web archives).
- **Job postings** - which roles a company keeps reposting (real, urgent need).
- **Email** - which subject-line styles recur in public newsletter archives.

Same engine. Same honesty gate. Different reality to be graded by.

---

## Built by

Chris Worsey - two-time founder (CourseMatch -> UCAS; SportsIcon). FLYWHEEL is the
growth-substrate sibling of **ATLAS**, the self-improving trading system that ran the
same architecture against live markets.

*MIT licensed. Clone it, run it, try to break it.*

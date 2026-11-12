# Qyverix — Execution Plan

**Companion to [PRODUCT_STRATEGY.md](./PRODUCT_STRATEGY.md) · 2026-11-12**

This plan reconciles the two research resources and turns them into work you can schedule.

| | Resource 1: "Qyverix AI Security Engineering Stack" | Resource 2: "Autonomous security engineering platform" research |
|---|---|---|
| Core message | Don't trust one AI agent. Layer proven scanners, centralize findings in DefectDojo, and add AI remediation behind verification. | Don't build a scanner wrapper. Build the missing evidence → fix → verify layer. |
| Horizon | **Now.** Secure Qyverix's own code. | **Months.** Build a sellable product. |
| Risk if done alone | You end up operating eight tools and building no IP | You build product for months on an insecure codebase, with no real-world data |

**Resolution: run two tracks in parallel. Track A feeds Track B.**

```
 TRACK A — "Secure Qyverix now"  (Resource 1)          TRACK B — "Build Qyverix Security Intelligence" (Resource 2)
 ────────────────────────────────────────────          ─────────────────────────────────────────────────────────────
 Scanners in CI on all Qyverix repos         ──data──►  Baseline numbers + real findings for the eval harness
 DefectDojo as system of record              ──data──►  Ground truth for dedupe/fingerprinting design
 ZAP + Shannon/Strix against staging         ──data──►  Competitor teardown (§14.4 of the spec)
 Weekly security review                      ◄─product─ Each Track B release is dogfooded here first
```

Track A is cheap, takes about two weeks, and is the right thing to do regardless of the product. It also gives Track B the one thing the research says matters most: **real, held-out, real-world findings** (the Nephilex lesson: 2% recall on real fixes vs +89 on a benchmark it was tuned on).

---

## 1. Where each resource item ended up

| Item | Source | Decision | Where |
|---|---|---|---|
| OpenGrep (SAST) | R1, R2 | Adopt in both tracks | A1, spec §6 |
| Trivy + OSV-Scanner (SCA, containers, SBOM) | R1, R2 | Adopt | A1 |
| Gitleaks (secrets, incl. history) | R1, R2 | Adopt, plus a pre-commit hook | A1 |
| Checkov (IaC) | R1, R2 | Adopt | A1 |
| Zizmor (GitHub Actions) | R2 | Adopt | A1 |
| OWASP ZAP (DAST) | R1, R2 | Adopt, staging only | A3 |
| Shannon (AI pentest) | R1, R2 | **Evaluation only** (AGPL). Run against staging; don't embed in the product. | A3, B teardown |
| Strix (AI pentest) | R2 | Evaluate in Track A; optional evidence source in Track B | A3, B Phase 4 |
| DefectDojo | R1, R2 | **Track A system of record.** Track B exports to it rather than rebuilding it. | A2 |
| OWASP AppSec Agent | R1, R2 | Reference architecture (role separation) only | Spec §3.2 |
| Nephilex | R1, R2 | Watch list. Corrected facts in spec §0. | — |
| Mobb / Bugsy | R2 | Competitor; benchmark target | Spec §3 |
| Open-ASM (external attack surface) | R1 | **Deferred.** Out of scope until Track B Phase 4+. ⚠️ GPL-3.0 per R1 (unverified). | §6 below |
| Isolated remediation agent + verifier | R1, R2 | **Core Track B IP** | Spec §5.03 |
| Non-negotiable safeguards | R1, R2 | Adopt in both tracks | Spec §10 |
| 3-stage rollout (foundation → central → autonomous) | R1 | = Track A, then Track B | This doc |
| 4-phase product roadmap | R2 | = Track B phases | §3 below |
| Benchmarks (Juice Shop, OWASP Benchmark, AutoPenBench, SecureAgentBench, SecLLMHolmes, XBOW) | R1, R2 | Adopt; held-out discipline added | Spec §14 |
| Weekly security review | R1, R2 | Adopt | §4 below |
| RTX 3050 6 GB note | R1 | Scanners and triage model run locally; fixer and verifier models run on an API or GPU server | Spec §11 |
| Don't train a custom LLM; no Kubernetes for the MVP | R2 | Adopt | Spec §1, §7 |

---

## 2. Track A: Secure Qyverix now (weeks 1–3)

**Owner:** 1 engineer, part-time. **Cost:** compute only.

### A1 · Scanner foundation in CI (week 1)

On every PR and nightly, for every Qyverix repository:

| Check | Tool | Gate on PR? | Output |
|---|---|---|---|
| Secrets (diff + full history once) | Gitleaks | **Block** on new secrets | SARIF |
| SAST | OpenGrep (default security rulesets) | Warn first; block on high severity after triage | SARIF |
| Dependencies | OSV-Scanner + Trivy fs | Warn; block on critical *with fix available* | SARIF + SBOM (CycloneDX) |
| Container images | Trivy image | Warn | SARIF |
| IaC / Docker / Compose | Checkov + Trivy config | Warn | SARIF |
| CI workflows | Zizmor | **Block** on template injection and excessive permissions | SARIF |
| Pre-commit (developer machines) | Gitleaks | Local block | — |

Rules:
- Pin every action and image to a **commit SHA or digest**, not a tag.
- CI tokens get least-privilege `permissions:`.
- Upload all SARIF to GitHub code scanning (if available) **and** to DefectDojo.

**Exit:** every repo has a green or known-red baseline, and the existing findings are triaged into `fix`, `accept (with expiry)` or `false positive`.

### A2 · DefectDojo as the system of record (week 2)

- Deploy with Docker Compose on internal infrastructure. Don't expose it publicly. Use SSO if available.
- One *Product* per repo, one *Engagement* per CI pipeline, and import via the API on each run.
- Turn on deduplication and record the hash-code fields used per tool. **Track B needs this data** to design its fingerprinting.
- Weekly export of metrics (open by severity, mean time to remediate, FP rate per tool).

**Exit:** one place answers "what is open, who owns it, and is it actually fixed?"

### A3 · Runtime testing on staging (weeks 2–3)

- A staging environment with **disposable data** and dedicated test accounts: ≥2 users per role and ≥2 tenants. The same fixtures are reused by Track B's authz harness.
- ZAP automation-framework plan: authenticated baseline weekly, full active scan before releases.
- A Shannon Lite **and** Strix run against staging, each once, with a fixed model budget. Record per finding: true or false positive, time, cost, reproducible (y/n). This is the first real data point of the competitor teardown.
- Never run either against production.

**Exit:** a short report comparing ZAP vs Shannon vs Strix on Qyverix staging, covering precision, unique true positives, cost and runtime.

### A4 · Weekly security review (ongoing from week 2, 30 min)

Agenda:
1. New Critical/High findings since last week and their owners.
2. Findings past SLA.
3. Accepted risks expiring this month.
4. FP rate per tool; tune or disable noisy rules.
5. Track B: what last week's real findings teach the product (feeds the eval set).

Initial SLAs: Critical 7 days · High 30 days · Medium 90 days · secrets **rotated within 24 h** (not just removed from code).

---

## 3. Track B: Build Qyverix Security Intelligence

**Assumption:** a team of 2–3 engineers. Scale the timelines if that's different.

### B0 · Evaluation harness first (weeks 1–2, overlaps Track A)

| Task | Acceptance criterion |
|---|---|
| docker-compose for OWASP crAPI, VAmPI, Juice Shop with seeded multi-tenant users | `make targets-up` brings all three up with fixtures |
| Build **Qyverix-RealFix v0**: 30–50 real CVE-fix commits in Node/Python web repos (pre-fix commit + upstream patch + CWE) | Frozen, versioned and never used for tuning |
| Baseline runner: OpenGrep + Gitleaks + OSV + Trivy + ZAP on all targets | One command produces a precision/recall table |
| Metrics module (spec §14.2) | Outputs JSON + Markdown report |

### B1 · Intelligence foundation (weeks 3–6)

| Task | Acceptance criterion |
|---|---|
| Monorepo skeleton (layout below), FastAPI app, worker, Postgres, Redis, MinIO via compose | `docker compose up` gives a healthy stack |
| Unified Finding + Evidence schema (spec §9) and migrations | Round-trips SARIF from all 5 scanners |
| Normalizer + fingerprint/dedupe | Dedupe matches or beats DefectDojo on Track A data |
| tree-sitter indexing for TS/JS + Python | Indexes a 100k-LOC repo in < 5 min |
| Route + middleware extractors: Express, NestJS, FastAPI, Django | ≥95% of routes found on crAPI, VAmPI and 1 internal repo (manually verified) |
| Security graph v1: route → middleware → handler → ORM query → table | Query "routes reaching table X with no ownership predicate" returns correct results on crAPI |
| GitHub App: checks + summary comment | Runs on PRs in Qyverix repos (dogfood) |

**Milestone M1:** useful repository-wide security report with no LLM involved.

### B2 · Autonomous investigation (weeks 6–9)

| Task | Acceptance criterion |
|---|---|
| State machine (spec §8) with checkpointing, budgets and audit log | Kill a worker mid-job and it resumes from the last state |
| LiteLLM router + cost ledger | Cost per job and per state recorded |
| Triage state (small model) with typed output | Invalid output → 1 retry → escalate, never guessing |
| Staging sandbox runner (gVisor/rootless, no egress, reset per run) | Isolation test suite passes (no host socket, no egress, no token in env) |
| Differential multi-identity authz harness | Finds known BOLA on crAPI/VAmPI; **0 false Confirmed** |
| Injection reproducers (SQLi/NoSQLi/command) with deterministic oracles | Confirmed on Juice Shop known vulns |
| Memory v1: FP suppression with expiry, attempt history, resumability | A second scan of an unchanged repo costs < 10% of the first |

**Milestone M2:** the system separates *Hypothesis* from *Confirmed* with executed proof.

### B3 · Autonomous remediation (weeks 9–12)

| Task | Acceptance criterion |
|---|---|
| Root-cause state using graph + LLM | Patch location overlaps the upstream fix in ≥70% of RealFix cases |
| Patch state in isolated git worktree | Never touches the default branch |
| Gates G1–G4 (spec §5.03) | Each gate is unit-tested with a deliberately bad patch it must reject |
| Independent verifier (different model family, read-only) | Disagreement → NEEDS_HUMAN |
| PR generator from the evidence bundle | PR shows the reproducer before and after plus gate results |
| Ablation: G1-only vs G1–G4 | Report how many test-passing patches were insecure |

**Milestone M3 (go/no-go):** ≥60% secure repair rate, ≤5% regressions on MVP classes, held-out. If this fails, stop and fix before Phase 4. Don't add features.

### B4 · Differentiated intelligence (weeks 13–24)

- G5 variant search and G6 suppression detector.
- Automatic custom-rule generation from confirmed findings.
- Business-logic workflows: payments and refunds, invites, role changes, multi-step state.
- Strix as an optional evidence source (if the Track A teardown justifies it).
- IaC/CI coverage (Checkov, Zizmor) in the graph.
- Cost dashboard, GitLab support, a minimal Next.js UI.
- 2–3 design partners on staging.
- Public benchmark report v1.

### Proposed product repository layout

```
qyverix-security/
├── apps/
│   ├── api/                 # FastAPI: findings, evidence, jobs, GitHub App webhooks
│   ├── worker/              # job runner; state machine executor
│   └── web/                 # Next.js (Phase 4)
├── core/
│   ├── schema/              # Finding, Evidence, Job models + migrations
│   ├── orchestrator/        # state machine, budgets, audit log
│   ├── router/              # model routing + cost ledger (LiteLLM)
│   ├── memory/              # versioned facts, FP suppressions, invariants
│   └── policy/              # autonomy, target allowlist, destructive-action denylist
├── intel/
│   ├── indexer/             # tree-sitter
│   ├── extractors/          # express, nestjs, fastapi, django
│   └── graph/               # security graph build + queries
├── signals/                 # adapters: opengrep, osv, trivy, gitleaks, checkov, zizmor, zap, strix
├── verify/
│   ├── sandbox/             # isolated runner
│   ├── authz_harness/       # differential multi-identity testing
│   └── reproducers/         # injection oracles
├── remediate/
│   ├── rootcause/
│   ├── patcher/
│   ├── gates/               # G1–G6
│   └── pr/
├── eval/
│   ├── targets/             # compose files for crAPI, VAmPI, Juice Shop
│   ├── realfix/             # frozen held-out dataset
│   └── runner/              # metrics + ablations
└── deploy/compose/
```

---

## 4. Calendar view

| Week | Track A | Track B |
|---|---|---|
| 1 | A1 scanners in CI | B0 eval targets + RealFix dataset |
| 2 | A2 DefectDojo · A4 weekly review starts | B0 baseline report |
| 3 | A3 ZAP + Shannon/Strix teardown on staging | B1 skeleton, schema, normalizer |
| 4–6 | Steady state; triage | B1 indexer, extractors, graph, GitHub App → **M1** |
| 6–9 | Dogfood M1 on Qyverix repos | B2 state machine, sandbox, authz harness → **M2** |
| 9–12 | Dogfood M2 | B3 remediation + gates → **M3 go/no-go** |
| 13–24 | Replace overlapping Track A pieces with Qyverix where it measurably wins | B4 + design partners |

---

## 5. Detection coverage roadmap

Resource 2's "what it must detect" list, assigned to phases:

| Category | Track A (now, tools) | Track B MVP (proved & fixed) | Track B later |
|---|---|---|---|
| Injection (SQLi, NoSQLi, command, XSS) | OpenGrep, ZAP | ✅ | — |
| Broken access control / IDOR / BOLA / tenant isolation | ZAP (weak), Shannon/Strix | ✅ **flagship** | — |
| SSRF | OpenGrep, ZAP | Hypothesis/Corroborated only | Confirmed via OOB callback oracle |
| Auth flaws: JWT, session fixation, OAuth | OpenGrep, ZAP | — | ✅ Phase 4 |
| Rate-limit bypass | ZAP (partial) | — | ✅ Phase 4 |
| Business logic: payments, privilege escalation, workflow skipping | Shannon/Strix, manual | Partial (role escalation) | ✅ Phase 4 |
| Dependency CVEs, malicious packages | OSV, Trivy | Reachability via graph | Malicious-package heuristics |
| Secrets (code + history) | Gitleaks | Signal only | Auto-rotation guidance |
| IaC, Docker, cloud misconfiguration | Checkov, Trivy | — | ✅ Phase 4 (in graph) |
| CI/CD (GitHub Actions) | Zizmor | — | ✅ Phase 4 |
| External attack surface | — | — | Open-ASM evaluation (post-Phase 4) |

---

## 6. Deferred on purpose

- **Open-ASM / external attack surface:** a different buyer and a different problem. Revisit after M3. Verify its license (reported GPL-3.0) before any use.
- **Custom security LLM:** no.
- **Kubernetes / microservices:** no, until there's load that needs them.
- **Polished dashboard:** not before M3.
- **Auto-merge:** never.

---

## 7. Decisions needed from you

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| 1 | Where should the product code live? | A new repo, e.g. `qyverix/qyverix-security` (private) | B1 |
| 2 | Team size and who owns Track A | 1 part-time on Track A; 2–3 on Track B | Timeline |
| 3 | Which Qyverix repos and staging env are in scope for Track A | All active repos; one shared staging | A1, A3 |
| 4 | Model provider(s) and monthly budget | One hosted provider for fixer, a different family for verifier, local small model for triage; set a hard monthly cap | B2 |
| 5 | Hosted vs self-host first | Hosted GitHub App for design partners; keep self-host path | B1 |
| 6 | Design partners | 2–3 teams with Node/Python multi-tenant APIs + staging | B4 |
| 7 | Shannon usage policy | Evaluation only, unless legal approves otherwise | A3, B4 |

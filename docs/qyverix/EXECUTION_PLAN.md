# Qyverix Security Intelligence — Execution Plan

**Version 2 · 2026-11-12 · companion to [PRODUCT_STRATEGY.md](./PRODUCT_STRATEGY.md)**

> **The path:** build it as a Qyverix product → run it on Qyverix's own code → design partners → paying clients → *then* YC, with usage data in hand.
> **The first product:** continuous authorization and tenant-isolation assurance for multi-tenant B2B SaaS, in TypeScript/JavaScript first.

---

## 1. How the three resources fit together

| | Resource 1: security stack | Resource 2: platform research | Resource 3: market reality check |
|---|---|---|---|
| Core message | Layer proven scanners, centralize findings, put AI fixes behind verification | Build the missing evidence → fix → verify layer, not a scanner wrapper | That pitch is crowded. Narrow to application-specific invariants and authorization. |
| What it gives this plan | The tools Qyverix runs on its own code now | The architecture, evidence model and benchmarks | The wedge, the first customer, and the order of work |
| Risk if followed alone | Operating eight tools, no IP | A broad platform nobody can tell apart from funded competitors | A narrow tool with no foundation under it |

**What changed from version 1 of this plan:**

1. **The wedge is narrower.** Not "find, prove and fix everything". The first product is one promise: *your tenants cannot see each other's data, and we re-prove it on every pull request.*
2. **The build order flipped.** The invariant gate ships before automated fixing. Fix generation is where the funded competitors and GitHub are strongest. Assurance on every PR is the part to own first, and it is sellable without auto-fix.
3. **TypeScript/JavaScript first.** Python follows. Nothing else until one stack works properly.
4. **Customer discovery runs alongside the build**, with a kill criterion. A crowded market proves interest in the category, not demand for this wedge.
5. **The path is staged with gates:** product → clients → YC.

---

## 2. The three stages

| Stage | When | Outcome | Gate to move on |
|---|---|---|---|
| **1. Build and dogfood** | Weeks 1–12 | The invariant gate and proof-carrying fixes work on TS/JS apps, and run on Qyverix's own repositories | Held-out targets met (§3.4) **and** discovery confirms the wedge (§4) |
| **2. Design partners → paying clients** | Months 4–9 | 3–5 external teams run it on every PR. The first of them pay. | Paying clients with retained weekly use (§5) |
| **3. Scale, then YC** | After clients | More languages and bug classes. A YC application built on usage data. | YC readiness checklist (§6) |

Timelines assume 2–3 engineers. Scale them if the team is different.

---

## 3. Stage 1: build and dogfood (weeks 1–12)

Three workstreams run in parallel.

```
 A. Secure Qyverix now          B. Build the product                 C. Customer discovery
 (scanner stack, Resource 1)    (wedge first, Resources 2 + 3)       (validate before over-building)
 ───────────────────────────    ────────────────────────────────    ──────────────────────────────
 real findings + staging  ───►  eval data, fixtures, dogfood target
                                working demo on real code      ───►  shown in interviews
                                                               ◄───  what teams actually fear / would pay for
```

### 3.1 Workstream A: secure Qyverix now (weeks 1–3, then steady state)

One engineer, part-time. This is worth doing regardless of the product, and it produces the real-world data the product needs.

**A1 · Scanners in CI on every Qyverix repository (week 1)**

| Check | Tool | PR gate | Output |
|---|---|---|---|
| Secrets (diff, plus full history once) | Gitleaks | **Block** new secrets | SARIF |
| SAST | OpenGrep | Warn; block high severity after triage | SARIF |
| Dependencies | OSV-Scanner + Trivy fs | Block critical with a fix available | SARIF + CycloneDX SBOM |
| Container images | Trivy image | Warn | SARIF |
| IaC, Docker, Compose | Checkov + Trivy config | Warn | SARIF |
| CI workflows | Zizmor | **Block** template injection and excess permissions | SARIF |
| Developer machines | Gitleaks pre-commit | Local block | — |

Pin actions and images to a commit SHA or digest. Give CI tokens least-privilege `permissions:`.

**A2 · DefectDojo as the system of record (week 2).** Docker Compose, internal only. One product per repo, imports from CI. Record the dedupe fields per tool, because workstream B's fingerprinting is designed from this data.

**A3 · Runtime testing on staging (weeks 2–3).** A staging environment with disposable data and seeded identities: at least two users per role and two tenants. The product's harness reuses the same fixtures. Run ZAP weekly. Run Shannon Lite and Strix once each with a fixed budget, **for evaluation only**, and record true/false positives, cost, time and reproducibility. Never point any of them at production.

**A4 · Weekly security review (30 minutes, from week 2).** New Critical/High findings and owners; findings past SLA; accepted risks about to expire; false-positive rate per tool; what the week's real findings teach the product.
Starting SLAs: Critical 7 days · High 30 days · Medium 90 days · leaked secrets **rotated within 24 hours**.

### 3.2 Workstream B: build the product

| Weeks | Build | Acceptance criterion |
|---|---|---|
| **1–2** · Foundations | Evaluation harness: crAPI, VAmPI and Juice Shop in docker-compose. **TenantBench v0**: two small multi-tenant TS/JS apps with seeded authorization bugs and their fixes, half frozen. **RealFix v0**: 30–50 real CVE-fix commits in JS/TS web repos, frozen. Baseline run of OpenGrep + Gitleaks + OSV + Trivy + ZAP. Repo skeleton, schema, GitHub App skeleton. TS/JS indexer with route and middleware extraction for Express, NestJS and Next.js. | One command produces the baseline table. ≥95% of routes found on the test apps, checked by hand. |
| **3–4** · Graph and findings | Security graph v1: route → middleware → handler → query → table and tenant key. Scanner adapters and normalizer. Reachability. States *Suspected* and *Corroborated*. PR summary comment. | The query "routes that reach a tenant-owned table with no ownership check" is correct on TenantBench. Dedupe is at least as good as DefectDojo on workstream A data. **M1: a useful report with no LLM involved.** |
| **5–6** · Invariants and proof | Application model and `.qyverix/invariants.yml`, proposed from the graph and API spec, confirmed by a human. Disposable environment runner (compose from repo, seeded identities, no egress). Differential multi-identity harness. Evidence capture (request/response, DB side effects). State *Reproduced*. | Finds the seeded tenant-isolation and IDOR bugs on the **frozen** half of TenantBench and on crAPI/VAmPI, with **zero false Reproduced**. **M2.** |
| **7–8** · The PR gate | Change-impact selection: a graph diff picks the invariants affected by each PR. Required status check. Coverage report with uncovered routes listed. Incomplete runs reported as incomplete. Injection reproducers as the second bug family. | Seeded regression PRs are blocked before merge. The check finishes in under 10 minutes on the test apps (a target to validate). A timed-out run never reports clean. **M3: first shippable product.** |
| **9–10** · Proof-carrying fixes | Root cause from the graph. Patch in an isolated worktree. Gates G1–G4. An independent verifier on a different model family, read-only. Draft PR built from the evidence bundle. States *Fixed* and *Verified*. | ≥60% secure repair rate on seeded authorization bugs, ≤5% regressions, on held-out cases. Each gate rejects a deliberately bad patch in its unit test. **M4.** |
| **11–12** · Real-world validation | Run on Qyverix's repositories and on 2–3 friendly external repositories, with written permission. Compare against Semgrep/OpenGrep, GitHub agentic autofix and one pentest agent on the same cases. Write up results and limitations. | A report with precision, authorization coverage, repair rate, cost and time. **Go/no-go for stage 2.** |

**Order of value.** After week 8 there is a product worth showing: it blocks a tenant-isolation regression before merge and proves it with a replayable request. Weeks 9–10 add fixing on top. If time slips, protect weeks 5–8.

### 3.3 Product repository layout

```
qyverix-security/
├── apps/
│   ├── api/                 # FastAPI: findings, evidence, jobs, GitHub App webhooks
│   ├── worker/              # job runner; state machine executor
│   └── web/                 # Next.js (stage 2)
├── core/
│   ├── schema/              # Finding, Evidence, Job models + migrations
│   ├── orchestrator/        # state machine, budgets, audit log
│   ├── router/              # model routing + cost ledger
│   ├── memory/              # versioned facts, suppressions with expiry
│   └── policy/              # autonomy, target allowlist, destructive-action denylist
├── intel/
│   ├── indexer/             # tree-sitter (TS/JS first)
│   ├── extractors/          # express, nestjs, nextjs; then fastapi, django
│   ├── graph/               # security graph build, queries, per-commit diff
│   └── impact/              # change-impact selection
├── invariants/
│   ├── model/               # identities, roles, tenants, resources
│   ├── proposer/            # drafts invariants from graph + API spec
│   └── compiler/            # invariants → harness tests
├── signals/                 # adapters: opengrep, osv, trivy, gitleaks, checkov, zizmor, zap
├── verify/
│   ├── sandbox/             # disposable environment runner
│   ├── authz_harness/       # differential multi-identity testing
│   └── reproducers/         # injection oracles
├── remediate/               # rootcause, patcher, gates (G1–G6), pr
├── eval/
│   ├── targets/             # crAPI, VAmPI, Juice Shop
│   ├── tenantbench/         # our seeded multi-tenant apps (half frozen)
│   ├── realfix/             # frozen real CVE-fix commits
│   └── runner/              # metrics, baselines, ablations
└── deploy/compose/
```

### 3.4 Stage 1 exit targets

All measured on held-out data. Targets are starting points to revisit after the week 1–2 baseline.

| Metric | Target |
|---|---|
| Evidence-backed precision (true positives ÷ Reproduced) | ≥95% |
| Authorization coverage on TenantBench (boundaries tested ÷ boundaries in the model) | ≥90% |
| Seeded authorization bugs found on the frozen half | Beat every baseline tool |
| Secure repair rate (authorization bugs) | ≥60% |
| Regression rate of Verified fixes | ≤5% |
| Verification accuracy (Verified findings that are really fixed) | ≥98% |
| Incomplete scans reported as clean | 0 |
| Cost and time per verified fix | Reported |

---

## 4. Workstream C: customer discovery (weeks 1–4, then ongoing)

Resource 3's sharpest point: a team might want "a complete autonomous security engineer", or might pay sooner for "tenant isolation never regresses". Those are different businesses, and only customers can say which.

**Who:** 15–20 CTOs or lead engineers at B2B SaaS companies with a multi-tenant product, roughly 5–50 engineers, and no dedicated AppSec hire.

**Ask about the past, not the product:**
1. Have you had a tenant-isolation or authorization bug, a near miss, or a pentest finding of that kind? What happened?
2. How do you check today that one customer can't reach another's data? Who owns it?
3. What security tools do you pay for? What do you ignore from them?
4. What did your last pentest or SOC 2 / enterprise security questionnaire cost you in time and money?
5. Would you connect a staging environment and a repository to a tool that tests this on every PR? What would stop you?

**Signals that the wedge is real:**
- A specific incident, near miss or failed customer security review.
- Hand-written authorization tests they find painful to maintain.
- Willingness to connect staging for a trial.
- An existing budget line it could replace (pentests, a scanner nobody reads).

**Kill criterion.** If fewer than about a third of interviews show at least two of those signals by week 4, don't change the technology. Change the wedge. The fallbacks, in order: proof-carrying fixes on top of scanners the customer already runs; then software agencies that manage many client codebases.

By week 6 there is a working demo on real code to show in these conversations.

---

## 5. Stage 2: design partners → paying clients (months 4–9)

| Step | What happens | Evidence collected |
|---|---|---|
| Recruit 3–5 design partners | From the discovery interviews. Multi-tenant TS/JS (or Python) product, staging available, an engineer who will give weekly feedback. | Signed permission and scope |
| Onboard | Connect the repo, bootstrap the disposable environment, confirm the proposed invariants in one working session | Time to first Reproduced or first "all invariants hold" result |
| Run on every PR for 4–6 weeks | Free pilot with a stated end date and success criteria agreed up front | Violations caught before merge, false blocks, check time, fix PRs merged |
| Convert | Paid plan for those who met the criteria | Paying clients; reasons from those who decline |
| Harden | Python support, hybrid deployment (cloud control plane, workers in the customer's environment), SSO and audit export, minimal web UI | — |

**Pricing:** don't fix a number yet. Test per-repository and per-developer monthly pricing in the pilot conversations, and anchor against what the team already spends on pentests.

**Build during stage 2, driven by partner demand only:** gates G5–G6, automatic rule generation from past findings, payment and workflow-state invariants, Checkov/Zizmor signals in the graph, the cost dashboard.

**Gate to stage 3:** at least three paying clients, weekly active use on PRs retained for two months, and at least a handful of real invariant violations caught before merge in client code.

---

## 6. Stage 3: scale, then YC

Apply only when these are true. They are what separates Qyverix from a roadmap and a demo:

- [ ] The product is complete for its wedge: invariant gate and proof-carrying fixes, in two language stacks.
- [ ] Paying clients, with retention data.
- [ ] Real violations caught before merge in client code, with their consent to cite them (anonymized if needed).
- [ ] A published held-out benchmark against Semgrep/OpenGrep, GitHub agentic autofix and one pentest agent, with methodology.
- [ ] Clear numbers: precision, authorization coverage, secure repair rate, cost per verified fix.
- [ ] A one-sentence difference from Corgea, ZeroPath, Gecko, Winfunc and MindFort that a client has said in their own words.
- [ ] A decision on structure: stays a Qyverix product line, or spins out as its own company for the application.

Expansion after that, in order: more languages (Python is already done by then; next Java/Go by client demand), broader bug classes (auth flows, SSRF with out-of-band oracles, rate limiting), then IaC/CI/cloud in the graph. External attack surface stays out until clients ask.

---

## 7. Where each resource item landed

| Item | From | Decision |
|---|---|---|
| OpenGrep, Trivy, OSV-Scanner, Gitleaks, Checkov, Zizmor | R1, R2, R3 | Workstream A now; signals inside the product |
| OWASP ZAP | R1–R3 | Workstream A on staging; baseline in evaluation |
| DefectDojo | R1, R2 | Workstream A system of record; the product exports to it |
| Shannon (AGPL) | R1–R3 | Evaluation only. Not embedded. |
| Strix (Apache-2.0) | R2, R3 | Evaluation now; optional evidence source later |
| CodeQL | R3 | Not bundled (license). Accept a customer's own SARIF. |
| OWASP AppSec Agent | R1, R2 | Reference for role separation only |
| Nephilex | R1, R2 | Watch list. Its 2% held-out recall is why evaluation is held-out. |
| Mobb / Bugsy | R2 | Competitor |
| Corgea, ZeroPath, Gecko, Winfunc, MindFort, Tolmo; 0.security, OpenHack, Casco | R3 | Funded competitors. Teardown where access is possible. They are the reason the wedge is narrow. |
| GitHub agentic autofix | R3 | Standing baseline. It verifies with CodeQL, not with an exploit. |
| Application-specific invariants | R3 | **The entry wedge** (weeks 5–8) |
| Repository-to-runtime graph | R2, R3 | Weeks 1–4, incremental per commit |
| Proof-carrying patches, five states | R1–R3 | Weeks 9–10. States: Suspected, Corroborated, Reproduced, Fixed, Verified. |
| Change-impact intelligence | R3 | Weeks 7–8, inside the PR gate |
| Gate for AI-written changes | R3 | Positioning for the same PR gate. Not a separate build. |
| Persistent memory, model routing | R2 | Minimal in stage 1 (suppressions with expiry, cost ledger); deepen in stage 2 |
| Benchmarks: Juice Shop, crAPI, VAmPI, AutoPenBench, SecureAgentBench, SecLLMHolmes, VulnGym, JITVul | R1–R3 | Evaluation harness. SecRepoBench (C/C++) is reference only. |
| Open-ASM, external attack surface | R1 | Deferred |
| Weekly security review | R1, R2 | Workstream A4 |
| "Never report clean on timeout" | R3 | Hard rule, tested in weeks 7–8 |
| RTX 3050 6 GB | R1, R3 | Scanners and evidence run locally. Models through an API. No local-inference requirement. |

---

## 8. What not to build

- A generic multi-agent framework with many overlapping agents.
- Another dashboard that aggregates scanner alerts.
- A chatbot that explains CVEs.
- A fixer that doesn't prove its fixes.
- Support for every language before one works properly.
- A home-grown SAST engine, or a custom security LLM.
- A compliance platform.
- Anything that attacks production, or merges its own patches.
- Kubernetes or microservices before load demands them.

---

## 9. Decisions needed from you

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| 1 | Does Qyverix have its own multi-tenant TS/JS application to dogfood on? If not, whose is the first real target? | Use a Qyverix app if one exists; otherwise a friendly team's staging | Weeks 5–6, 11–12 |
| 2 | Where does the product code live? | A new private repository (this one is your profile repo) | Week 1 |
| 3 | Team: who builds, and who owns workstream A and the interviews? | 2–3 engineers on the build; one part-time on A; you lead the interviews | Timeline |
| 4 | Model providers and a hard monthly budget | One provider for fixing, a different family for verifying, a cap from day one | Weeks 9–10 |
| 5 | Which Qyverix repositories and staging environment are in scope for workstream A | All active repositories; one shared staging | Week 1 |
| 6 | Who are the first 15–20 interview targets | Start from your own network of SaaS CTOs | Weeks 1–4 |

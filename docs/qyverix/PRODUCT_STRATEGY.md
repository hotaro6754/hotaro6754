# Qyverix — Autonomous Security Engineering Platform

**Product strategy, architecture and evaluation plan**
Research checked: 2026-11-12

> **One-line thesis.** Qyverix should not be another detector or another AI pentester. It should be the system that turns a *suspicion* into *evidence*, the evidence into a *fix*, and the fix into a *verified, reviewable pull request*, across a whole repository and its running application.

---

## 0. Corrections to the earlier research notes

Before building on the earlier notes, these claims were re-checked. Treat everything marked ⚠️ as unverified until someone confirms it from the primary source.

| Claim in earlier notes | Status | Note |
|---|---|---|
| SecureAgentBench: 105 tasks, best correct-and-secure rate 15.2% | ✅ Confirmed | arXiv 2509.22097. Best agent was SWE-agent with DeepSeek-V3.1. Average is below 10%. A later version of the paper (*SecureVibeBench*, C/C++ OSS-Fuzz tasks) reports different numbers, so don't mix the two. |
| AutoPenBench: 33 tasks, 21% autonomous vs 64% assisted | ✅ Confirmed | arXiv 2410.03225. Code: `lucagioacchini/auto-pen-bench`. |
| AutoPT: PSM state machine, 22% → 41% | ✅ Confirmed | arXiv 2411.01236. Single benchmark, GPT-4o-mini. ⚠️ The IEEE TIFS venue was not confirmed. |
| SecLLMHolmes: 228 scenarios, 8 LLMs, high FPR | ✅ Confirmed | IEEE S&P 2024, arXiv 2312.12575. The models date from 2023–24, so the exact numbers are dated, but the failure modes still apply. |
| Shannon is AGPL-3.0, ~50k stars | ✅ Confirmed (secondary sources) | The open-source edition is "Shannon Lite" (AGPL-3.0). Shannon Pro is commercial. **AGPL affects how Qyverix can embed it** (see §9). |
| Strix: autonomous exploitation, self-hosted Docker | ✅ Confirmed | Apache-2.0, bring-your-own LLM key. Star counts vary widely between snapshots. Don't cite one. |
| OWASP AppSec Agent: 4 agents, Lab project, 1 contributor | ✅ Mostly confirmed | ~15 stars, not 20. The current docs use different role names (`code_reviewer`, `pr_reviewer`, `threat_modeler`, a run-tests-after-fix role, and an `fp_adversary` false-positive filter). |
| IEEE Access systematic review (208 studies; 91.3% / 11.1% / 5.3%) | ⚠️ Not verified | A 2025 review by Germano et al. with this framing is cited elsewhere, but the venue, study count and percentages were not confirmed. Check DOI `10.1109/ACCESS.2025.3631363` before quoting. The direction (detection-heavy, repair-light) agrees with other reviews: Zhou et al., 58 studies; an SLR of 227 detection studies. |
| "Nephilex" (early alpha, 2% recall) | ❌ Could not find | No repository, website or listing found under this name. Remove it from the comparison unless someone has a working link. |
| Repository-level detection paper (IEEE TSE 2026) and assertion-guided analysis (IEEE 2026) | ⚠️ Not verified | Plausible, but not checked. |
| Practitioner survey (158 respondents, 88% / 63%) | ⚠️ Vendor survey | Use only as directional evidence. |

**Rule for this document:** cite a number only if it is ✅. Everything else is a hypothesis we will test ourselves (§7).

---

## 1. Where the market actually is

The research and the competitive scan agree on one pattern:

> **Finding vulnerabilities is getting cheaper. Completing the security lifecycle is not.**

| Stage | Who does it well today | What is still broken |
|---|---|---|
| Detect (SAST/SCA/secrets/IaC) | OpenGrep/Semgrep, Trivy, OSV-Scanner, Gitleaks, Checkov, Snyk | Noise. No exploitability. File-level or rule-level context. |
| Prove (DAST / pentest) | ZAP, Strix, Shannon | Separate from code findings. Slow (~1–1.5 h per run for Shannon), costly, and the runs are not reproducible. |
| Fix | Dependency bumps (Snyk, OSV guided remediation); AI fixers | Agents produce "working but insecure" patches (SecureAgentBench). |
| Verify fix | Almost nobody, end to end | "The scanner stopped complaining" gets treated as "fixed". |
| Manage | DefectDojo, GitLab, Aikido | Aggregates reports, but has no reasoning about cause or fix. |

**The gap Qyverix should own is the connective tissue:** one evidence chain that runs from detection to proof to fix to re-proof, kept per repository over time.

---

## 2. Six differentiating opportunities

### 01 · Evidence-first vulnerability intelligence *(highest priority)*

LLMs produce convincing descriptions of vulnerabilities that don't exist, and they flag already-patched code (SecLLMHolmes). So the core product object is the **evidence bundle**, not the report.

Every finding carries:

- the exact location (file, symbol, line range, commit SHA);
- a source-to-sink trace (from the static engine, not from the LLM);
- the attacker-controlled input and preconditions (role, auth state, feature flags);
- a reproducer (HTTP request sequence, unit test, or PoC script);
- the observed impact (response diff, data leaked, state changed);
- provenance (which tool or agent produced each claim, model and version, prompt hash);
- the remediation and retest history.

Three states, enforced by the system and never by model self-assessment:

| State | Required evidence | UI treatment |
|---|---|---|
| **Confirmed** | A reproducer ran and an impact oracle passed | Red, can block a merge |
| **Corroborated** | ≥2 independent signals agree (e.g. a taint path plus a reachable route plus a matching DAST response), but no exploit ran | Amber |
| **Hypothesis** | One signal, or LLM reasoning only | Grey. Never shown as a vulnerability. |

A finding can only move up a state through an executed artifact. An LLM can *propose* a promotion. It cannot *perform* one.

### 02 · Whole-repository security graph *(high priority)*

Detection is moving from the function level to the repository level, and the hard bugs (IDOR/BOLA, tenant leaks, privilege escalation) cross several components. Build and continuously update a **security graph**:

```
Route ──► Middleware chain ──► Handler ──► Service ──► Query/ORM ──► Table / tenant column
  │            │ (authn? authz? which roles?)             │
  └── OpenAPI / GraphQL schema                            └── Sensitive-field tags (PII, secrets, money)
Package ──► CVE (OSV) ──► Reachable call sites
IaC resource ──► Exposure (public? IAM scope?) ──► Service it hosts
```

Build the graph from deterministic sources: tree-sitter parsing, language call graphs, framework route extractors (Express/Nest, FastAPI/Django, Spring, Rails), OpenGrep taint output, SBOMs, and Checkov/Trivy IaC output. The LLM **queries** the graph. It does not build it from raw text.

This graph is what makes "reachable CVE", "missing ownership check" and "this endpoint is public in prod" answerable questions.

### 03 · Security-verified autonomous remediation *(high priority, most visible)*

SecureAgentBench shows that agents often produce patches that are functionally correct and still insecure. So remediation is a pipeline with **independent gates**, not a single agent call:

```
Reproduce ─► Root-cause ─► Patch (isolated worktree) ─► Gates ─► PR
                                                          │
            ┌─────────────────────────────────────────────┤
            │ G1 Build + type-check + existing tests       │
            │ G2 Original reproducer now FAILS to exploit  │  ← re-exploit, not just re-scan
            │ G3 Original scanner rule no longer fires     │
            │ G4 Full SAST/secret/IaC diff: no NEW findings│  ← catches "fixed one, added one"
            │ G5 Variant check: same bug class elsewhere   │
            │ G6 Patch-minimality & suppression detector   │  ← rejects `# nosemgrep`, deleted tests,
            │                                              │    disabled routes, broad try/except
            └─────────────────────────────────────────────┘
```

- The **verifier is a different process** from the fixer: a different prompt, ideally a different model, and no write access.
- G2 needs a reproducer from Opportunity 01. If none exists, the PR is labeled *unverified-fix*.
- The PR body is generated from the evidence bundle: the finding, the reproducer before and after, the gate results, residual risk and rollback steps.
- **Humans merge.** There is never an auto-merge for a security patch.

### 04 · Business-logic and authorization testing

This is where generic scanners are weakest, and where a repository-aware system has a real advantage.

Example: user A owns order 123 and user B owns order 456. `GET /orders/{id}` checks authentication but not ownership. A scanner that only checks "is auth present?" misses this.

Build an application-aware testing engine that reasons about:

- **User roles and permissions.** These come from the security graph (middleware, decorators, policy files) and, where needed, a short human-confirmed role model.
- **Tenant boundaries.** Which tables and columns carry `tenant_id` / `org_id`, and whether every query path filters on them.
- **Resource ownership.** Which resources belong to which principal, and whether each read, write and delete path checks it.
- **Multi-step workflows.** Checkout, refunds, invites, password reset, approval chains: skipped steps, replayed steps, reordered steps.
- **State and quantity invariants.** Negative quantities, double-spend, race conditions on balance or stock.

**Method: a differential, multi-identity harness.**

1. Provision ≥2 test users per role and ≥2 tenants in a disposable staging DB (seeded by fixture scripts the user approves).
2. For every route in the graph, record the legitimate request as user A.
3. Replay it as user B, as the same role in another tenant, as a lower role, and unauthenticated.
4. **The oracle is deterministic.** Compare status, body, and DB side effects against the expected access matrix. The LLM proposes the matrix and interesting mutations; the harness decides pass or fail.
5. A failure produces a **Confirmed** finding with a reproducer that already works as a regression test.

This turns BOLA/IDOR, the #1 OWASP API risk, into something a machine can find, prove and regression-test. It is the feature most likely to make Qyverix noticeably better than Strix or Shannon on real SaaS codebases.

### 05 · Deterministic orchestration with cost-aware model routing

The evidence: a structured state machine roughly doubled task completion over free-form ReAct (AutoPT: 22% → 41%). Open-source agents' issue trackers show sandbox races, malformed tool arguments and cost-accounting bugs.

- **Workflow engine first, LLM second.** Every job is a durable state machine (Temporal, or a Postgres-backed job table plus Redis): `DISCOVER → CORRELATE → TRIAGE → REPRODUCE → ROOT_CAUSE → PATCH → VERIFY → PR → RETEST`. The LLM makes bounded decisions *inside* a state, and its tool calls are schema-validated.
- **Resumable.** Each state checkpoints its inputs and outputs, so a crash or rate limit resumes the job instead of restarting it.
- **Model routing by task:**
  - triage and dedupe: a small or local model;
  - root cause and patch: a strong coding model;
  - verification: a *different* model family from the fixer;
  - summaries and PR text: a small model.
- **Hard budgets per job** (tokens, wall-clock, tool calls), with cost recorded per finding. "Cost per confirmed finding" and "cost per verified fix" are first-class metrics.
- **Caching.** Graph queries, embeddings and scanner outputs are keyed by commit SHA, so incremental PR scans only touch changed subgraphs.

### 06 · Governance, audit trail and repository security memory

**Governance (policy-as-code):**
- Per-repo policy says which stages may run autonomously, which targets may be actively exploited, and which branches PRs may target.
- A destructive-action allowlist for exploitation: no `DROP`, no mass email, no payment calls. Enforce it with a proxy, not with prompts.
- Every agent action is appended to a tamper-evident log: tool, arguments, output hash and model.

**Security memory (per repository):**
- Accepted risks and false positives, each with a reason and an expiry date, so the same noise doesn't come back every scan.
- Learned project conventions ("authz is done by `@require_owner`", "all queries go through `TenantScopedRepo`"). These are turned into **custom OpenGrep rules** automatically and proposed in a PR.
- Fix history. When a bug class recurs, the system suggests a framework-level guard instead of another point fix.

That last point is the compounding advantage: **every confirmed finding becomes a deterministic rule.** Over time Qyverix gets cheaper and more precise on each customer's codebase, which a stateless agent cannot do.

---

## 3. Positioning

| Product | Their centre of gravity | Qyverix's angle |
|---|---|---|
| Strix / Shannon | Autonomous exploitation of a running app | We consume exploitation as *one evidence source*, tie it to code, fix it, and re-prove it |
| Semgrep / OpenGrep, Snyk | Rule-based detection, dependency fixes | We add exploitability, cross-component reasoning and verified patches, and we generate rules |
| DefectDojo | Finding aggregation | We are the reasoning and remediation layer, and can export to DefectDojo instead of replacing it |
| Aikido / GitLab Security | Integrated commercial AppSec | Self-hostable, evidence-first, works on top of existing GitHub/GitLab |

**What we deliberately do not build:** our own CVE database (use OSV), our own generic SAST engine (use OpenGrep), our own DAST crawler (use ZAP), our own vulnerability-management UI at feature parity with DefectDojo, or network/external attack surface tooling (out of scope for v1).

---

## 4. MVP: the narrow wedge

Shipping a "full autonomous security engineer" first is how this fails. Pick a wedge where the evidence loop can be closed end to end:

> **MVP: authorization and injection bugs in TypeScript/Node and Python web APIs, found, proven, fixed and re-proven, delivered as GitHub PRs.**

Why this wedge:
- BOLA/IDOR and injection are high-impact, common in startups, and poorly covered by rule-only tools.
- Node and Python are where most new SaaS backends are written, and the research literature underrepresents them.
- Both bug classes have **deterministic oracles**: the differential access matrix, and the injection payload response or DB side effect.

**MVP scope:**

| In | Out (later) |
|---|---|
| Express/NestJS, FastAPI/Django route extraction | Java/Go/.NET |
| OpenGrep, Gitleaks, OSV-Scanner, Trivy (fs + image) as inputs | Full IaC, cloud posture |
| Security graph v1 (routes, middleware, handlers, ORM queries, tenant columns) | Cross-service and microservice graph |
| Multi-identity differential authz harness | Free-form AI pentest |
| Remediation pipeline with gates G1–G4 | G5 variant analysis, G6 advanced suppression detection |
| GitHub App: PR comments + fix PRs | GitLab, Bitbucket |
| SARIF + DefectDojo export | Own dashboard beyond a findings list |

---

## 5. Reference architecture

```
                 ┌──────────────── GitHub App (webhooks, checks, PRs) ────────────────┐
                 ▼                                                                    │
        ┌─────────────────┐     ┌────────────────────┐     ┌──────────────────────┐   │
        │ Job orchestrator │────►│ Scan workers       │────►│ Normalizer           │   │
        │ (durable state   │     │ OpenGrep, Gitleaks,│     │ SARIF/JSON → Finding │   │
        │  machine)        │     │ OSV, Trivy, ZAP    │     │ + dedupe/fingerprint │   │
        └───────┬─────────┘     └────────────────────┘     └──────────┬───────────┘   │
                │                                                     ▼               │
                │        ┌─────────────────────┐          ┌──────────────────────┐    │
                ├───────►│ Security graph       │◄────────►│ Evidence store        │    │
                │        │ (Postgres + pgvector │          │ (findings, artifacts, │    │
                │        │  or a graph DB)      │          │  audit log; S3/MinIO) │    │
                │        └─────────────────────┘          └──────────┬───────────┘    │
                │                                                     │               │
                ▼                                                     ▼               │
        ┌────────────────────────── Agent runtime ───────────────────────────────┐   │
        │ Triage │ Reproducer │ Root-cause │ Fixer │ Verifier (separate model)   │   │
        │ — schema-validated tools, per-job budget, model router                 │   │
        └──────────────┬──────────────────────────────────────┬─────────────────┘   │
                       ▼                                      ▼                     │
        ┌──────────────────────────────┐       ┌──────────────────────────────┐     │
        │ Disposable sandbox (per job) │       │ Disposable staging target    │     │
        │ git worktree, tests, rescans │       │ app + seeded DB + identities │     │
        │ no host docker socket,        │       │ egress-blocked, reset per run│     │
        │ egress allowlist only         │       └──────────────────────────────┘     │
        └──────────────────────────────┘                                            │
                       └──────────────── verified PR + evidence ────────────────────┘
```

**Stack choices:**

| Concern | Choice | Reason |
|---|---|---|
| Orchestration | Temporal (or a Postgres job table to start) | Durable, resumable, auditable |
| Queue/cache | Redis | Simple |
| Graph + findings | PostgreSQL (+ pgvector); move to a graph DB only if queries demand it | One database to operate |
| Artifacts | MinIO / S3 | Reproducers, logs, HAR files |
| Sandboxes | Firecracker/gVisor, or rootless containers | Isolation from untrusted repo code |
| LLM access | Model router over a hosted API plus optional local vLLM/Ollama | Cost and privacy flexibility |
| Interop | SARIF in and out, DefectDojo API | Coexist with customers' existing tooling |

**Hardware note.** An RTX 3050 6 GB is fine for scanners and a small local triage model. It is not enough for the fixer or verifier models. Use a hosted API or a separate GPU server for those.

---

## 6. Core data model: the evidence bundle

```yaml
finding:
  id: QYV-2026-000123
  fingerprint: sha256(rule_class + normalized_sink + route)   # stable across commits
  class: CWE-639            # Authorization Bypass Through User-Controlled Key (BOLA/IDOR)
  state: confirmed          # hypothesis | corroborated | confirmed | fixed-verified | accepted-risk
  location: { repo: org/api, commit: 9f2c1e7, file: src/orders/controller.ts, symbol: getOrder, lines: [41, 58] }
  graph_path: [ "GET /orders/:id", "authMiddleware", "OrdersController.getOrder", "OrderRepo.findById", "orders(tenant_id)" ]
  signals:
    - { source: graph, claim: "no ownership predicate on OrderRepo.findById", tool_version: qyv-graph 0.4 }
    - { source: opengrep, rule: qyv.authz.missing-owner-check, confidence: medium }
  reproducer:
    kind: http_sequence
    artifact: s3://evidence/QYV-2026-000123/repro.har
    oracle: "as user_b: status==200 AND body.order.owner_id == user_a.id"
    result: passed            # i.e. exploit succeeded
  impact: "User in tenant B can read any order in tenant A, including address and payment last4."
  remediation:
    pr: org/api#482
    gates: { G1: pass, G2: pass, G3: pass, G4: pass }
    retest: { reproducer_result: failed_as_expected, at: 2026-11-12T10:42Z }
  provenance:
    - { stage: root_cause, model: <router-selected>, prompt_sha: 3ab1…, tokens: 18233, cost_usd: 0.21 }
```

---

## 7. Evaluation plan: prove it before claiming it

The earlier notes' advice stands: **measure first.** Every public claim Qyverix makes should come from this harness.

**Targets:**

| Set | Purpose |
|---|---|
| OWASP Juice Shop, OWASP crAPI, VAmPI, DVWA | Known-vulnerable apps. crAPI and VAmPI are API/BOLA-heavy, a good fit for the MVP. |
| OWASP Benchmark (Java) | SAST precision and recall baseline (only for comparing the static layer) |
| AutoPenBench (33 tasks) | Pentest capability against a published baseline (21% / 64%) |
| SecureAgentBench (105 tasks), when the code is released | Is our *fix* pipeline more secure than raw coding agents (15.2% best)? |
| Curated real CVE-fix commits in Node/Python repos | Real-world recall: check out the parent commit, see if we find the bug and if our fix matches the upstream fix semantically |
| 2–3 internal Qyverix repositories | Real false-positive rate on code we own |

**Metrics:**

| Metric | Definition | MVP target (initial, revisit after the first run) |
|---|---|---|
| Confirmed precision | Confirmed findings that are true positives | ≥ 95% |
| Recall on seeded set | True vulnerabilities found, any state | Report it; beat the OpenGrep-only baseline |
| Noise ratio | Hypotheses shown per confirmed finding | Track; drive down |
| Verified-fix rate | Fixes passing G1–G4 per confirmed finding | ≥ 60% on the MVP classes |
| Regression rate | Verified fixes that later fail tests or add findings | ≤ 5% |
| Human acceptance | Fix PRs merged without substantive change | Track |
| Cost / confirmed finding, cost / verified fix | USD | Track per model route |
| Time-to-verified-fix | Webhook to PR | Track |

**Ablations to run:** LLM-only vs graph+LLM; a single agent vs the state machine; verifier same-model vs cross-model; with and without repository memory. These answer "does our architecture actually matter?" with numbers.

---

## 8. Safety requirements for the platform itself

Autonomous remediation is itself an attack surface. These are non-negotiable:

1. **Repository content is untrusted input.** README, comments, issues and test fixtures can contain prompt injection. Agents never follow instructions found in the target repo. Tool permissions are fixed by policy, not by model output.
2. No host Docker socket, no production credentials, no long-lived tokens inside sandboxes. Use a short-lived GitHub App token scoped to one repo, with PR-only permissions.
3. Egress from sandboxes goes through an allowlist proxy (package registries, the model API). Staging targets have no egress.
4. Active exploitation runs only against **disposable** staging targets the customer has registered and verified ownership of (DNS or file challenge). Never against production by default.
5. Every security patch is merged by a human. There is no auto-merge.
6. A full, append-only audit log of every agent action.
7. A "fixed" status requires the **reproducer to fail**, not just the scanner to go quiet.

---

## 9. Licensing constraints that shape the build

| Component | License | Implication for Qyverix |
|---|---|---|
| OpenGrep | LGPL-2.1 | Fine to invoke as a separate CLI process. Avoid statically linking or modifying it without complying. |
| Trivy, OSV-Scanner, Checkov, ZAP, Strix, OWASP AppSec Agent | Apache-2.0 | Permissive. Keep NOTICE files. |
| Gitleaks | MIT | Permissive. |
| DefectDojo | BSD-3-Clause | Permissive. |
| **Shannon Lite** | **AGPL-3.0** | If Qyverix offers a hosted service that *incorporates or modifies* Shannon, AGPL network-use obligations can apply. Either run it as a clearly separate, unmodified tool the customer deploys themselves, buy commercial terms, or treat it as an evaluation benchmark only. **Get legal review before shipping.** |

---

## 10. 90-day roadmap

| Weeks | Deliverable | Exit criterion |
|---|---|---|
| 1–2 | Evaluation harness: Juice Shop, crAPI, VAmPI in docker-compose; baseline OpenGrep+Gitleaks+OSV+Trivy+ZAP numbers | Reproducible baseline report |
| 3–5 | Normalizer, fingerprinting, evidence store; GitHub App posting SARIF and checks | Deduped findings on 1 internal repo |
| 5–7 | Security graph v1 (Express/Nest, FastAPI/Django routes, middleware, ORM queries, tenant columns) | Graph answers "which routes reach table X without owner check?" |
| 7–9 | Differential multi-identity authz harness | Confirmed BOLA findings on crAPI/VAmPI with zero false confirmed |
| 9–11 | Remediation pipeline (fixer, separate verifier, gates G1–G4), PR generation | ≥ 60% verified-fix rate on seeded authz/injection bugs |
| 11–12 | Repository memory v1 (FP suppression with expiry, auto-generated custom rules); first ablation report | Written results; decide whether to continue to Opportunity 05/06 depth |

**Do not build a polished dashboard before week 12.** The PR, the check run and the evidence bundle are the product until the numbers prove otherwise.

---

## 11. Open decisions for the team

1. **Deployment model.** Self-hosted first (privacy, matches the earlier notes), or a hosted GitHub App first (faster feedback)? Recommendation: hosted for design partners, with a self-host path kept architecturally possible.
2. **Model provider.** Which hosted model family for fixer vs verifier? This needs a cost/quality bake-off on the eval harness, not a decision in advance.
3. **Shannon/Strix.** Integrate as optional evidence sources, or treat them as competitors we benchmark against? Recommendation: benchmark first, integrate Strix (Apache-2.0) if it adds confirmed findings our harness misses.
4. **Design partners.** Which 2–3 external teams with Node/Python APIs and real multi-tenant data will run the MVP on staging?

---

## Sources (verified 2026-11-12)

- SecureAgentBench — https://arxiv.org/abs/2509.22097
- AutoPenBench — https://arxiv.org/abs/2410.03225 · code: https://github.com/lucagioacchini/auto-pen-bench
- AutoPT — https://arxiv.org/abs/2411.01236
- SecLLMHolmes / "LLMs Cannot Reliably Identify and Reason About Security Vulnerabilities (Yet?)" — https://arxiv.org/abs/2312.12575
- Shannon — https://github.com/KeygraphHQ/shannon
- Strix — https://github.com/usestrix/strix
- OWASP AppSec Agent — https://owasp.org/www-project-appsec-agent/ · docs: https://owasp.org/appsec-agent/docs/agents.html
- LLM vulnerability detection & repair review (Zhou et al.) — https://arxiv.org/abs/2404.02525
- Systematic review of LLM vulnerability detection (227 studies) — https://arxiv.org/abs/2507.22659
- OpenGrep — https://github.com/opengrep/opengrep · Trivy — https://github.com/aquasecurity/trivy · OSV-Scanner — https://github.com/google/osv-scanner · Gitleaks — https://github.com/gitleaks/gitleaks · Checkov — https://github.com/bridgecrewio/checkov · ZAP — https://github.com/zaproxy/zaproxy · DefectDojo — https://github.com/DefectDojo/django-DefectDojo
- OWASP ASVS — https://owasp.org/www-project-application-security-verification-standard/

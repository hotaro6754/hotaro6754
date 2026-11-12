# Qyverix Security Intelligence — Product Research & Architecture Specification

**Version 3 · research checked 2026-11-12** · Execution plan: [EXECUTION_PLAN.md](./EXECUTION_PLAN.md)

> **Positioning:** *Understand the application. Prove the risk. Verify the fix.*
> **Entry wedge:** continuous authorization and tenant-isolation assurance for multi-tenant B2B SaaS.
> **Path:** build it as a Qyverix product → run it on Qyverix's own code → design partners → paying clients → only then YC.

**Version 3 narrows the thesis.** "An AI security engineer that scans, exploits and fixes" is now the pitch of at least six YC-funded startups I could confirm, and GitHub made agentic autofix generally available in October 2026 (§3.3). Qyverix therefore enters through one thing it can do measurably better than a broad tool: know what must never happen in a *specific* application, test those rules on every code change, and attach executed proof to every finding and every fix. Repository-wide intelligence and verified remediation grow from that base. They are the destination, not the opening move.

## Contents

0. [Evidence ledger: what was verified](#0-evidence-ledger-what-was-verified)
1. [Strategic choice: which business to be in](#1-strategic-choice-which-business-to-be-in)
2. [What the research says](#2-what-the-research-says)
3. [Competitor teardown](#3-competitor-teardown)
4. [Research-to-feature traceability matrix](#4-research-to-feature-traceability-matrix)
5. [Differentiating capabilities](#5-differentiating-capabilities)
6. [Build vs integrate](#6-build-vs-integrate)
7. [System architecture](#7-system-architecture)
8. [Investigation state machine](#8-investigation-state-machine)
9. [Evidence schema](#9-evidence-schema)
10. [Threat model for Qyverix itself](#10-threat-model-for-qyverix-itself)
11. [Technology selection](#11-technology-selection)
12. [MVP scope and decisions](#12-mvp-scope-and-decisions)
13. [Roadmap and milestones](#13-roadmap-and-milestones)
14. [Benchmark and validation strategy](#14-benchmark-and-validation-strategy)
15. [Licensing and commercial viability](#15-licensing-and-commercial-viability)
16. [Risks and open questions](#16-risks-and-open-questions)
17. [Research library](#17-research-library)

---

## 0. Evidence ledger: what was verified

Only ✅ numbers should appear in pitch material. Everything else is a hypothesis we test ourselves (§14).

| Claim | Status | Note |
|---|---|---|
| **SecureAgentBench**: 105 repo-level tasks; best correct-and-secure rate 15.2%; agents introduce new vulnerabilities | ✅ | arXiv 2509.22097. Best agent was SWE-agent with DeepSeek-V3.1. The average is under 10%. A later revision (*SecureVibeBench*, C/C++ OSS-Fuzz tasks) reports different numbers. Don't mix them. |
| **AutoPenBench**: 33 tasks; 21% autonomous vs 64% assisted | ✅ | arXiv 2410.03225. Code at `lucagioacchini/auto-pen-bench`. |
| **AutoPT**: state-machine agent, 22% → 41% vs ReAct | ✅ | arXiv 2411.01236. DOI `10.1109/TIFS.2025.3601343` resolves to IEEE Xplore, which fits the TIFS venue. Single benchmark (Vulhub), GPT-4o-mini. |
| **SecLLMHolmes**: 228 scenarios, 8 LLMs, high FPR, flags patched code, wrong reasoning | ✅ | IEEE S&P 2024, arXiv 2312.12575. The models are from 2023–24, so the exact rates are dated. The failure modes still apply. |
| **IEEE Access systematic review** (208 studies; 91.3% detection / 11.1% repair / 5.3% explanation) | ⚠️ Partial | The DOI `10.1109/ACCESS.2025.3631363` resolves to an IEEE Xplore record, but its content couldn't be read from here, so the numbers are unchecked. The detection-heavy, repair-light pattern does agree with Zhou et al. (58 studies) and Kaniewski & Schmidt (227 detection studies). |
| "Synergizing LLM semantic reasoning with assertion-guided analysis" (+29.74%) | ⚠️ Not checked | |
| "From Function to Repository" (IEEE TSE 2026) | ⚠️ Not checked | Its central claim, that function-level benchmarks miss cross-function bugs, is well established elsewhere. |
| Practitioner survey (158 respondents; 88% / 63%) | ⚠️ Vendor survey | Use as directional evidence only. |
| **Shannon**: AGPL-3.0, ~50k stars, Lite/Pro split | ✅ (secondary sources) | Shannon Lite is AGPL-3.0. Shannon Pro is commercial. |
| **Strix**: autonomous exploitation, SARIF output, Docker sandbox | ✅ | **Apache-2.0** (this answers the earlier "verify Strix's license" item). Bring-your-own LLM key. Star counts vary between snapshots, so don't cite one. |
| **OWASP AppSec Agent**: 4 agents, Lab project | ✅ | ~15 stars, 1 contributor. Current role names: `code_reviewer`, `pr_reviewer`, `threat_modeler`, a run-tests-after-fix role, and an `fp_adversary` false-positive filter. |
| **Nephilex**: early alpha, integrated AI security engineer | ✅ **Corrected.** Version 1 of this doc wrongly said the repo couldn't be found. | `Nephilex/nephilex`, Apache-2.0, ~14 stars, "early alpha". **Its own README reports 2.0% recall on held-out real fix commits.** Semgrep also scored 2.0% and Bandit 10.2% (Python only). It reports +89.4 on the OWASP Benchmark (Python), but the README says its rules were developed *with that dataset visible*, so that score is not independent. |
| **Mobb** | ✅ | Commercial hosted product. Its community edition **Bugsy** is MIT-licensed: a CLI that takes Checkmarx/CodeQL/Fortify/Snyk results and proposes fixes. I found no evidence of a self-hostable full platform. |
| **Zizmor**: GitHub Actions security | ✅ | The repo has moved to `zizmorcore/zizmor` (the old `woodruffw/zizmor` link redirects). It covers template injection, credential leakage and excessive permissions in Actions, Dependabot and pre-commit configs. |
| **VulnGym**: 184 advisories, 408 vulnerability entries, 23 repositories; coding agents struggle at repository-level detection and at building evidence traces | ✅ | arXiv 2608.02001. Detection only. Specific recall figures quoted in blogs (e.g. 22.58% best case on hard tasks) were not checked against the paper. |
| **JITVul**: 879 CVEs, 91 vulnerability types, paired vulnerable/fixed commits | ✅ | ACL 2025, arXiv 2503.03586. LLMs label over 90% of samples "vulnerable" in some settings, which inflates F1. Pairwise accuracy is the honest measure. |
| "SecureRepoBench": 318 tasks, 27 repositories, 15 CWEs | ✅ Name corrected | The benchmark is **SecRepoBench** (arXiv 2504.21205). It covers C/C++ secure code *completion*, so it is weak evidence for web-application repair. |
| A.S.E. benchmark; SAST-adoption barriers study; Reddit thread on triage load | ⚠️ Not checked | Directional only. |
| YC-funded overlap: Corgea, ZeroPath, Gecko Security, Winfunc, MindFort, Tolmo | ✅ | All have YC profiles with find / verify / fix claims. Details in §3.3. |
| YC-funded overlap: 0.security, OpenHack, Casco | ⚠️ | 0.security appears only in a LinkedIn post (YC F26). I found nothing on OpenHack or Casco. |
| **GitHub agentic autofix** | ✅ | Generally available since 15 Oct 2026. It validates a fix by **re-running CodeQL**, not by re-running an exploit. Default-branch alerts only. Needs Code Security or Advanced Security plus Copilot. |

**Lesson from Nephilex:** its numbers are the strongest evidence in this document for our core thesis. Benchmark scores built with the test set visible look excellent (+89.4). The same tool on held-out real-world fix commits finds 2%. **Qyverix's evaluation must be held-out and real-world from day one**, or we will fool ourselves the same way.

---

## 1. Strategic choice: which business to be in

| Direction | What you'd build | Assessment |
|---|---|---|
| AI pentesting | A Strix/Shannon competitor | Crowded, well-funded open-source leaders, fast-moving. Hard to differentiate. |
| AI code security | A Snyk/Semgrep competitor | Large incumbents, mature rule ecosystems, distribution advantages. |
| Autonomous security engineering | Discovery + evidence + remediation + verification | **The destination, not the entry point.** At least six YC-funded startups already claim this loop (§3.3), and GitHub ships agentic autofix. |
| **Continuous authorization and tenant-isolation assurance** | A model of what must never happen in one application, tested on every change, with proof-carrying fixes | **Enter here.** Narrow, measurable with deterministic oracles, painful for multi-tenant SaaS, and the base the broader product grows from. |

**Defensible IP**, in priority order:
1. Application-specific security invariants, and the authorization harness that checks them.
2. A repository-to-runtime security graph, updated incrementally per commit.
3. Evidence-based verification (a suspicion is promoted only when executed proof exists).
4. Proof-carrying patches (independent gates, re-exploitation).
5. Repository security memory that compounds into deterministic rules.
6. A continuously growing, held-out benchmark of real-world secure repairs.

**Not IP, so integrate:** CVE databases, generic SAST engines, DAST crawling, secret regexes, IaC policy libraries, LLMs. (Don't train a custom security LLM. It is an expensive distraction at this stage.)

---

## 2. What the research says

| # | Source | Finding | Product implication |
|---|---|---|---|
| R1 | IEEE Access systematic review (⚠️) and corroborating reviews | Research is overwhelmingly about detection. Repair and explanation are thin. JS, Python and Java are underrepresented. | Build detection-to-remediation, and target modern web stacks first. |
| R2 | SecLLMHolmes (✅) | LLMs give false positives, flag patched code, answer inconsistently, and explain wrongly even when right | An LLM claim is never proof. Every finding carries executed evidence. |
| R3 | AutoPT (✅) | A state machine nearly doubles completion over free-form ReAct | A deterministic workflow engine, with LLM decisions bounded inside states. |
| R4 | SecureAgentBench (✅) | ≤15.2% of agent patches are correct *and* secure. Some functional patches add new vulnerabilities. | Security regression gates that are independent of the fixer. |
| R5 | AutoPenBench (✅) | 21% autonomous → 64% with human assistance | Design for *targeted* human checkpoints when evidence is insufficient, not maximum autonomy. |
| R6 | Assertion-guided analysis (⚠️) | Program analysis plus LLM with counterexample feedback beats either alone | Use a static graph and assertions as the LLM's grounding and checker. |
| R7 | Function → Repository (⚠️) | Real vulnerabilities span functions and files | Treat call graph, data flow and route maps as core infrastructure. |
| R8 | Nephilex README (✅) | Visible-set scores do not transfer to held-out real fixes | Held-out, real-world evaluation only. |
| R9 | Vendor practitioner survey (⚠️) | Manual validation burden; FP rate matters more than cost | Make evidence-backed precision a flagship metric. |
| R10 | VulnGym (✅) | Coding agents struggle at end-to-end repository-level detection and at building a trace from entry point to effect | Build traces deterministically from the graph; don't ask the model to invent them. |
| R11 | JITVul (✅) | LLMs over-predict "vulnerable"; paired vulnerable/fixed accuracy is the honest measure | Evaluate on pairs: flag the vulnerable version *and* clear the fixed one. |
| R12 | GitHub agentic autofix (✅) | The market-default fixer verifies by re-running the scanner | Re-exploitation and invariant re-checks are what make a Qyverix fix different. |

**Synthesis:** finding is getting cheaper; *completing the lifecycle reliably* is not. The opportunity is an evidence-driven system that moves between code understanding, exploit validation, remediation and independent verification.

---

## 3. Competitor teardown

### 3.1 Capability matrix

Legend: ● strong · ◐ partial / paid tier · ○ absent or out of scope. These are based on public docs and READMEs, not hands-on audits. Verify each with a teardown run (§14.4).

| | Repo graph | SAST | SCA | Secrets | IaC / CI | DAST | Exploit proof | Business-logic authz | Fix generation | Fix *security* verification | Lifecycle mgmt | Self-host OSS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Strix** (Apache-2.0) | ◐ | ◐ | ○ | ○ | ○ | ● | ● | ◐ | ◐ | ○ | ○ | ● |
| **Shannon Lite** (AGPL) | ◐ | ◐ | ○ | ○ | ○ | ● | ● | ◐ | ○ | ○ | ○ (Pro) | ● |
| **Nephilex** (Apache, alpha) | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ○ | ● | ◐ | ○ | ● |
| **OWASP AppSec Agent** (Apache, Lab) | ○ | ◐ (LLM) | ○ | ○ | ○ | ○ | ○ | ○ | ● | ◐ (tests only) | ○ | ● |
| **Mobb / Bugsy** (MIT CE) | ○ | ○ (consumes) | ○ | ○ | ○ | ○ | ○ | ○ | ● | ◐ | ◐ | ◐ |
| **OpenGrep** (LGPL) | ◐ | ● | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● |
| **Semgrep** (commercial + OSS) | ◐ | ● | ● | ● | ◐ | ○ | ○ | ○ | ◐ | ○ | ● | ◐ |
| **Snyk** | ◐ | ● | ● | ◐ | ● | ◐ | ○ | ○ | ◐ | ○ | ● | ○ |
| **Aikido** | ◐ | ● | ● | ● | ● | ◐ | ○ | ○ | ◐ | ○ | ● | ○ |
| **GitLab Security** | ○ | ● | ● | ● | ● | ● | ○ | ○ | ◐ | ○ | ● | ◐ |
| **ZAP / Trivy / OSV / Gitleaks / Checkov / Zizmor** | ○ | ○ | ●(Trivy/OSV) | ●(Gitleaks) | ●(Checkov/Trivy/Zizmor) | ●(ZAP) | ○ | ○ | ○ | ○ | ○ | ● |
| **DefectDojo** (BSD) | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● | ● |
| **Qyverix (target)** | ● | ● (via OpenGrep) | ● (via OSV/Trivy) | ● (via Gitleaks) | ● (via Checkov/Zizmor) | ● (via ZAP) | ● | ● | ● | **●** | ◐ (export to DefectDojo) | ● |

**Among these open-source tools and incumbents, the empty column is "Fix security verification".** None documents re-exploiting after the patch and diff-scanning for newly introduced weaknesses. The funded startups in §3.3 do claim parts of this, so the column is a place to out-execute, not an uncontested gap.

### 3.2 Where each competitor stops

**Strix.** Agents with browser, terminal and an HTTP proxy. Proof-of-concept reports. SARIF/JSON/CSV/Markdown output. Docker sandbox. *Stops at:* a pentest report. There is no broad SAST/SCA/IaC, no remediation verification loop, and no finding lifecycle. Its public issues show operational fragility: sandbox readiness races, malformed tool arguments, path handling, cost accounting, and dedupe accepting invalid model values. *Lesson:* deterministic orchestration and validated tool schemas matter as much as model quality.

**Shannon (Lite).** Source-informed attack paths, browser exploitation, reproducible PoCs, authenticated testing, resumable workspaces. *Stops at:* code-informed web/API pentesting. Broader agentic SAST, governance and lifecycle are in Pro. Runs take ~1–1.5 h. One model setting is used for the whole run. Its docs warn about mutative exploitation and prompt injection from source code. *Lesson:* per-stage model routing and incremental runs keyed by commit are real cost advantages.

**Nephilex.** The closest in *ambition* (repo scan, attack surface, validation, fixes, multi-provider). *Stops at:* early alpha, 14 stars, and 2% held-out recall by its own report. *Lesson:* an all-LLM pipeline without strong deterministic grounding does not generalize. Watch it, and don't depend on it.

**OWASP AppSec Agent.** A clean four-role separation (reviewer, threat modeler, fixer, QA verifier) and an adversarial false-positive pass. *Stops at:* the QA verifier only runs the test suite. That is the exact gap SecureAgentBench exposes. *Lesson:* borrow the role separation, and add security gates.

**Mobb / Bugsy.** Turns third-party SAST results into fix PRs. *Stops at:* trusting the input finding (no exploit proof) and verifying only that the fix compiles and tests pass. *Lesson:* "fix from SARIF" is already a product. Our fix is differentiated only if it is *proven*.

**Snyk, Semgrep, Aikido, GitLab.** Strong detection, developer workflow and lifecycle management. *Stop at:* rule-based or reachability-based risk. No demonstrated exploitability, and no security-verified autonomous patches. *Lesson:* coexist with them. Accept their SARIF as input signals instead of trying to replace them.

**Emerging (⚠️, verify before relying on these):** search results mention OpenAI security agents (Aardvark in private beta, an open-sourced Codex Security CLI). Frontier labs entering repo-level vulnerability finding and patching is the main strategic risk, and it reinforces that **evidence, verification and business-logic depth** must be the moat, not access to a strong model.

### 3.3 Funded startups with the same pitch

These are product claims from YC profiles and vendor pages, not audited capabilities. A missing mention on a website is not evidence that a feature is missing.

| Company | What it claims | What to test against it |
|---|---|---|
| **Corgea** (YC S23) | AppSec platform that validates vulnerabilities and generates fixes, alongside Snyk/Semgrep. Per the research notes, also code-aware pentesting, exploit reproduction and continuous retesting. | Repeatability of verified patches; depth on application-specific authorization |
| **ZeroPath** (YC S24) | AI-native SAST with detection and automated patching | Multi-service runtime behavior; security regression testing |
| **Gecko Security** (YC F24) | Models how the application should behave, simulates attacks, verifies exploitable flaws, proposes fixes | Whether the application model persists and stays accurate as code changes |
| **Winfunc** (YC S24) | "AI hacker" that finds, verifies and patches vulnerabilities in codebases | Reproducible coverage; independent verification of repairs |
| **MindFort** (YC X25) | Agents that find, validate and patch in web apps and networks; continuous pentesting; a company page claims under 1% false positives | Determinism, cost, code-level fixes |
| **Tolmo** (YC, founded 2026) | Security agents on a live knowledge graph of cloud services, containers and databases; waitlist | Code-level depth; graph accuracy |
| 0.security, OpenHack, Casco | ⚠️ As described in the research notes; not confirmed | — |
| **GitHub agentic autofix** (GA Oct 2026) | Agent investigates a code scanning alert, writes a fix, re-runs CodeQL, opens a draft PR; up to 25 alerts per PR | Verifies with the scanner, not an exploit; default-branch alerts only; no application-specific authorization model |

**What this means for Qyverix:**
- Business-logic testing, knowledge graphs, exploit validation and autonomous patching are all *claimed* by someone. None is a differentiator by name alone.
- Qyverix can't win on breadth against funded teams. It can win on a narrow promise with measured results: one customer type, one bug family, deterministic proof, and published held-out numbers.
- As far as public material shows, these products sell *discovery*: they go looking for vulnerabilities. The wedge here is *assurance*: a declared, versioned set of rules about the application that is re-proven on every change and never silently reported as clean. Treat that distinction as a hypothesis to confirm in the §14.4 teardown and in customer interviews.

---

## 4. Research-to-feature traceability matrix

Every major feature must trace to evidence and to a metric. If a feature has no row here, it doesn't get built in v1.

| Feature | Evidence | Design decision | Success metric (§14) |
|---|---|---|---|
| F1 Evidence states (Suspected → Corroborated → Reproduced → Fixed → Verified) | R2, R8, R9 | Promotion only via executed artifacts. The LLM proposes; the harness decides. | Evidence-backed precision |
| F2 Security graph | R6, R7 | Built from deterministic parsers, not from LLM reading | Recall on cross-file bugs; root-cause accuracy |
| F3 Investigation state machine | R3, Strix issues | Durable workflow; LLM inside bounded states; schema-validated tools | Job completion rate; stuck-job rate |
| F4 Verified remediation gates | R4 | Fixer and verifier separated; re-exploit; diff-scan; suppression detector | Secure repair rate; regression rate |
| F5 Differential authz harness | R1 (web stacks), BOLA prevalence | Multi-identity replay with a deterministic oracle | Reproduced authz findings on crAPI/VAmPI; FP = 0 |
| F6 Human checkpoints | R5 | Escalate when evidence is insufficient instead of guessing | Assisted vs autonomous resolution rate |
| F7 Persistent security memory | R3, Shannon resumability | Structured, versioned facts, not chat logs | Re-scan cost; repeat-FP rate |
| F8 Cost-aware model routing | Shannon single-model runs, cost reports | Route by uncertainty, severity and complexity; per-job budgets | Cost per reproduced finding / per verified fix |
| F9 Held-out benchmark | R8, R11 | No tuning on the evaluation split; paired vulnerable/fixed cases | Results published per release |
| F10 Declared invariants + PR gate | R10, R12, §3.3 | Invariants live in the repo, compile to harness tests, and uncovered routes are reported | Authorization coverage; violations caught before merge |
| F11 Change-impact selection | R7 | A graph diff selects the invariants and past findings affected by each PR | PR check time; missed-regression rate |

---

## 5. Differentiating capabilities

**Priority order in v3.** Capability 04, reframed as declared invariants, is the entry wedge and ships first. 02 (the graph) and 01 (evidence) are what make it work. 03 (verified remediation) ships once the invariant gate is in use, because fix generation is where competition is densest. 05 and 06 support all of them. 07 and 08 are new in this version.

### 01 · Evidence-first vulnerability intelligence *(highest priority)*

The core product object is the **evidence bundle**, not the report. It holds:

- the exact file, symbol, line range and commit;
- the source-to-sink trace, from the static engine;
- attacker-controlled input and preconditions;
- a reproducible test case;
- the observed impact;
- artifact provenance;
- remediation and retest status.

| State | Required evidence | Shown as |
|---|---|---|
| **Suspected** | A single scanner or model signal | An investigation lead. **Never shown as a vulnerability.** |
| **Corroborated** | ≥2 *independent* signals agree (e.g. taint path + reachable route + matching DAST response) | Likely vulnerability |
| **Reproduced** | A reproducer ran and a deterministic impact oracle passed | A vulnerability; can block a merge |
| **Fixed** | A patch exists and passes build and tests | Fix pending verification |
| **Verified** | The original reproducer now fails, the invariants hold, and no new findings appeared | Closed, with proof |

Transitions upward require an executed artifact. An LLM can *request* a promotion. It cannot *perform* one, and it never marks its own patch Verified.

### 02 · Whole-repository security graph *(high priority)*

```
Route ─► Middleware chain (authn? authz? roles?) ─► Handler ─► Service ─► Query/ORM ─► Table (tenant_id?) ─► Sensitive fields
Package ─► CVE (OSV) ─► Reachable call sites        IaC resource ─► Exposure ─► Service it hosts        CI workflow ─► Secrets / permissions
```

Sources: tree-sitter parsing, per-language call graphs, framework route extractors (Express, NestJS and Next.js first; FastAPI/Django next), OpenGrep taint output, Joern-style code property graphs where depth is needed, SBOMs, and Checkov/Trivy/Zizmor output. The LLM **queries** the graph. It doesn't build it from raw source text. This makes "reachable CVE", "route without an ownership check" and "tenant filter missing on this query path" into queries rather than guesses. The graph also records runtime observations (which endpoints exist and how they respond), and it is updated incrementally per commit, not rebuilt for every question.

### 03 · Security-verified autonomous remediation *(high priority, most visible)*

`Find → Reproduce → Root cause → Patch → Test → Rescan → Re-exploit → Verify → PR`

| Gate | Check | Catches |
|---|---|---|
| G1 | Build, type-check, existing tests | Broken functionality |
| G2 | The original reproducer **now fails** to exploit | Fixes that don't fix |
| G3 | The original scanner signal no longer fires | Incomplete fixes |
| G4 | Full SAST/secret/IaC/SCA **diff**: zero *new* findings | "Fixed one, added one" (R4) |
| G5 | Variant search for the same bug class elsewhere | Partial coverage |
| G6 | Suppression and evasion detector | `nosemgrep` comments, deleted or skipped tests, disabled routes, broad `try/except`, weakened assertions, scanner-config edits |

- The verifier runs in a separate process with a different prompt, ideally a different model family, and read-only access.
- With no reproducer, the PR is labeled **unverified-fix**. It is never presented as verified.
- The PR body is generated from the evidence bundle: the finding, the reproducer before and after, the gate results, residual risk and rollback steps.
- **No auto-merge, ever.**

### 04 · Business-logic and authorization testing

Example: user A owns order 123 and user B owns order 456. `GET /orders/{id}` authenticates but doesn't check ownership. A scanner that only checks "auth present?" misses this.

The engine reasons about:
- roles and permissions;
- tenant boundaries;
- resource ownership;
- state transitions;
- payment and refund workflows;
- administrative privilege escalation;
- quantity and price invariants;
- race conditions.

It derives tests from API specs (OpenAPI/GraphQL), the security graph, and **explicitly configured test accounts**.

**Invariants are declared, versioned and reviewed.** The engine proposes them from the graph and the API spec. A human confirms them once. They then live in the repository:

```yaml
# .qyverix/invariants.yml
model:
  tenant_key: organization_id
  roles: [owner, admin, member, billing, anonymous]
  resources:
    invoice: { owner: organization, routes: ["/api/invoices/**"] }
    user:    { owner: self,         routes: ["/api/users/**"] }
invariants:
  - id: tenant-isolation
    rule: "no principal reads or writes a resource owned by another organization"
    applies_to: [invoice, project, document]
  - id: no-self-escalation
    rule: "a member cannot change any role, including their own"
    routes: ["PATCH /api/users/:id/role"]
  - id: paid-feature-gate
    rule: "an organization on plan=free cannot call routes tagged paid"
  - id: refund-finality
    rule: "a refunded payment never transitions to paid"
```

Each invariant compiles to concrete harness tests. A violation is a Reproduced finding. A new route that no invariant covers is reported as **uncovered**, never as safe.

**Differential multi-identity harness:**
1. Provision ≥2 users per role and ≥2 tenants in a disposable staging DB, using approved fixture scripts.
2. Record the legitimate request for each route as its owner.
3. Replay it as another user, the same role in another tenant, a lower role, and unauthenticated. Also skip, reorder and replay workflow steps.
4. **The oracle is deterministic:** status code, response body and DB side effects compared against the expected access matrix. The LLM proposes the matrix and the mutations; the harness decides pass or fail.
5. A failure is a Reproduced finding whose reproducer is already a regression test.

### 05 · Persistent security memory

This is structured, versioned evidence, not vector blobs or chat transcripts. It holds:
- previous attack attempts, both successful and dead-end, so they aren't repeated;
- repository architecture and auth flows, as graph snapshots per commit;
- confirmed security invariants ("all `/admin/*` routes require `role=admin`");
- previous patches and any regressions;
- known false positives and accepted risks, each with an **expiry date** and a reason;
- learned project conventions ("ownership is enforced by `@require_owner`").

Two payoffs:
- **Resumability.** A scan resumes at the last completed state and never redoes finished work.
- **Compounding.** Reproduced findings and conventions are compiled into **custom OpenGrep rules and harness invariants**, proposed in a PR. Each customer's codebase gets cheaper and more precise to scan over time, which a stateless agent cannot do.

### 06 · Cost-aware multi-model orchestration

| Work | Engine |
|---|---|
| Broad coverage | Deterministic scanners (no LLM) |
| Triage, dedupe, classification | Small or local model |
| Complex exploit paths, root cause | Strong reasoning model |
| Patch generation | Coding model |
| Verification | A **different** model family from the fixer, plus symbolic and dynamic checks |
| Objective proof | Executed reproducers, tests, scanners (no LLM) |

- Route by uncertainty, severity and complexity.
- Each job has a hard budget for tokens, wall-clock time and tool calls.
- Record token spend, cache hits, runtime and outcome for every investigation.
- Key incremental scans by commit SHA and changed subgraph.

*The model is replaceable. The evidence and workflow are not.*

### 07 · Security change-impact intelligence

On each PR, the graph diff answers: which invariants depend on the changed code, which routes are affected, and which previously Verified findings could have come back. Only those tests re-run. That keeps the check fast enough to be a required status on every PR, and it catches regressions that a periodic scan would find weeks later.

### 08 · A gate for AI-written changes *(a distribution angle, not a separate product)*

Coding agents raise the rate of change, so the same PR gate matters more. Don't position this as "we scan AI code": GitHub and Snyk are already there. Position it as the same invariant gate regardless of who wrote the diff, and later expose it as a tool a coding agent can call before it proposes a change.

---

## 6. Build vs integrate

| Capability | Decision | With |
|---|---|---|
| SAST patterns and taint | Integrate | OpenGrep (CLI, separate process) |
| Dependency CVEs, SBOM, containers | Integrate | OSV-Scanner, Trivy |
| Secrets | Integrate | Gitleaks |
| IaC / CI config | Integrate | Checkov, Trivy, Zizmor |
| DAST crawling and active scan | Integrate | OWASP ZAP (automation framework) |
| Agentic pentest | **Optional evidence source** | Strix (Apache-2.0). Shannon only as a separately deployed, unmodified tool, or under commercial terms (see §15). |
| Finding lifecycle UI | Integrate / export | SARIF, DefectDojo API |
| Code property graph | Integrate where needed | tree-sitter, plus Joern (Apache-2.0) for deep languages |
| **Security graph (routes → authz → data)** | **Build** | Our framework extractors |
| **Application security model and invariant compiler** | **Build** | Core IP; the entry wedge |
| **Evidence model and promotion rules** | **Build** | Core IP |
| **Investigation state machine** | **Build** on a workflow engine | Temporal or a custom state machine |
| **Differential authz / business-logic harness** | **Build** | Core IP |
| **Remediation gates G1–G6** | **Build** | Core IP |
| **Memory and auto rule generation** | **Build** | Core IP |
| **Model router and cost ledger** | Build thin, on LiteLLM | |
| **Held-out benchmark** | **Build and publish** | Core credibility asset |

**Excluded:**
- *CodeQL.* Its license restricts use on non-open-source code without GitHub Advanced Security, so don't bundle it. Accept a customer's own CodeQL SARIF as an input instead.
- *A custom security LLM.*

---

## 7. System architecture

```
 Ingestion: GitHub/GitLab App · local repo · Docker images · OpenAPI/GraphQL · IaC · CI configs
                                    │
                                    ▼
 ┌──────────────────────────── 01 Repository intelligence ─────────────────────────────┐
 │ tree-sitter AST · call graph · data flow · dependency graph · route & middleware map │
 │ trust boundaries · tenant/ownership columns · sensitive-field tags   ──► Security graph│
 └──────────────────────────────────────────────────────────────────────────────────────┘
                                    │
 ┌──────────────────────────── 02 Analysis engines (signals) ──────────────────────────┐
 │ OpenGrep · OSV/Trivy · Gitleaks · Checkov/Zizmor · ZAP · Strix (opt) · authz harness  │
 └──────────────────────────────────────────────────────────────────────────────────────┘
                                    │ SARIF/JSON → normalizer → fingerprint/dedupe
                                    ▼
 ┌──────────────────────────── 03 Reasoning & orchestration ───────────────────────────┐
 │ Durable state machine (§8) · model router · budgets · memory · attack-path planner    │
 └──────────────────────────────────────────────────────────────────────────────────────┘
                 │                                               │
                 ▼                                               ▼
 ┌──── 04 Evidence & validation ────┐             ┌──── 05 Autonomous remediation ─────┐
 │ static + runtime evidence        │             │ root-cause localization            │
 │ reproducers in staging sandbox   │◄───────────►│ minimal patch in isolated worktree │
 │ deterministic oracles            │  re-exploit │ gates G1–G6 · independent verifier │
 │ correlation · calibrated states  │             └────────────────────────────────────┘
 └──────────────────────────────────┘                             │
                 └──────────────────────┬──────────────────────────┘
                                        ▼
 ┌──────────────────────────── 06 Security assurance ──────────────────────────────────┐
 │ Verified findings · remediation PRs · check runs · audit log · SARIF/DefectDojo export │
 └──────────────────────────────────────────────────────────────────────────────────────┘
```

**Architectural principle:** separate **Analysis** (what could be wrong?), **Verification** (can we demonstrate it?) and **Remediation** (can we correct it safely?). No single LLM is the sole authority for more than one of these.

**Runtime topology (MVP):** a modular monolith (FastAPI) plus a worker pool, a Postgres database, Redis, object storage, and per-job ephemeral sandboxes. **No Kubernetes and no microservice sprawl for the MVP.**

---

## 8. Investigation state machine

Each investigation is one durable workflow. **D** = deterministic step; **L** = LLM decision, bounded and schema-validated; **H** = optional human checkpoint.

```
INGEST(D) → INDEX(D) → SCAN(D) → NORMALIZE(D) → CORRELATE(D+L)
   → TRIAGE(L) ──discard──► CLOSED_FP (memory)
        │
        ▼
   PLAN_REPRO(L) → REPRODUCE(D, sandbox) ──fail×N──► NEEDS_HUMAN(H) / stay SUSPECTED
        │ oracle pass
        ▼
   REPRODUCED → ROOT_CAUSE(L + graph) → PATCH(L, worktree) → GATES G1..G6(D)
        │                                   ▲          │ fail (≤k retries, then H)
        │                                   └──────────┘
        ▼ all pass
   INDEPENDENT_VERIFY(L', different model) → PR_OPEN(D) → HUMAN_MERGE(H) → RETEST(D) → VERIFIED
```

Rules:
- Every state is checkpointed (inputs, outputs, artifacts, cost), so jobs can resume.
- Each L-state has a typed output schema. Invalid output is retried once, then the job escalates. It never "best-guesses".
- Budgets are enforced per state and per job. Running out of budget leads to NEEDS_HUMAN, not silent truncation.
- Transitions are emitted to the audit log.

---

## 9. Evidence schema

```yaml
finding:
  id: QYV-2026-000123
  fingerprint: sha256(cwe + normalized_sink + route_template)     # stable across commits
  cwe: CWE-639
  state: reproduced     # suspected | corroborated | reproduced | fixed | verified | accepted_risk | closed_fp
  location: { repo: org/api, commit: 9f2c1e7, file: src/orders/controller.ts, symbol: getOrder, lines: [41, 58] }
  graph_path: ["GET /orders/:id", "authMiddleware", "OrdersController.getOrder", "OrderRepo.findById", "orders(tenant_id)"]
  preconditions: { auth: "any authenticated user", role: "customer", feature_flags: [] }
  signals:
    - { source: graph,    claim: "no ownership predicate on OrderRepo.findById", tool: qyv-graph@0.4 }
    - { source: opengrep, rule: qyv.authz.missing-owner-check, severity: medium }
  reproducer:
    kind: http_sequence                     # http_sequence | unit_test | script | browser_trace
    artifact: s3://evidence/QYV-2026-000123/repro.har
    oracle: "as user_b: status == 200 && body.order.owner_id == fixtures.user_a.id"
    runs: [{ at: 2026-11-12T09:58Z, env: staging-7f3, result: exploit_succeeded }]
  impact: "Cross-tenant read of any order (address, payment last4)."
  remediation:
    pr: org/api#482
    gates: { G1: pass, G2: pass, G3: pass, G4: pass, G5: "2 variants fixed", G6: pass }
    verifier: { model_family: B, verdict: approve }
    retest: { at: 2026-11-12T10:42Z, result: exploit_blocked }
  provenance:
    - { state: ROOT_CAUSE, model: <routed>, prompt_sha: 3ab1…, tokens_in: 14211, tokens_out: 1890, cost_usd: 0.21 }
  human: { checkpoints: [], merged_by: null }
```

---

## 10. Threat model for Qyverix itself

Qyverix ingests untrusted code, runs it, attacks live apps, and writes to customers' repositories. That makes it a high-value target.

**Assets:**
- customer source code;
- repository write tokens;
- staging credentials and test-account secrets;
- the evidence store, which holds working exploits;
- LLM API keys;
- the audit log;
- the integrity of the PRs it opens.

| Threat | Vector | Mitigation |
|---|---|---|
| **Prompt injection from target repo** | README, comments, fixtures or issue text instruct the agent ("ignore previous… push to main") | Repo content is passed as data, never as instructions. Tool permissions are fixed by policy, not by model output. A deny-list of state transitions an LLM can't trigger. Canary instructions in evals. |
| **Sandbox escape / host compromise** | Malicious build scripts, postinstall hooks, test code | gVisor/Firecracker or rootless containers. **No host Docker socket.** No host mounts. CPU, memory and time limits. Disposable per job. |
| **Token theft / privilege abuse** | Exfiltrating the GitHub token from the sandbox | Short-lived GitHub App installation tokens, scoped to one repo, PR-only permissions. Tokens never enter the code-execution sandbox; PR creation happens in a separate trusted service. |
| **Malicious or backdoored patch** | A compromised model or injected prompt produces a subtly harmful fix | Gate G6. Independent verifier. Diff size limits. Signed commits from the bot identity. **Human merge only.** |
| **Attacking the wrong target** | A misconfigured URL points the exploit stage at production or a third party | Targets need an ownership challenge (DNS/file). Staging allowlist. Egress-blocked staging network. Destructive-action denylist enforced by a proxy (no DROP, mass email or payment calls). |
| **Data exfiltration to LLM provider** | Sending code or secrets to external APIs | Per-tenant model policy (local only / approved API / zero-retention endpoints). Secret redaction before prompts. Data-flow logging. |
| **Evidence store leakage** | Stored working exploits leak | Encryption at rest, per-tenant keys, RBAC, retention limits, access logging. |
| **Supply chain of Qyverix** | Compromised scanner image or dependency | Pinned digests. Qyverix's own SBOM. Scan Qyverix with Qyverix. Signed releases. |
| **Repudiation** | "The bot did that" disputes | An append-only, hash-chained audit log of every tool call, model, prompt hash and output hash. |
| **Denial of wallet** | A huge repo or a looping agent burns tokens | Per-job, per-tenant budgets, loop detection, and cost alerts. |

**Non-negotiables:**
- Never auto-merge.
- Never use production credentials.
- Run active exploitation only against disposable, verified staging targets.
- "Fixed" requires the reproducer to fail, not just the scanner going quiet.

---

## 11. Technology selection

| Layer | Choice | Note |
|---|---|---|
| Backend | Python + FastAPI | Best scanner and analysis ecosystem |
| Orchestration | Temporal, or a custom Postgres-backed state machine | Start custom if the team is small; the interface stays the same |
| Parsing | tree-sitter + language analyzers | Joern for deep CPG queries when needed |
| Code intelligence store | **PostgreSQL first** (graph as adjacency tables + recursive CTEs) | Move to a graph DB only when query profiles demand it |
| Scanners | OpenGrep, Trivy, OSV-Scanner, Gitleaks, Checkov, Zizmor | Run as CLIs in workers |
| DAST | OWASP ZAP automation framework | Authenticated plans per staging target |
| Pentest (optional) | Strix | Shannon only as described in §15 |
| Findings | PostgreSQL + SARIF in/out | DefectDojo export |
| Vector retrieval | pgvector; Qdrant only if scale requires it | Only where semantic retrieval helps |
| Jobs | Redis queue + isolated workers | |
| Sandboxes | gVisor or Firecracker; rootless containers as a minimum | |
| Model gateway | LiteLLM-compatible router | Hosted APIs + Ollama/vLLM |
| Source control | GitHub App first, GitLab second | |
| Frontend | Next.js + TypeScript | **After** the evidence and PR flow work |

**Hardware note.** An RTX 3050 6 GB handles the scanners and a small local triage model. Fixer and verifier models need a hosted API or a separate GPU server.

---

## 12. MVP scope and decisions

The thesis is locked as follows:

| Question | Decision | Why |
|---|---|---|
| First paying customer | **Small and mid-sized B2B SaaS teams** with a multi-tenant application and no dedicated AppSec engineer | Sensitive customer data, frequent change, and an authorization bug can end the business. Value can be shown with a real failing test, not an AI claim. |
| Technical wedge | **Application-specific security invariants and authorization** | Deterministic oracle, so precision can be near-perfect. Least well served by rule-based tools. It is the base for the graph and verified fixes. |
| Deployment | **Hybrid:** cloud control plane, isolated workers in the customer's environment, LLM through a router | Source and staging access stay with the customer. No GPU needed. |
| Objective | **A Qyverix product line first.** YC only after the product is complete and has paying clients (gates in the execution plan). | Your stated direction |
| Autonomy | Find → prove → fix → verify → open a draft PR automatically; a human approves every merge | R5: targeted human checkpoints beat full autonomy |
| Scan scope | Code, dependencies, secrets and APIs, with runtime testing in a disposable environment | Proof needs runtime |

**The wedge:** authorization and tenant-isolation invariants in **TypeScript/JavaScript APIs first (Express, NestJS, Next.js route handlers)**, then Python (FastAPI/Django): declared in the repo, tested on every PR, proven when violated, and fixed with a proof-carrying PR. Injection is the second bug family.

| In MVP | Later |
|---|---|
| Express, NestJS, Next.js route + middleware extraction | FastAPI/Django next; then Java/Spring, Go, .NET, Rails |
| Invariant file, PR gate, change-impact selection | Auto-proposed invariants for payment and workflow state |
| OpenGrep, Gitleaks, OSV, Trivy (fs) as signals | Container images, Checkov, Zizmor, cloud posture |
| Security graph v1 | Cross-service / microservice graph |
| Differential authz harness + injection reproducers | Free-form agentic pentest; Strix integration |
| Gates G1–G4 + independent verifier | G5 variants, G6 full suppression detection |
| Memory v1 (FP expiry, resumability) | Auto rule generation |
| GitHub App: checks, comments, fix PRs; SARIF/DefectDojo export | Web dashboard, GitLab |

---

## 13. Roadmap and milestones

The schedule lives in [EXECUTION_PLAN.md](./EXECUTION_PLAN.md), so there is one timeline, not two. In outline:

| Stage | Outcome | Gate to the next stage |
|---|---|---|
| **1. Build and dogfood** (weeks 1–12) | Invariant gate and proof-carrying fixes for TS/JS, running on Qyverix's own repositories | Held-out numbers meet the §14.2 targets |
| **2. Design partners → paying clients** (months 4–9) | 3–5 external teams using it on every PR; first paid contracts | Paying clients with retained weekly use |
| **3. Scale, then YC** | More languages and bug classes; a YC application backed by usage data | — |

Don't build a polished dashboard before stage 2. The PR check, the draft PR and the evidence bundle *are* the product until the numbers say otherwise.

---

## 14. Benchmark and validation strategy

### 14.1 Datasets

| Set | Evaluates | Held-out? |
|---|---|---|
| OWASP crAPI, VAmPI | API authz / BOLA (MVP core) | Use one for development, one held out |
| OWASP Juice Shop | Broad web vulnerabilities | Dev |
| OWASP Benchmark | Static-layer precision and recall baseline | Reference only. Don't tune on it (see the Nephilex lesson). |
| AutoPenBench | Autonomous pentest vs the published 21% / 64% | Held out |
| SecureAgentBench (on code release) | Secure repair vs the published ≤15.2% | Held out |
| SecLLMHolmes | LLM-layer FP robustness (patched-code, renamed-variable variants) | Held out |
| VulnGym | Repository-level detection and evidence traces vs published agent results | Held out |
| JITVul | Paired vulnerable/fixed discrimination: does it still flag the patched version? | Held out |
| SecRepoBench | Secure completion (C/C++; low relevance to the MVP) | Reference only |
| **Qyverix-TenantBench** (our own): small multi-tenant SaaS apps in TS/JS with seeded authorization bugs and their fixes | Invariant coverage and authorization detection | Half for development, half frozen |
| XBOW-style exploitation challenges (⚠️ check availability and license) | Exploitation depth | Held out |
| **Qyverix-RealFix** (our own): real CVE-fix commits in Node/Python repos; scan the parent commit, compare to the upstream fix | Real-world recall + repair quality | **Frozen, never tuned on** |
| 2–3 internal Qyverix repos | Real FP rate and developer acceptance | Live |

### 14.2 Metrics

**Flagship metrics:** *evidence-backed precision* and *secure repair rate*. Thirty real findings with twenty-five safe fixes beat 500 findings of which 400 are false.

| Metric | Definition | Initial target (revisit after Phase 0) |
|---|---|---|
| Evidence-backed precision | True positives ÷ Reproduced | ≥95% |
| Recall | Known vulnerabilities found (any state) ÷ total | Beat the scanner-only baseline on the held-out set |
| Exploit reproducibility | Reproducers that pass on re-run in a fresh env | ≥95% |
| Root-cause accuracy | Patch location overlaps the upstream fix location | Report |
| Secure repair rate | Patches passing G1–G4 + verifier ÷ Reproduced | ≥60% (MVP classes) |
| Regression rate | Verified patches later failing tests or adding findings | ≤5% |
| Investigation cost | USD per reproduced finding and per verified fix | Report per model route |
| Time to verified fix | Webhook → PR | Report |
| Coverage completeness | Files, routes and packages analyzed vs skipped, with reasons | 100% reported (no silent skips) |
| Authorization coverage | Identity × tenant × route boundaries tested ÷ boundaries in the model | Report; ≥90% on TenantBench |
| Verification accuracy | Verified findings that are really fixed, on an audited sample | ≥98% |
| Human acceptance | Fix PRs merged without substantive edits | Report |

**Hard rule:** a scan that times out or runs out of budget reports *incomplete*, never *clean*.

### 14.3 Ablations (prove the architecture matters)

1. LLM-only vs graph + LLM.
2. Free-form agent vs state machine.
3. Same-model vs cross-family verifier.
4. With vs without memory, on a second scan.
5. Gates G1 only vs G1–G4. This measures how many "test-passing" patches are actually insecure, which is our own replication of R4.

### 14.4 Competitor teardown runs

The standing baselines for every published comparison are Semgrep/OpenGrep, GitHub agentic autofix and one autonomous pentest agent, on the same repositories and cases, not on different demos. Beyond that, run Strix, Shannon Lite (evaluation use only), Nephilex and OWASP AppSec Agent on the *same* held-out set with the *same* model budget, and trial any §3.3 product that offers access. Publish the methodology. This replaces the ● / ◐ / ○ guesses in §3.1 with measured numbers.

---

## 15. Licensing and commercial viability

| Component | License | How Qyverix may use it |
|---|---|---|
| OpenGrep | LGPL-2.1 | Invoke as a separate unmodified CLI. Publish any changes we make to it. |
| Trivy, OSV-Scanner, Checkov, ZAP, Strix, Nephilex, OWASP AppSec Agent, Joern | Apache-2.0 | Permissive. Keep NOTICE files. Check transitive dependencies. |
| Gitleaks, Zizmor, Bugsy | MIT | Permissive. |
| DefectDojo | BSD-3-Clause | Permissive. |
| **Shannon Lite** | **AGPL-3.0** | Embedding or modifying it in a hosted Qyverix service can trigger AGPL source-disclosure obligations. Options: (a) evaluation and benchmarking only; (b) customer-deployed, unmodified, behind a documented interface; (c) commercial terms with Keygraph. **Legal review before any product use.** |
| CodeQL | GitHub terms | Don't bundle it. Accept customer SARIF only. |
| LLM providers | Provider ToS | Check data retention, training opt-out, and acceptable-use clauses for offensive security. |

**Commercial model hypothesis:**
- open-core: an OSS self-hosted scanner, evidence engine and benchmark;
- paid tiers for verified remediation, the business-logic harness, memory and rule generation, multi-repo governance, and SSO/audit.

Maintain Qyverix's own SBOM and license inventory in CI from day one.

---

## 16. Risks and open questions

| Risk | Likelihood | Mitigation |
|---|---|---|
| Funded startups and GitHub already ship find-and-fix agents (§3.3) | **Already happened** | Don't compete on breadth. Own one customer type and one bug family, with deterministic proof and published held-out numbers. Stay model-agnostic. |
| The wedge is not an urgent, budgeted problem for SaaS teams | Unknown | 15–20 customer interviews in weeks 1–4 with a kill criterion (execution plan §4) |
| Reproducers are flaky across environments | Medium | Deterministic fixtures, environment snapshots, re-run requirement before Reproduced |
| Staging environments are hard for customers to provide | High | Ship a docker-compose "staging from repo" bootstrapper. Fall back to Corroborated state with a clear UI. |
| LLM cost per investigation is too high | Medium | Scanner-first funnel, routing, caching by commit, per-job budgets |
| Over-claiming from benchmarks | Medium | Held-out sets only. Publish methodology. (Nephilex lesson.) |
| AGPL contamination | Low if policy is followed | §15 policy, license scanning in CI |

**Open questions for the team:**
1. Who are the 2–3 design partners with Node/Python multi-tenant APIs and a staging environment?
2. Does Qyverix have its own multi-tenant TS/JS application to dogfood on? If not, whose application is the first real target?
3. Which model families for the fixer vs the verifier? Decide by bake-off in Phase 3, not in advance.
4. Is Strix integrated as an evidence source, or only benchmarked against? Decide after the §14.4 teardown.

---

## 17. Research library

**Papers**
- SecLLMHolmes — Ullah et al., IEEE S&P 2024 — https://arxiv.org/abs/2312.12575 · DOI 10.1109/SP54263.2024.00210
- AutoPT — https://arxiv.org/abs/2411.01236 · DOI 10.1109/TIFS.2025.3601343
- SecureAgentBench — https://arxiv.org/abs/2509.22097
- AutoPenBench — https://arxiv.org/abs/2410.03225 · ACL Anthology: https://aclanthology.org/2025.emnlp-industry.114/ · code: https://github.com/lucagioacchini/auto-pen-bench
- VulnGym — https://arxiv.org/abs/2608.02001
- JITVul — Yildiz et al., ACL 2025 — https://arxiv.org/abs/2503.03586
- SecRepoBench — https://arxiv.org/abs/2504.21205
- IEEE Access systematic review (⚠️ numbers unchecked) — DOI 10.1109/ACCESS.2025.3631363
- Assertion-guided analysis + LLM (⚠️) — https://ieeexplore.ieee.org/abstract/document/11576675
- From Function to Repository (⚠️) — DOI 10.1109/TSE.2026.3662145
- Zhou et al., LLMs for vulnerability detection & repair — https://arxiv.org/abs/2404.02525
- Kaniewski & Schmidt, SLR on LLM vulnerability detection — https://arxiv.org/abs/2507.22659

**Projects**
- Strix — https://github.com/usestrix/strix
- Shannon — https://github.com/KeygraphHQ/shannon
- Nephilex — https://github.com/Nephilex/nephilex
- OWASP AppSec Agent — https://owasp.org/www-project-appsec-agent/
- Mobb Bugsy — https://github.com/mobb-dev/bugsy
- OpenGrep — https://github.com/opengrep/opengrep
- Trivy — https://github.com/aquasecurity/trivy
- OSV-Scanner — https://github.com/google/osv-scanner
- Gitleaks — https://github.com/gitleaks/gitleaks
- Checkov — https://github.com/bridgecrewio/checkov
- Zizmor — https://github.com/zizmorcore/zizmor
- ZAP — https://github.com/zaproxy/zaproxy
- DefectDojo — https://github.com/DefectDojo/django-DefectDojo
- Joern — https://github.com/joernio/joern

**Funded competitors**
- Corgea — https://ycombinator.com/companies/corgea
- Gecko Security — https://ycombinator.com/companies/gecko-security
- Winfunc — https://ycombinator.com/companies/winfunc
- MindFort — https://www.ycombinator.com/companies/mindfort
- Tolmo — https://www.ycombinator.com/companies/tolmo
- ZeroPath — https://zeropath.com
- GitHub agentic autofix (GA) — https://github.blog/changelog/2026-10-15-agentic-autofix-for-code-scanning-alerts-general-availability

**Curated lists and standards**
- Awesome-LLM4SVD — https://github.com/hs-esslingen-it-security/Awesome-LLM4SVD
- Awesome AI Pentest — https://github.com/insidetrust/awesome-ai-pentest
- OWASP ASVS — https://owasp.org/www-project-application-security-verification-standard/
- OWASP API Security Top 10 — https://owasp.org/API-Security/

> **Research limitation:** this is a curated synthesis of papers, abstracts, official docs and public repositories. Published experiments were not reproduced, and competitor capabilities in §3.1 come from documentation, not hands-on audits. Treat the gaps as hypotheses until the §14.4 teardown runs confirm them.

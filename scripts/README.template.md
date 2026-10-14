{{pic:hero}}

{{buttons}}

{{pic:impact}}

{{h:about}}

I'm a software engineer with 3+ years of experience building backend systems and production ML, mostly in Python and Java. At **Ally Financial** I own two of the microservices behind a real-time fraud detection platform (Python, gRPC, Kafka, Redis). Before that, I shipped Java/Spring Boot features to a core banking platform at **TCS** and led its zero-downtime Oracle → PostgreSQL migration. I have an MS in Computer Science from **UMass Boston** (2025).

I lean backend, and I like proof: every project below comes with the numbers that show it works, and with what those numbers don't show.
<!-- Add work-authorization status here, e.g. "F-1 STEM OPT, no sponsorship needed until 20XX". -->

{{h:experience}}

<details open>
<summary><b>Software Developer · Ally Financial</b> · 07/2025 – present · Remote<br><sub>Real-time fraud scoring: fraud losses −18% in the first quarter after launch</sub></summary>
<br>

- Helped build Ally's fraud detection platform from the ground up. I own **FraudRiskService** and **TransactionPolicyService**, which score transactions in real time (Python, gRPC, Kafka, Redis).
- Built the `/transaction-risk-evaluation` and `/fraud-alert-monitoring` APIs on PostgreSQL/Aurora. Reworking query plans and adding connection pooling brought average response time from **340 ms to 265 ms**.
- Built a React/TypeScript fraud analytics dashboard that streams live KPIs from Kafka. It replaced hand-maintained Excel reports and cut average investigation time by **~21%**.
- Integrated Claude 3 into risk scoring to write anomaly narratives. Prompt guardrails and validation layers keep the output within FFIEC audit requirements.
- Built the CI/CD pipeline (GitHub Actions, Docker, EKS) and added structured logging and Prometheus/Grafana metrics, so on-call engineers find issues in minutes instead of hours.
- Own OAuth 2.0/JWT auth on every endpoint for SOC 2 and PCI DSS. Wrote **85+ tests** that run on every PR, with **>90% coverage** on critical paths.

</details>

<details>
<summary><b>Graduate Teaching Assistant · University of Massachusetts Boston</b> · 09/2024 – 05/2025 · Boston, MA<br><sub>8 lab cohorts, 90+ students, feedback within 24 hours</sub></summary>
<br>

- Led 8 lab cohorts (**90+ students**) through circuit analysis and MATLAB/Multisim simulations.
- Gave actionable feedback on **70+ lab reports within 24 hours**, which improved problem-solving for **85%** of student pairs.

</details>

<details>
<summary><b>Software Engineer · Tata Consultancy Services</b> · 08/2022 – 08/2023 · Gurgaon<br><sub>Core banking: zero-downtime Oracle → PostgreSQL migration, $45K/yr saved</sub></summary>
<br>

- Shipped 7 Java/Spring Boot features to a core banking platform that processes **50K+ transactions a day**. Wrote 120+ JUnit tests and owned the Jenkins pipeline, which cut the defect rate by **40%** versus the previous release cycle.
- Led a **zero-downtime migration of a 20 GB production database** from Oracle to PostgreSQL. Refactored 15K lines of SQL and application code and re-indexed critical queries, which saved **$45K/year** in licensing and cut **4 s** from page loads.
- Managed a 6-person Tier-2 support team. A structured triage process raised SLA compliance (tickets resolved within 24 h) from **~65% to 90%**.
- Automated nightly reporting with Bash and cron, removing ~5 hours a week of manual work and alerting on production anomalies.

</details>

<details>
<summary><b>Software Development Engineer Intern · NTT Data</b> · 01/2021 – 07/2022 · Remote<br><sub>Enterprise apps: Spring Security hardening, weekly releases</sub></summary>
<br>

- Built Angular/TypeScript components and Spring Boot APIs, plus a Kafka order-processing microservice handling 2K+ transactions a day.
- Added authentication and role-based access (Spring Security, OAuth2, JWT) and fixed input-validation gaps from a security audit. There were zero auth-related incidents after launch.
- Added JUnit/Mockito stages and SonarQube quality gates to GitHub Actions, which helped the team move from biweekly to weekly releases with fewer rollbacks.

</details>

{{h:work}}

### [pytest-triage](https://github.com/shashank11yadav/pytest-triage)
A triage assistant for pytest's GitHub issues that runs in shadow mode: it suggests labels, missing information and likely duplicates, never writes to GitHub, and is scored against what the maintainers actually did. [Live results, updated daily](https://shashank11yadav.github.io/pytest-triage/)

**Problem:** since January 2025, 247 of pytest's 484 new issues (51%) never got a label. Triage is the first thing to slip when volunteers are busy.  
**Approach:** a fixed pipeline of three cheap LLM calls plus local search, with enum-only outputs, injection guardrails and a policy check, and every choice made on a 2024 dev split before the test set is scored.

- Labels: **macro-F1 0.56** vs 0.46 for the best free method, a logistic-regression classifier (**+0.095**, 95% CI +0.04 to +0.14).
- High-precision mode: **82% precise on the 17% of issues** where a second model agrees.
- Duplicates: **7 of 15 known pairs flagged, 3 of 30 false alarms** (search alone finds 5).
- Prompt injection: **0 of 104 attack runs reached a maintainer** (19 attacks in 6 variants each).
- About **$0.0015 and 3.3 s per issue**; $2.13 spent on building and evaluating everything. A CI regression gate fails any prompt or model change that hasn't been re-measured.

`Python · Gemini · BM25 + embeddings · bootstrap evals · GitHub Actions · Docker`

<details>
<summary><b>Inside pytest-triage</b> · how one issue flows through it</summary>
<br>

<p align="center">{{pic:triage}}</p>

</details>

<details>
<summary><b>How these numbers are measured</b> · what they show and what they don't</summary>
<br>

- **Split by time:** examples come from issues before 2024, every choice (prompt, model, thresholds) is made on 256 issues from 2024, and the 237 test issues from 2025 onward are scored once per final choice. Few-shot examples and duplicate candidates are always older than the issue being triaged.
- **Is the gap real?** Paired bootstrap, 2,000 resamples. With 11 to 44 examples per label, gaps under about 0.03 are noise: the prompt revisions after v1 each moved the score by less than that, so I don't count them as wins.
- **The fair baseline:** a logistic regression on embeddings I already had, not just kNN or keywords. The LLM wins on intent labels (docs 0.85 vs 0.58) and ties on feature names (fixtures, parametrize).
- **Precision:** measured 0.43 against maintainer labels, but maintainers apply about 1 label per issue and the model suggests 1.6. A blind audit of 50 "false positives" by two LLM raters (kappa 0.41, no human) puts real precision at about 0.65 to 0.75: an indication, not a measurement.
- **Duplicates and injection fixes** were designed on the same data they're scored on, so those numbers are optimistic. The "before the fixes" injection run (1 of 104 reached a maintainer) is the fairer estimate, and I wrote the attacks myself.
- **Not yet used by maintainers:** the daily shadow run scores issues that didn't exist when the code was written. That's the first step towards measuring whether it actually helps.

</details>

### [Ask the Filings](https://github.com/shashank11yadav/ask-the-filings)
Ask a question about a company's annual report (SEC 10-K) and get an answer with the exact passages it came from. If the filings don't contain the answer, it says so instead of guessing.

**Problem:** an answer about a filing is only useful if you can check it, and if it admits when the filing doesn't say.  
**Approach:** hybrid search (pgvector + Postgres full-text, merged with RRF), a local cross-encoder reranker, and Gemini answering in JSON with citations. Every change was kept or dropped based on an eval.

- Hybrid + reranker: **recall@8 0.92 and 57 of 60 answers correct** (dense alone: 0.78 and 0.82), for **$0.007 and 4.8 s per question**. It never gave a confident wrong answer on this set; the 3 misses were honest "not in the excerpts".
- The reranker had to earn its place: `bge-reranker-base` lifted recall@8 from 0.88 to 0.92, while a MiniLM reranker trained on web snippets added nothing.
- A table-aware chunker looked like an 8-point win on the first 60 questions. On 121 newer ones it fixed 9 and broke 7 (McNemar p = 0.80), so I didn't adopt it.

`Python · Postgres/pgvector · bge embeddings + reranker · Gemini · FastAPI · Streamlit · Docker`

<details>
<summary><b>Inside Ask the Filings</b> · ingestion and the query path</summary>
<br>

<p align="center">{{pic:filings}}</p>

</details>

<details>
<summary><b>How these numbers are measured</b> · what they show and what they don't</summary>
<br>

- **The set:** 60 questions over 10 companies' 10-Ks (2 years each), answered by Gemini 3.8 Flash. Retrieval-only metrics need no API calls.
- **Same-family judge:** Gemini drafted the questions and Gemini grades the answers, and I haven't hand-checked all of them yet. That tends to be generous.
- **Small set:** at 60 questions, a score like 0.95 is uncertain by several points either way. `evals/compare.py` runs a paired McNemar test and a bootstrap interval before I call any change a win.
- **Not measured yet:** none of the 60 questions is unanswerable, so how often it wrongly refuses is still unknown.

</details>

### [SyncScribe](https://github.com/shashank11yadav/collaborative-editor)
A Google-Docs-style real-time editor with presence, inline comments and sharing. [Live demo](https://collaborative-editor-ten.vercel.app)

**Problem:** people editing one document together need each other's changes and cursors instantly, with per-document permissions.  
**Approach:** one Liveblocks room per document, Clerk identities mapped to `room:write` or `room:read` access, and Lexical as the editor.


`Next.js · TypeScript · Liveblocks · Lexical`

<details>
<summary><b>Inside SyncScribe</b> · auth, rooms and real-time sync</summary>
<br>

<p align="center">{{pic:syncscribe}}</p>

</details>

<!--
When you enable this section, renumber the headers after it in scripts/render_svgs.py (SECTIONS).

{{h:opensource}}

**<Project>** · <N> merged pull requests
<One sentence: what the change does and why it mattered.> ([#1234](https://github.com/<org>/<repo>/pull/1234))

**<Project>** · <N> merged pull requests
<One sentence.> ([#5678](https://github.com/<org>/<repo>/pull/5678), [#5690](https://github.com/<org>/<repo>/pull/5690))
-->

{{h:interview}}

**More retrieval candidates made duplicate detection worse.** In pytest-triage, merging the LLM's expansion queries into one ranked pool pushed easy duplicates out of the top 100. Keeping the issue's own top 8 and adding the expansion results as a separate pool raised recall from 6/15 to 10/15.

**My precision number was wrong because the ground truth was incomplete.** Maintainers apply about 1 label per issue and the model suggests 1.6, so measured precision was 0.43. A blind audit of 50 "false positives" put real precision at about 0.65–0.75.

**An 8-point win that was noise.** In Ask the Filings, a table-aware chunker beat the plain one by 8 points on the first 60 questions. Re-tested on 121 newer questions sampled from the filing text, it fixed 9 answers and broke 7 (McNemar p = 0.80). I kept the simpler chunker and added a paired test to every comparison.

**340 ms → 265 ms came from the database layer.** At Ally, reworking the query plans behind the fraud APIs and adding connection pooling cut average response time by about a fifth. <!-- Add what you found: which query, what the plan was doing, how you measured it. -->

{{h:toolbox}}

| Area | Tools | Where I've used them |
| :--- | :--- | :--- |
| **Languages** | Python, Java, TypeScript, C++, SQL, Bash | Python and Java in production at Ally, TCS and NTT Data |
| **Backend & APIs** | Spring Boot, FastAPI, gRPC, REST, WebSockets, OAuth 2.0/JWT | Ally fraud APIs and services, TCS core banking |
| **Streaming & data** | Kafka, Redis, PostgreSQL (incl. pgvector), Aurora, Oracle, MongoDB | Ally real-time scoring, TCS Oracle → Postgres migration, Ask the Filings |
| **Cloud & delivery** | AWS (EKS, Lambda, SQS/SNS, S3), Docker, Kubernetes, GitHub Actions, Jenkins | Ally CI/CD to EKS, TCS Jenkins pipeline |
| **ML & LLM systems** | PyTorch, Hugging Face Transformers, RAG, hybrid retrieval, rerankers, LLM guardrails | pytest-triage, Ask the Filings, AccuScan, Ally narrative generation |
| **Quality & reliability** | PyTest, JUnit/Mockito, SonarQube, Prometheus/Grafana, bootstrap evals | 85+ tests at Ally, 120+ JUnit tests at TCS, eval-backed project results |

{{h:activity}}

Public activity only: work I do for employers lives in their repositories, so it doesn't show up here. Redrawn every 6 hours from GitHub's contribution calendar.

{{pic:activity}}

---

**Working on real-time systems or production ML? I'd like to hear about it.**<br>
I'm looking for backend, ML/AI engineering and platform roles.

**US · Open to remote**<br>
[Email](mailto:yadav.shashank1201@gmail.com) · [LinkedIn](https://www.linkedin.com/in/shashank-yadav-cs/) · [Portfolio](https://shashank11yadav.github.io/shashank-yadav-portfolio/) · [X](https://x.com/Shashankyadav30)

<details>
<summary>Plain-text version of the images</summary>

**Activity:** a year of public GitHub contributions, one cell per day, with totals, active days, streaks and the busiest day; redrawn every 6 hours.

**Shashank Yadav**: open to software engineer, backend and ML/AI roles. Software engineer building real-time services, the data paths behind them, and the evals that show the ML inside them works. MS Computer Science, UMass Boston (2025) · based in the United States, open to remote · Software Developer at Ally Financial. Stream (Kafka, Redis) → serve (gRPC, Spring, FastAPI) → retrieve (pgvector, BM25, RRF) → evaluate (bootstrap CIs, audits).

**Results:** fraud losses −18% in the first quarter (Ally Financial) · average fraud-API response 340 → 265 ms (Ally) · +0.095 macro-F1 for LLM triage over the best free method, 95% CI +0.04 to +0.14 (pytest-triage).

</details>

{{views}}

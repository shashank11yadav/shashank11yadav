# Hi, I'm Shashank

**Software Engineer | MS CS @ UMass Boston (’25) | Python, Java/Spring, Kafka, AWS**

I lean backend: real-time services, the data paths behind them, and checking whether the ML inside them actually works. At **Ally Financial** I own two of the microservices that score transactions for fraud. In its first quarter, the platform cut fraud losses by **18%**.

### Open to
`Software Engineer` · `Backend` · `ML / AI Engineer`. Full-time, US or remote.
<!-- Add work-authorization status here, e.g. "F-1 STEM OPT, no sponsorship needed until 20XX". -->

[Email](mailto:yadav.shashank1201@gmail.com) · [LinkedIn](https://www.linkedin.com/in/shashank-yadav-cs/) · [Portfolio](https://shashank11yadav.github.io/shashank-yadav-portfolio/) · [Resume](https://drive.google.com/file/d/1snhoAl2qE-RtV797FtQCy2SIOwR_2YRu/view) · [LeetCode](https://leetcode.com/u/Shashank-yadav/)

## 01 / Experience

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

## 02 / Featured work

### [pytest-triage](https://github.com/shashank11yadav/pytest-triage)
A shadow-mode triage assistant for pytest's GitHub issues, scored against what the maintainers actually did.
- Label suggestions: **macro-F1 0.52 vs 0.41** for a free kNN baseline (+0.12, 95% CI +0.06 to +0.17, paired bootstrap).
- Duplicate finder: **10/15 known originals recovered, 3/30 false alarms**, after fixing a retrieval-pool bug.
- Tested against **19 prompt-injection attacks**. 2 got through, and both are now routed to a human.

`Python · Gemini · hybrid search · bootstrap evals · Docker`

### [Ask the Filings](https://github.com/shashank11yadav/ask-the-filings)
Question answering over SEC 10-K filings with cited answers. It says so when the filings don't contain the answer.
- Postgres with pgvector and full-text search, merged with Reciprocal Rank Fusion. Answers come back as structured JSON with citation ids.
- Dense, sparse and hybrid retrieval compared on recall@8, faithfulness, abstention accuracy, p95 latency and $/query.

`Python · Postgres/pgvector · Gemini · FastAPI · Docker`

### [SyncScribe](https://github.com/shashank11yadav/collaborative-editor)
A Google-Docs-style real-time editor with presence, inline comments and sharing. [Live demo](https://collaborative-editor-ten.vercel.app)

`Next.js · TypeScript · Liveblocks · Lexical`

<!--
When you enable this section, renumber the sections after it (03 → 04, 04 → 05).

## 03 / Open-source contributions

**<Project>** · <N> merged pull requests
<One sentence: what the change does and why it mattered.> ([#1234](https://github.com/<org>/<repo>/pull/1234))

**<Project>** · <N> merged pull requests
<One sentence.> ([#5678](https://github.com/<org>/<repo>/pull/5678), [#5690](https://github.com/<org>/<repo>/pull/5690))
-->

## 03 / Three things I'd bring up in an interview

**More retrieval candidates made duplicate detection worse.** In pytest-triage, merging the LLM's expansion queries into one ranked pool pushed easy duplicates out of the top 100. Keeping the issue's own top 8 and adding the expansion results as a separate pool raised recall from 6/15 to 10/15.

**My precision number was wrong because the ground truth was incomplete.** Maintainers apply about 1 label per issue and the model suggests 1.7, so measured precision was 0.43. A blind audit of 50 "false positives" put real precision at about 0.65–0.75.

**340 ms → 265 ms came from the database layer.** At Ally, reworking the query plans behind the fraud APIs and adding connection pooling cut average response time by about a fifth. <!-- Add what you found: which query, what the plan was doing, how you measured it. -->

## 04 / Toolbox

| Area | Tools | Where I've used them |
| :--- | :--- | :--- |
| **Languages** | Python, Java, TypeScript, C++, SQL, Bash | Python and Java in production at Ally, TCS and NTT Data |
| **Backend & APIs** | Spring Boot, FastAPI, gRPC, REST, WebSockets, OAuth 2.0/JWT | Ally fraud APIs and services, TCS core banking |
| **Streaming & data** | Kafka, Redis, PostgreSQL (incl. pgvector), Aurora, Oracle, MongoDB | Ally real-time scoring, TCS Oracle → Postgres migration, Ask the Filings |
| **Cloud & delivery** | AWS (EKS, Lambda, SQS/SNS, S3), Docker, Kubernetes, GitHub Actions, Jenkins | Ally CI/CD to EKS, TCS Jenkins pipeline |
| **ML & LLM systems** | PyTorch, Hugging Face Transformers, RAG, hybrid retrieval, LLM guardrails | pytest-triage, Ask the Filings, AccuScan, Ally narrative generation |
| **Quality & reliability** | PyTest, JUnit/Mockito, SonarQube, Prometheus/Grafana, bootstrap evals | 85+ tests at Ally, 120+ JUnit tests at TCS, eval-backed project results |

---

**Working on real-time systems or production ML? I'd like to hear about it.**
I'm looking for backend, ML/AI engineering and platform roles.

**US · Open to remote**
[Email](mailto:yadav.shashank1201@gmail.com) · [LinkedIn](https://www.linkedin.com/in/shashank-yadav-cs/) · [Portfolio](https://shashank11yadav.github.io/shashank-yadav-portfolio/)

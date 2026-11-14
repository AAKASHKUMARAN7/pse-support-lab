# Screenshots

Taken on 14 Nov 2026 from the running lab, after the reproduction run (04:22–05:06 UTC).

**Time zones:** the Grafana screenshots show **IST (UTC+5:30)**, my browser's time zone, so 10:14 IST = 04:44 UTC. The portal shows **GST (UTC+4)**, so 08:35 GST = 04:35 UTC. The text evidence files use UTC.

## Grafana — dashboard "Invoicely Lite – Overview"

| File | Incident | What it shows |
|---|---|---|
| [g1-overview-row.png](g1-overview-row.png) | #2, #1 | Top row: **"API process restarts (1h)" = 11**, while Docker recorded only **2** real restarts (`RestartCount=2`). The restart metric over-counts (see Incident 2, dead end 3). **"5xx responses" = 0**, although the portal returned 502s: the API can't count errors while it's dead. The API row shows `/v1/imports` latency p95 reaching minutes (Oasis). |
| [g2-container-memory.png](g2-container-memory.png) | #2 | "Containers" row. **Container memory (working set)**: the api line (yellow) climbs and drops twice (~10:14 and ~10:21 IST = the two OOM kills). Container restarts: only api restarts. API Go heap in use: the same sawtooth. |
| [g3-api-heap.png](g3-api-heap.png) | #2 | **API Go heap in use** close-up: heap grows with every upload to ~120 MiB and only "drops" when the process is killed. Retention, not a spike. |
| [g4-container-restarts.png](g4-container-restarts.png) | #2 | **Container restarts**: only the api container restarts (1, then 2 in the 10-minute window). |
| [g5-asp-responses.png](g5-asp-responses.png) | #4, #3 | **ASP responses by HTTP status**: **HTTP 429** (blue, Sahara throttled) and **HTTP 422** (yellow, Al Noor BR-CO-15) at ~10:09 IST. My *first* Sahara upload (~10:00 IST) also got 26 × 429 but shows no blue bar: most likely the 429 counter series was created at that moment and `increase()` ignores a series' first sample. The first burst of throttling is invisible on the dashboard. |
| [g6-import-processing-time.png](g6-import-processing-time.png) | #1 | **Import processing time p50/p95**: Oasis-period p95 far above the 60 s portal timeout. Two caveats: (1) the histogram buckets jump from 120 s to 300 s, so the ~4.6 min shown is Grafana's estimate inside that bucket; the exact times (138–157 s) are in the logs ([07-oasis-timing.txt](../07-oasis-timing.txt)). (2) The ~9.5 min spike at 10:30 IST is when my laptop ran out of memory and Docker froze. That's environment, not product. |
| [g7-alert-rules-firing.png](g7-alert-rules-firing.png) | #2 | Alerting → Alert rules, filter Firing (taken 06:46 UTC): **"Invoicely API restarted" is firing although the API has not restarted since 04:50 UTC** (Docker `RestartCount=2`). That's the false positive caused by `process_start_time_seconds` drifting. "Invoicely API 5xx responses" is also firing, but only because Docker's `/healthz` probe got a 503 while my laptop was short of RAM (no 5xx on customer routes). The 5xx alert mixes health-probe failures with customer traffic. Details: [../12-grafana-alert-state.txt](../12-grafana-alert-state.txt). |



## Portal

| File | Incident | What it shows |
|---|---|---|
| [p1-oasis-batches.png](p1-oasis-batches.png) | #1 | Oasis upload #1: **processing time 156.8 s**, Accepted 3 / Rejected 5. OBS-2611-001..003 Accepted with ASP references; 004/005 Rejected by portal (AE-BR-09, against copies still being processed by uploads #2/#3). |
| [p2-sahara-batch.png](p2-sahara-batch.png) | #4 | Sahara batch: **Submitted 26 / Accepted 14**. The HTTP 201 came back after 19.4 s, but 26 invoices never got past "Submitted". |
| [p3-alnoor-invoice-0042.png](p3-alnoor-invoice-0042.png) | #3 | ANF-2611-0042: total without VAT 14,307.08 + VAT 715.35, but **total with VAT 15,022.42**. Rejected by ASP, **BR-CO-15 "Got 15022.42, expected 15022.43"**, with the raw ASP response. |
| [p4-ghaf-batch.png](p4-ghaf-batch.png) | #5, #2 | Ghaf batch: 4 × Rejected by portal, issue dates shown exactly as typed (`13/11/2026`). Also visible: **"Source preview is no longer available for this upload"**. The in-memory copy of the file (SourceCache, the root cause of Incident 2) was lost when the API restarted. |

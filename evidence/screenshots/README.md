# Screenshots

Grafana: http://localhost:3001 → dashboard **Invoicely Lite – Overview**. Set the time range (top right) to **2026-11-14 04:20:00 → 05:06:00 UTC**, the window of the lab run, and the timezone to UTC.

| File | What to capture | What it shows |
|---|---|---|
| `g1-overview-row.png` | Top row: API up, API process restarts (1h), 5xx responses (15m), Submission queue | API down/up flaps; restart stat (over-counts; see Incident 2); 5xx stays ~0 because the API can't count errors while it's dead |
| `g2-container-memory.png` | Panel "Container memory (working set)" | api line climbs to the 128 MiB limit, drops at ~04:44 and ~04:51 (sawtooth) |
| `g3-api-heap.png` | Panel "API Go heap in use" | Heap rises with every upload and never comes back down between restarts |
| `g4-container-restarts.png` | Panel "Container restarts" | Only the api container restarts |
| `g5-asp-responses.png` | Panels "ASP responses by HTTP status" + "Submissions by outcome" | 429 bars (Sahara) with no matching outcome line; 422s (Al Noor) |
| `g6-import-time-lookups.png` | Panels "Import processing time p50/p95" + "Participant lookups" | Oasis imports at ~140–160 s; constant ~0.2 s lookups |
| `g7-alert-rules.png` | Grafana → Alerting → Alert rules (folder Invoicely) | "Invoicely API restarted" firing |
| `p1-oasis-batches.png` | Portal → Batches, the Oasis imports | 3 completed imports with Accepted/Rejected mix |
| `p2-sahara-batch.png` | Portal → the Sahara batch page | Invoices "Submitted" with empty ASP reference |
| `p3-alnoor-invoice.png` | Portal → invoice ANF-2611-0042 | "Rejected by ASP: BR-CO-15 … Got 15022.42, expected 15022.43" |
| `p4-ghaf-batch.png` | Portal → the first Ghaf batch | 4 × Rejected, AE-BR-04 |

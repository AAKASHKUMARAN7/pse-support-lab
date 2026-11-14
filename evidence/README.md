# Evidence index

All files were produced on my laptop against the running lab (`docker compose up`), on **14 Nov 2026**. Times inside the files are **real UTC**; the narrative in `SUBMISSION.md` uses the exercise clock (Mon 16 Nov, Asia/Dubai).

SQL was run with [`scripts/q.sh`](scripts/q.sh) (`docker compose exec postgres psql …`). Every file shows the exact query or command next to its output.

## By incident

| Incident | Files |
|---|---|
| Baseline (what "normal" looks like) | [01-baseline-desert-rose.txt](01-baseline-desert-rose.txt): 5 invoices, 3.4 s, all Accepted, full status history |
| Sample-file analysis (before uploading anything) | [00-sample-file-inspection.txt](00-sample-file-inspection.txt): Ghaf date cell types; Al Noor totals recomputed by hand, predicting which 3 invoices fail BR-CO-15 |
| #1 Oasis | [07-oasis-portal-uploads.txt](07-oasis-portal-uploads.txt) (3 × HTTP 504 at ~60 s via the portal) · [07-oasis-timing.txt](07-oasis-timing.txt) (server finished in 138–157 s; proxy log; per-row lookups) · [07-oasis-db-state.txt](07-oasis-db-state.txt) (per-invoice outcome across uploads; ASP holds exactly one copy of each) |
| #2 API restarts | [02-api-before-load.txt](02-api-before-load.txt) · [02-api-memory-sampler.log](02-api-memory-sampler.log) · [03-make-load-output.txt](03-make-load-output.txt) · [08-api-docker-events-readable.txt](08-api-docker-events-readable.txt) (oom → die 137 → start, ×2) · [08-incident2-logs.txt](08-incident2-logs.txt) · [08-portal-probe.log](08-portal-probe.log) (502s during restart) · [08-incident2-db-after-restart-1.txt](08-incident2-db-after-restart-1.txt) · [10-incident2-workaround.txt](10-incident2-workaround.txt) (Retry recovers Validated; Parsed blocked) · [11-prometheus-api-memory-restarts.txt](11-prometheus-api-memory-restarts.txt) · [12-grafana-alert-state.txt](12-grafana-alert-state.txt) |
| #3 Al Noor | [04-alnoor-reproduce.txt](04-alnoor-reproduce.txt): totals per invoice, ASP BR-CO-15 responses, payload lines and totals, ASP log |
| #4 Sahara | [06-sahara-reproduce.txt](06-sahara-reproduce.txt): 14 Accepted / 26 stuck Submitted, 429s in API and ASP logs, ASP document list, Retry 409, resend → 40 × AE-BR-09, metrics |
| #5 Ghaf | [05-ghaf-reproduce.txt](05-ghaf-reproduce.txt): 4 × AE-BR-04 only; corrected file → 4 × Accepted; real date cells → 4 × Accepted |
| Scope across all sellers | [09-scope-queries.txt](09-scope-queries.txt) |

## Scripts

| Script | Purpose |
|---|---|
| [scripts/q.sh](scripts/q.sh) | Run one SQL query against the lab DB and echo it with its output |
| [scripts/scope.sh](scripts/scope.sh) | Cross-seller scope queries (stuck invoices, stuck imports, Marina Bay, ASP rejections, 429s) |
| [scripts/inspect_samples.py](scripts/inspect_samples.py) | Cell types of Ghaf's dates; exact-decimal recomputation of Al Noor totals |
| [scripts/fix_ghaf_dates.py](scripts/fix_ghaf_dates.py) | Corrected copy of Ghaf's file (text dd/mm/yyyy → yyyy-mm-dd) |
| [scripts/ghaf_real_dates_test.py](scripts/ghaf_real_dates_test.py) | Test copy with real Excel date cells (what Text to Columns → DMY produces), invoice numbers prefixed `TEST-` |
| [scripts/reupload_stuck_number.py](scripts/reupload_stuck_number.py) | Test file re-using an invoice number stuck in Parsed, to show it is blocked |
| [scripts/prom.py](scripts/prom.py) | Export Prometheus series (api memory, heap, up, restarts, queue depth) as a table |

## Files

[files/](files/) holds the test workbooks built by the scripts above.

## Screenshots

See [screenshots/README.md](screenshots/README.md) for the list of Grafana and portal screenshots and what each one shows.

# Schneider Electric Control Narrative — Real Data

Place your Schneider Electric control narrative PDF here.

## File naming
Name the file descriptively, for example:
- `schneider_control_narrative.pdf`
- `SE_pump_station_spec.pdf`

## Running the pipeline on real data

```bash
python run_pipeline.py --input data/schneider_electric/schneider_control_narrative.pdf --real-data
```

The `--real-data` flag marks this as a real-data run in the audit report, which is
important for the paper's real-data validation section.

## What gets produced

Results go to `output/schneider_control_narrative/`:
- `audit_report.html` — full safety audit report
- `knowledge_graph.html` — interactive equipment graph
- `plc_output.st` — generated IEC 61131-3 Structured Text

## Data handling note

All processing is **local only** — Ollama runs on your GPU, no data leaves your machine.
The PDF is not uploaded to any external service.

## For the paper

After running, the audit findings should be:
1. Reviewed by you (or Dr. Raviteja) for domain validity
2. Cross-referenced with known issues in the Schneider Electric system if applicable
3. Reported as the "Real Data Validation" section in the paper (Section 5.2 suggested)

The report includes the number of findings, their types, and IEC 61511 clause references —
all of which are directly citable in the paper.

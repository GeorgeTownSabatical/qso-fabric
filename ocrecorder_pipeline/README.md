# ocrecorder_pipeline

Resumable Orange County Recorder analytics scaffold.

## What it does
- Generates bounded query slices (surname + date windows).
- Supports resumable acquisition bookkeeping.
- Normalizes recorder rows (names, APNs, entities).
- Produces anomaly analytics and parcel alerts.
- Builds title-chain and community graph outputs.

## Folder layout
- `data/raw_html`: saved response pages.
- `data/parsed`: parsed row-level CSV files.
- `data/normalized`: normalized canonical records.
- `data/exports`: ranked report outputs.
- `manifests`: query slices and crawl run manifests.

## Quickstart
```bash
cd ocrecorder_pipeline
python3 -m pip install -e .
ocrecorder run-demo --output-dir data/exports
```

## Analyze an input CSV
Expected columns:
- `doc_number`, `record_date`, `doc_type`, `apn`, `grantor`, `grantee`, `notary`

```bash
ocrecorder analyze \
  --input-csv data/parsed/sample_records.csv \
  --normalized-out data/normalized/normalized_records.csv \
  --output-dir data/exports
```

## Generate query slices
```bash
ocrecorder slice \
  --surnames SMITH,GARCIA,NGUYEN \
  --year-start 1982 \
  --year-end 1984 \
  --quarters \
  --output manifests/query_slices.json
```

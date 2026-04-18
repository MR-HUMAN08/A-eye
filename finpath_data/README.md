# FinPath Data Pipeline

This folder holds the first-pass dataset ingestion and preprocessing layer for FinPath.

## What it does

- Loads local CSVs from the hackathon workspace.
- Pulls external CSV and Hugging Face datasets listed in `dataset_manifest.json`.
- Removes null rows, duplicate rows, and repeated normalized examples.
- Converts tabular data into two outputs:
  - instruction-style samples for fine-tuning
  - RAG-ready text records for retrieval

## Outputs

- `data/processed/merged_records.jsonl`
- `data/processed/instruction_corpus.jsonl`
- `data/processed/rag_corpus.jsonl`
- `data/processed/summary.json`

## Notes

- Kaggle sources are marked in the manifest and require manual download or Kaggle API credentials.
- The script is designed to be extended with repo-derived knowledge sources later.
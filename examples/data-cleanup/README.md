# CSV cleanup sample

Synthetic portfolio demonstration for the human-owned, AI-assisted service.
This is not client work and contains no client data.

Run `python3 clean.py` in this directory. Python's standard library is sufficient.

Eight input rows become five valid output rows. One exact duplicate is removed
after normalization. Two invalid rows are flagged with their source line and
reason instead of silently guessed or discarded. Text is trimmed, categories
lowercased, dates standardized to ISO format and amounts formatted to two decimals.

Deliverables: `input.csv`, `cleaned.csv`, `clean.py`, and `report.json`.
The script checks that every input row is accounted for in the output, duplicate
count, or rejection report. Production rules would be agreed against a client's
actual input and acceptance criteria.

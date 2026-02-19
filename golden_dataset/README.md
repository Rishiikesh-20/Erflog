# Golden Dataset — ERFOLG M1 (Data Scientist)

This folder contains the **ground truth** dataset for Section 8.2 of the paper
(Offline Ranking / Precision@K evaluation).

## Folder Structure

```
golden_dataset/
├── README.md                    ← You are here
├── extract_jobs.py              ← Run this to pull 50 JDs from Supabase
├── resume_metadata.csv          ← Summary info for all 10 resumes
├── golden_labels_template.csv   ← Initial template (replaced by extract_jobs.py)
├── job_descriptions.csv         ← Generated: 50 job descriptions
├── golden_labels.csv            ← Generated: 500 pairs (10 resumes × 50 jobs)
└── resumes/
    ├── README.txt
    ├── fresher_01.pdf
    ├── fresher_02.pdf
    ├── backend_01.pdf
    ├── backend_02.pdf
    ├── backend_03.pdf
    ├── frontend_01.pdf
    ├── frontend_02.pdf
    ├── frontend_03.pdf
    ├── datasci_01.pdf
    └── datasci_02.pdf
```

## How to Use

### Step 1: Extract Job Descriptions
```bash
cd Erflog/backend
python ../golden_dataset/extract_jobs.py
```
This creates `job_descriptions.csv` (50 JDs) and `golden_labels.csv` (500 pairs to label).

### Step 2: Collect Resumes
Place 10 PDF resumes in `resumes/` following the naming convention above.
Update `resume_metadata.csv` with each resume's details.

### Step 3: Manual Labeling
Open `golden_labels.csv` and for each row:
- Set `is_relevant` = **1** (good match) or **0** (not a match)
- Optionally add `relevance_reason`

### Step 4: Benchmark (Day 2)
Use the labeled dataset to compare ERFOLG vs. keyword search vs. vector-only search.

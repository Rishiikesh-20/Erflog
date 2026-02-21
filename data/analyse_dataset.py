import pandas as pd

# Load dataset
df = pd.read_csv("golden_labels.csv")

# Total rows
total_rows = len(df)

# Unique resumes
unique_resumes = df["resume_id"].nunique()

# Categories
categories = df["resume_category"].unique()

# Relevant / Non-relevant count
relevant_count = df["is_relevant"].sum()
non_relevant_count = total_rows - relevant_count

# Rows per resume (should be 5)
rows_per_resume = df.groupby("resume_id").size()

print("=== DATASET SUMMARY ===")
print("Total Rows:", total_rows)
print("Unique Resumes:", unique_resumes)
print("Categories:", categories)
print("Relevant Jobs:", relevant_count)
print("Non-Relevant Jobs:", non_relevant_count)

print("\nRows Per Resume:")
print(rows_per_resume)

# Precision@5 per resume
precision = df.groupby("resume_id")["is_relevant"].mean()

print("\nPrecision@5 per Resume:")
print(precision)

print("\nAverage Precision@5:", precision.mean())

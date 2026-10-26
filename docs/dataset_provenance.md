# Dataset Provenance, Methodology, and Validation Report

> **Dataset:** Academic Examination Questions Benchmark (AEQ-Bench v1.0.0)  
> **Target Dimensions:** Revised Bloom’s Taxonomy (6 Classes) & Estimated Difficulty (3 Classes)  
> **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)

---

## 1. Executive Summary

This document establishes the empirical provenance, annotation methodology, class distributions, and research limitations of the **Academic Examination Questions Benchmark (AEQ-Bench)**. The dataset serves as the standardized training, validation, and held-out test repository for the **Automatic Question Paper Difficulty Analyzer** research pipeline.

---

## 2. Dataset Provenance and Domain Coverage

The dataset comprises **570 examination questions** sourced from university-level computer science and engineering examination archives across eight foundational curricula:

| Subject / Domain | Question Count | Proportion |
| :--- | :---: | :---: |
| **Discrete Mathematics** | 76 | 13.33% |
| **Software Engineering** | 75 | 13.16% |
| **Engineering Physics** | 73 | 12.81% |
| **Database Systems** | 72 | 12.63% |
| **Data Structures & Algorithms** | 71 | 12.46% |
| **Operating Systems** | 71 | 12.46% |
| **Computer Networks** | 66 | 11.58% |
| **Artificial Intelligence** | 66 | 11.58% |
| **Total** | **570** | **100.0%** |

---

## 3. Class Distributions & Empirical Balance

### 3.1 Task A: Revised Bloom’s Taxonomy (6 Cognitive Levels)
The dataset exhibits balanced cognitive coverage across Anderson & Krathwohl's taxonomy, with an Imbalance Ratio ($IR = N_{\max} / N_{\min}$) of only **1.26**:

| Level | Description | Count | Percentage |
| :--- | :--- | :---: | :---: |
| **Remember (C1)** | Factual recall, definitions, naming | 110 | 19.30% |
| **Understand (C2)** | Explaining, classifying, summarizing | 96 | 16.84% |
| **Apply (C3)** | Step-by-step algorithms, calculations | 97 | 17.02% |
| **Analyze (C4)** | Comparative analysis, decomposition | 91 | 15.96% |
| **Evaluate (C5)** | Critiquing, assessing architectural trade-offs | 87 | 15.26% |
| **Create (C6)** | Designing new algorithms, formulating systems | 89 | 15.61% |

### 3.2 Task B: Question Difficulty (3 Categories & Continuous Score)
Difficulty is categorized into 3 tiers ($IR = 2.36$), complemented by a normalized continuous difficulty score in the interval $[0.15, 0.94]$:

| Difficulty Tier | Count | Percentage | Continuous Score Range |
| :--- | :---: | :---: | :---: |
| **Easy** | 113 | 19.82% | 0.15 – 0.30 |
| **Medium** | 190 | 33.33% | 0.40 – 0.65 |
| **Hard** | 267 | 46.84% | 0.70 – 0.94 |

---

## 4. Critical Research Finding: Orthogonality & Construct Validity

A cross-tabulation of Bloom's cognitive levels against Difficulty tiers reveals:

```
Difficulty Tier    Easy     Medium     Hard
Bloom's Level
--------------------------------------------
Remember            109          1        0
Understand            4         92        0
Apply                 0         97        0
Analyze               0          0       91
Evaluate              0          0       87
Create                0          0       89
```

### Scholarly Implication:
1. **Rubric-Derived Difficulty:** In current institutional practice, examination setters designate higher-order cognitive questions (*Analyze*, *Evaluate*, *Create*) as *Hard*, application questions as *Medium*, and recall questions as *Easy*.
2. **Threat to Construct Validity:** While intuitive from an instructional rubric standpoint, a model trained on this correlation will treat Difficulty as a surrogate for Cognitive Level.
3. **Research Protocol:**
   - The platform treats the two tasks as **distinct classification heads**.
   - Text preprocessing explicitly strips trailing examination marks (e.g. `[10 Marks]`) to prevent artificial leakage into text representation models.
   - Teachers retain the ability to override rubric difficulty based on empirical cohort performance (e.g., re-labeling an obscure recall question as *Hard*).

---

## 5. Stratification and Leakage Prevention

The dataset was partitioned using a **70% / 15% / 15%** stratified split (`random_state=42`):

- **Train Set:** 399 questions (`data/processed/train.csv`)
- **Validation Set:** 85 questions (`data/processed/val.csv`)
- **Held-Out Test Set:** 86 questions (`data/processed/test.csv`)

### Verification Checks:
- $\text{Train} \cap \text{Val} = \emptyset$ (0 shared question IDs, 0 shared cleaned texts)
- $\text{Train} \cap \text{Test} = \emptyset$ (0 shared question IDs, 0 shared cleaned texts)
- $\text{Val} \cap \text{Test} = \emptyset$ (0 shared question IDs, 0 shared cleaned texts)
- Stratification preserved across all 6 Bloom levels with $<1.5\%$ variance across splits.

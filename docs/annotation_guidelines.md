# Annotation Guidelines: Bloom’s Taxonomy and Question Difficulty

> **AI Exam Analyzer Research Protocol**  
> Version: 1.0.0  
> Date: October 2026  
> Authors: NLP Research & Evaluation Team

---

## 1. Purpose and Scope

This protocol establishes standardized annotation criteria for labeling academic examination questions across two independent classification dimensions:

1. **Cognitive Level:** According to Anderson & Krathwohl's Revised Bloom’s Taxonomy (6 levels).
2. **Estimated Question Difficulty:** Categorized into Easy, Medium, and Hard.

### Critical Principle: Separation of Dimensions
Cognitive complexity and question difficulty are **orthogonal concepts**:
- A question requiring higher-order thinking (e.g., *Evaluate*) is not automatically *Hard*.
- A question requiring factual recall (e.g., *Remember*) is not automatically *Easy* if the required knowledge is obscure or fine-grained.

Annotators must evaluate each dimension independently without allowing the judgment of one to bias the other.

---

## 2. Dimension 1: Revised Bloom’s Taxonomy (Cognitive Demand)

### Level 1: Remember (C1)
- **Definition:** Retrieving, recognizing, and recalling relevant knowledge from long-term memory.
- **Cognitive Processes:** Recognizing, recalling, naming, listing, defining, stating.
- **Typical Keywords:** Define, list, state, name, identify, label, who, when, what.
- **Example:** *"Define the term 'deadlock' in operating systems."*
- **Caution:** If the question asks for a definition in the student's *own words* or requires contrasting, it moves to *Understand*.

### Level 2: Understand (C2)
- **Definition:** Constructing meaning from oral, written, and graphic communications through interpreting, exemplifying, classifying, summarizing, inferring, comparing, and explaining.
- **Cognitive Processes:** Interpreting, clarifying, paraphrasing, exemplifying, classifying, summarizing, inferring, comparing, explaining.
- **Typical Keywords:** Explain, summarize, paraphrase, describe, contrast, classify, interpret.
- **Example:** *"Explain how virtual memory allows execution of processes larger than physical memory."*

### Level 3: Apply (C3)
- **Definition:** Carrying out or using a procedure, formula, or algorithm in a given situation.
- **Cognitive Processes:** Executing, implementing, calculating, solving with a known procedure.
- **Typical Keywords:** Calculate, compute, apply, solve, execute, demonstrate, use.
- **Example:** *"Given a page reference string and 3 page frames, calculate the number of page faults using the FIFO page replacement algorithm."*

### Level 4: Analyze (C4)
- **Definition:** Breaking material into constituent parts, determining how the parts relate to one another and to an overall structure or purpose.
- **Cognitive Processes:** Differentiating, organizing, attributing, deconstructing.
- **Typical Keywords:** Analyze, differentiate, distinguish, decompose, diagram, examine structure.
- **Example:** *"Analyze the time and space complexity trade-offs between Dijkstra's algorithm and the Bellman-Ford algorithm in sparse graphs."*

### Level 5: Evaluate (C5)
- **Definition:** Making judgments based on criteria and standards, such as checking for internal consistency or critiquing based on external metrics.
- **Cognitive Processes:** Checking, coordinating, detecting, monitoring, critiquing, judging.
- **Typical Keywords:** Critique, evaluate, justify, assess, defend, prioritize, rate.
- **Example:** *"Critique the use of microservice architecture versus a monolithic architecture for an early-stage startup with a 3-person engineering team. Justify your recommendation."*

### Level 6: Create (C6)
- **Definition:** Putting elements together to form a novel, coherent whole or making an original product; reorganizing elements into a new pattern or structure.
- **Cognitive Processes:** Generating, planning, producing, designing, formulating, synthesizing.
- **Typical Keywords:** Design, formulate, construct, propose, synthesize, develop, invent.
- **Example:** *"Design a rate-limiting middleware for an API gateway that supports sliding-window counters and distributes state across multiple nodes."*

---

## 3. Dimension 2: Question Difficulty Classification

Difficulty is annotated relative to a typical student who has completed the relevant course syllabus.

### Easy (D1)
- **Criteria:** Direct recall or single-step conceptual question; high probability of correct answer (>70% of prepared students); no tricky edge cases or nested logic.
- **Example:** *"State Ohm's Law and its mathematical formula."*

### Medium (D2)
- **Criteria:** Multi-step reasoning required; application of standard procedures to moderate scenarios; synthesis of two connected concepts; typical pass rate 40%–70%.
- **Example:** *"Calculate the equivalent resistance and total current drawn in a combined series-parallel circuit containing four resistors."*

### Hard (D3)
- **Criteria:** Non-standard problem formulation, boundary-case analysis, synthesis of three or more disparate concepts, or evaluation requiring rigorous counter-arguments; estimated pass rate <40%.
- **Example:** *"Prove whether the problem of determining if a given Turing Machine halts on all inputs is decidable, semi-decidable, or undecidable using Rice's Theorem."*

---

## 4. Handling Edge Cases & Multi-Part Questions

1. **Multi-Part Questions:** If a question contains sub-questions (e.g., 2a and 2b), annotate each sub-question individually whenever possible. If forced to annotate as a single unit, assign the label corresponding to the **highest cognitive level** that accounts for at least 50% of the total marks.
2. **Context Over Action Verbs:** Do not label solely on the first verb. Read the complete complement. (e.g., *"Explain the steps to design a new compiler"* is *Create*, not merely *Understand*).
3. **Ambiguity:** If the label is genuinely ambiguous between two adjacent levels, flag the item for secondary review and record both the primary choice and alternative choice.

---

## 5. Quality Assurance and Inter-Annotator Agreement

To establish research validity:
- A representative sample of at least 20% of dataset questions must be independently coded by at least two domain experts.
- Inter-annotator agreement will be measured using:
  - **Cohen’s Kappa ($\kappa$)** for pairwise agreement.
  - **Fleiss’ Kappa** for multi-annotator consistency.
- Any item with annotator disagreement must be resolved through a documented consensus session.

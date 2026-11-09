# LearnLens – Student Outcomes and Risk Analysis

**Code Sample | Data Scientist – Office of the New York State Attorney General**

**Applicant:** Yogananda Manjunath  
**Position Reference:** RAD_NYC_DAS_6463

**Technologies:** Python, PostgreSQL, SQL, Excel Power Query, Power BI

**GitHub Repository:** https://github.com/Yogananda16/learn-lens

**SQL Code:** https://github.com/Yogananda16/learn-lens/blob/main/sql/views.sql

---

## 1. Project Overview

LearnLens is a student data analytics project designed to identify attendance trends, withdrawal patterns, and students who may need early support.

Educational programs collect large amounts of data, but identifying meaningful patterns can be difficult when information is spread across spreadsheets and different systems.

I developed LearnLens to organize this information, investigate performance patterns, and present findings in a way that program teams can easily understand.

## 2. Dataset

The project uses a **synthetic dataset** containing:

- **214 students**
- **12 cohorts**
- **6 educational programs**

The dataset includes enrollment records, attendance, grades, and student survey information.

## 3. Data Analysis and Methodology

I used Python to generate sample datasets, Excel Power Query to clean and prepare records, and PostgreSQL to organize and analyze the data.

I developed **7 SQL reporting views** to:

1. Calculate student attendance rates.
2. Identify students with low attendance or failing grades.
3. Analyze enrollment and withdrawal trends.
4. Compare performance across cohorts.
5. Calculate academic performance metrics.
6. Summarize student survey responses.
7. Compare attendance patterns with Connecticut statewide benchmarks.

The analysis uses SQL joins, aggregations, window functions, and conditional logic to produce consistent reporting metrics.

## 4. Results and Impact

Developed an interactive Power BI dashboard that:

- **Identifies at-risk students** based on attendance and academic performance.
- **Highlights withdrawal patterns** across 12 cohorts.
- **Enables faster investigation** of performance trends through interactive filters.
- **Protects sensitive information** by separating student records from reporting data.

These capabilities demonstrate how data analysis can help program teams identify problems earlier and make informed decisions.

## 5. Dashboard

![LearnLens Power BI Dashboard](https://github.com/user-attachments/assets/f4649c6b-47b6-4410-b73b-99fc38d43c76)

*Figure 1: Interactive Power BI dashboard showing student performance, attendance trends, cohort comparisons, and risk indicators.*

## 6. SQL Code Sample

The primary code sample is the PostgreSQL reporting layer developed for this project.

**[View SQL Analysis Code](https://github.com/Yogananda16/learn-lens/blob/main/sql/views.sql)**

**[View Database Schema](https://github.com/Yogananda16/learn-lens/blob/main/sql/schema.sql)**

The SQL implementation demonstrates:

- Data aggregation and validation
- Complex joins and Common Table Expressions (CTEs)
- Window functions for ranking cohorts
- Conditional logic for risk classification
- Handling missing values
- Calculating attendance, retention, and performance metrics

## 7. Data Privacy and Limitations

All student records in this project are **synthetic**.

The database separates raw student information from reporting views. Personally identifiable information, such as student names and dates of birth, is excluded from the reporting layer.

The project demonstrates an analytical methodology rather than findings about actual students. Risk indicators are based on defined attendance and grade thresholds and are not validated predictive outcomes.

## 8. Relevance to Investigative Data Science

This project demonstrates my approach to solving data problems:

**Collect data → Clean and validate → Investigate patterns → Identify anomalies → Communicate findings**

These are the same analytical principles I hope to apply when supporting investigations and research at the Office of the New York State Attorney General.

---

**Developed by Yogananda Manjunath**  
MS in Data Science | University of New Haven

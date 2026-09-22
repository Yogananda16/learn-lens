-- =============================================================================
-- LearnLens: reporting views
-- =============================================================================
-- Everything in this file lives in the "reporting" schema. These views are
-- what Power BI (or APEX, or any other tool) should connect to -- never the
-- raw "sis" tables directly. That keeps two things true at once:
--   1. No PII leaves the source tables. No first_name, last_name, or
--      date_of_birth appears anywhere below. Only student_id (a number,
--      not a name) is carried through, which is what lets a director click
--      into "who is this row" without exposing a name on a shared dashboard.
--   2. The reporting logic (what counts as "chronic absence", what counts
--      as "at risk") is defined ONCE, here, in SQL -- not re-built inside
--      Power BI, APEX, or a spreadsheet. If dae moves from APEX to Power BI,
--      these views don't change; only the tool reading them does.
--
-- Definitions used throughout:
--   attendance_rate   = (Present + Tardy) / total scheduled sessions
--   chronic absence   = attendance_rate < 90%  (CT state definition: missing
--                        10%+ of enrolled days, for any reason, excused
--                        absences included)
--   at risk           = an ACTIVE enrollment that is chronically absent
--                        and/or trending below a C average
--
-- Oracle/APEX notes: ROUND, AVG, RANK, FILTER-less CASE all translate
-- directly. Postgres's FILTER (WHERE ...) has no Oracle equivalent --
-- the CASE WHEN ... THEN 1 ELSE 0 END form used below works in both.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Foundation view: one row per enrollment. Everything else is built on top
-- of this, so the attendance/grade math is written exactly once.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_enrollment_metrics AS
WITH att AS (
    SELECT
        enrollment_id,
        COUNT(*) AS sessions_total,
        SUM(CASE WHEN status IN ('Present', 'Tardy') THEN 1 ELSE 0 END) AS sessions_attended
    FROM sis.attendance
    GROUP BY enrollment_id
),
grd AS (
    SELECT
        enrollment_id,
        COUNT(score)          AS courses_graded,
        ROUND(AVG(score), 1)  AS avg_score
    FROM sis.grades
    GROUP BY enrollment_id
)
SELECT
    e.enrollment_id,
    e.student_id,
    e.cohort_id,
    e.status,
    e.enroll_date,
    e.withdraw_date,
    COALESCE(att.sessions_total, 0)    AS sessions_total,
    COALESCE(att.sessions_attended, 0) AS sessions_attended,
    ROUND(
        COALESCE(att.sessions_attended, 0)::numeric
        / NULLIF(att.sessions_total, 0), 3
    ) AS attendance_rate,
    -- CT definition: missing 10%+ of days => attendance_rate < 0.90
    (COALESCE(att.sessions_attended, 0)::numeric / NULLIF(att.sessions_total, 0)) < 0.90
        AS chronic_absent,
    grd.courses_graded,
    grd.avg_score
FROM sis.enrollments e
LEFT JOIN att ON att.enrollment_id = e.enrollment_id
LEFT JOIN grd ON grd.enrollment_id = e.enrollment_id;

COMMENT ON VIEW reporting.vw_enrollment_metrics IS
    'One row per enrollment: attendance rate, chronic-absence flag, average score. Foundation for the other reporting views.';

-- -----------------------------------------------------------------------------
-- Cohort retention: enrolled / completed / withdrawn / active, per cohort.
-- Includes a RANK() window function -- ranks cohorts by withdrawal rate
-- without collapsing the other rows the way GROUP BY + HAVING would.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_cohort_retention AS
SELECT
    c.cohort_id,
    c.cohort_name,
    p.program_name,
    p.track,
    c.location,
    c.funder,
    c.start_date,
    c.end_date,
    COUNT(*) AS enrolled,
    SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
    SUM(CASE WHEN m.status = 'Withdrawn' THEN 1 ELSE 0 END) AS withdrawn,
    SUM(CASE WHEN m.status = 'Active'    THEN 1 ELSE 0 END) AS active,
    ROUND(100.0 * SUM(CASE WHEN m.status = 'Withdrawn' THEN 1 ELSE 0 END) / COUNT(*), 1)
        AS withdrawal_pct,
    RANK() OVER (ORDER BY
        100.0 * SUM(CASE WHEN m.status = 'Withdrawn' THEN 1 ELSE 0 END) / COUNT(*) DESC
    ) AS withdrawal_rank
FROM reporting.vw_enrollment_metrics m
JOIN sis.cohorts  c ON c.cohort_id  = m.cohort_id
JOIN sis.programs p ON p.program_id = c.program_id
GROUP BY c.cohort_id, c.cohort_name, p.program_name, p.track, c.location,
         c.funder, c.start_date, c.end_date;

COMMENT ON VIEW reporting.vw_cohort_retention IS
    'Enrollment counts and withdrawal % per cohort, with a rank (1 = highest withdrawal rate).';

-- -----------------------------------------------------------------------------
-- Cohort attendance: average attendance rate and chronic-absence % per
-- cohort. Kept separate from retention so a short program (few sessions,
-- attendance_rate very sensitive) doesn't get mixed into the same page.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_cohort_attendance AS
SELECT
    c.cohort_id,
    c.cohort_name,
    p.program_name,
    c.location,
    COUNT(*) FILTER (WHERE m.sessions_total > 0) AS students_measured,
    ROUND(100.0 * AVG(m.attendance_rate), 1) AS avg_attendance_pct,
    ROUND(100.0 * AVG(CASE WHEN m.chronic_absent THEN 1 ELSE 0 END), 1) AS chronic_absence_pct
FROM reporting.vw_enrollment_metrics m
JOIN sis.cohorts  c ON c.cohort_id  = m.cohort_id
JOIN sis.programs p ON p.program_id = c.program_id
WHERE m.sessions_total > 0
GROUP BY c.cohort_id, c.cohort_name, p.program_name, c.location;

COMMENT ON VIEW reporting.vw_cohort_attendance IS
    'Average attendance % and chronic-absence % per cohort. Short programs (few sessions) make this more sensitive -- compare with caution.';

-- -----------------------------------------------------------------------------
-- At-risk students: currently ACTIVE enrollments only (you can't intervene
-- on someone who already left or finished). IDs only, no names.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_at_risk_students AS
SELECT
    m.student_id,
    m.enrollment_id,
    c.cohort_id,
    c.cohort_name,
    p.program_name,
    ROUND(100.0 * m.attendance_rate, 1) AS attendance_pct,
    m.chronic_absent,
    m.avg_score,
    CASE
        WHEN m.chronic_absent AND m.avg_score IS NOT NULL AND m.avg_score < 70
            THEN 'High: chronic absence + failing average'
        WHEN m.chronic_absent
            THEN 'Medium: chronic absence'
        WHEN m.avg_score IS NOT NULL AND m.avg_score < 70
            THEN 'Medium: failing average'
        ELSE 'Low: on track'
    END AS risk_level
FROM reporting.vw_enrollment_metrics m
JOIN sis.cohorts  c ON c.cohort_id  = m.cohort_id
JOIN sis.programs p ON p.program_id = c.program_id
WHERE m.status = 'Active'
  AND (m.chronic_absent OR (m.avg_score IS NOT NULL AND m.avg_score < 70));

COMMENT ON VIEW reporting.vw_at_risk_students IS
    'Currently-active students flagged for chronic absence and/or a failing average. student_id only -- no names. Join back to sis.students (restricted access) to resolve an identity.';

-- -----------------------------------------------------------------------------
-- Grades by cohort and course.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_grades_by_cohort AS
SELECT
    c.cohort_id,
    c.cohort_name,
    co.course_name,
    COUNT(g.score) AS graded_count,
    ROUND(AVG(g.score), 1) AS avg_score,
    ROUND(100.0 * SUM(CASE WHEN g.letter_grade IN ('A', 'B') THEN 1 ELSE 0 END)
          / NULLIF(COUNT(g.score), 0), 1) AS pct_a_or_b
FROM sis.grades g
JOIN sis.enrollments e ON e.enrollment_id = g.enrollment_id
JOIN sis.cohorts    c  ON c.cohort_id     = e.cohort_id
JOIN sis.courses    co ON co.course_id    = g.course_id
GROUP BY c.cohort_id, c.cohort_name, co.course_name;

COMMENT ON VIEW reporting.vw_grades_by_cohort IS
    'Average score and % earning A/B, per cohort and course.';

-- -----------------------------------------------------------------------------
-- Survey summary: satisfaction/belonging averages and response rate.
-- COUNT(DISTINCT ...) guards against join fan-out (a student with 2+
-- responses should not inflate the "enrolled" denominator).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_survey_summary AS
SELECT
    c.cohort_id,
    c.cohort_name,
    COUNT(DISTINCT e.enrollment_id) AS enrolled,
    COUNT(DISTINCT s.enrollment_id) AS responded,
    ROUND(100.0 * COUNT(DISTINCT s.enrollment_id) / COUNT(DISTINCT e.enrollment_id), 0)
        AS response_rate_pct,
    ROUND(AVG(s.satisfaction), 2) AS avg_satisfaction,
    ROUND(AVG(s.belonging), 2)    AS avg_belonging
FROM sis.cohorts c
JOIN sis.enrollments e ON e.cohort_id = c.cohort_id
LEFT JOIN sis.survey_responses s ON s.enrollment_id = e.enrollment_id
GROUP BY c.cohort_id, c.cohort_name;

COMMENT ON VIEW reporting.vw_survey_summary IS
    'Survey response rate and average satisfaction/belonging, per cohort.';

-- -----------------------------------------------------------------------------
-- Our chronic-absence rate vs. the public CT statewide benchmark, by year.
-- This is the "our cohorts vs. CT statewide" comparison for the dashboard.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW reporting.vw_attendance_vs_ct_benchmark AS
SELECT
    EXTRACT(YEAR FROM c.start_date)::int AS cohort_start_year,
    ROUND(100.0 * AVG(CASE WHEN m.chronic_absent THEN 1 ELSE 0 END), 1) AS our_chronic_pct,
    b.value AS ct_statewide_chronic_pct
FROM reporting.vw_enrollment_metrics m
JOIN sis.cohorts c ON c.cohort_id = m.cohort_id
LEFT JOIN sis.ct_benchmarks b
    ON b.metric = 'chronic_absenteeism_rate_pct'
    -- CT school year "2023-24" starts in fall 2023, so a cohort starting
    -- in 2023 lines up with the "2023-24" benchmark row.
    AND b.school_year = EXTRACT(YEAR FROM c.start_date)::text || '-'
        || RIGHT((EXTRACT(YEAR FROM c.start_date)::int + 1)::text, 2)
WHERE m.sessions_total > 0
GROUP BY EXTRACT(YEAR FROM c.start_date), b.value
ORDER BY 1;

COMMENT ON VIEW reporting.vw_attendance_vs_ct_benchmark IS
    'Our chronic-absence rate by cohort start year, next to the public CT statewide rate for the matching school year.';

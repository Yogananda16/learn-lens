-- =============================================================================
-- LearnLens: database schema (PostgreSQL)
-- =============================================================================
-- Two schemas keep sensitive data separate from reporting:
--   sis        source tables, PowerSchool-style. Contains student names + birth
--              dates (PII). Only the data team should have access.
--   reporting  views for dashboards. IDs only, no names. Power BI / APEX / a
--              chatbot read from here, never from sis.
--
-- CHECK constraints are the database's own data-quality guard: the bad rows in
-- the messy raw files (score 950, rating 55, status typos) are rejected.
--
-- Oracle / APEX notes for a future migration:
--   TEXT -> VARCHAR2(n)   NUMERIC -> NUMBER   DATE -> DATE
--   COALESCE works in both (Oracle also has NVL)
--   LIMIT n -> FETCH FIRST n ROWS ONLY
--   ILIKE -> UPPER(x) LIKE UPPER(y)
--   window functions, CTEs and joins are the same in both
-- =============================================================================

DROP SCHEMA IF EXISTS reporting CASCADE;
DROP SCHEMA IF EXISTS sis CASCADE;
CREATE SCHEMA sis;
CREATE SCHEMA reporting;

-- ---------- Reference tables -------------------------------------------------

CREATE TABLE sis.programs (
    program_id         TEXT PRIMARY KEY,
    program_name       TEXT NOT NULL,
    track              TEXT NOT NULL CHECK (track IN ('High School', 'Adult')),
    subject            TEXT NOT NULL,
    length_weeks       INTEGER NOT NULL CHECK (length_weeks > 0),
    grade_band         TEXT,
    sessions_per_week  INTEGER CHECK (sessions_per_week > 0)
);

CREATE TABLE sis.terms (
    term_id      TEXT PRIMARY KEY,
    term_name    TEXT NOT NULL,
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    school_year  TEXT NOT NULL,
    CHECK (end_date > start_date)
);

CREATE TABLE sis.courses (
    course_id      TEXT PRIMARY KEY,
    program_id     TEXT NOT NULL REFERENCES sis.programs (program_id),
    course_name    TEXT NOT NULL,
    contact_hours  INTEGER CHECK (contact_hours > 0)
);

CREATE TABLE sis.cohorts (
    cohort_id      TEXT PRIMARY KEY,
    program_id     TEXT NOT NULL REFERENCES sis.programs (program_id),
    cohort_name    TEXT NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    location       TEXT NOT NULL CHECK (location IN ('New Haven', 'Stamford')),
    funder         TEXT,
    planned_seats  INTEGER CHECK (planned_seats > 0),
    CHECK (end_date > start_date)
);

-- ---------- People (PII) -----------------------------------------------------

CREATE TABLE sis.students (
    student_id               INTEGER PRIMARY KEY,
    first_name               TEXT NOT NULL,
    last_name                TEXT NOT NULL,
    gender                   TEXT CHECK (gender IN ('Female', 'Male', 'Non-binary')),
    date_of_birth            DATE,
    entry_grade              TEXT CHECK (entry_grade IN ('9', '10', '11', '12', 'Adult')),
    race_ethnicity           TEXT,
    home_town                TEXT,
    school_district          TEXT,
    econ_disadvantaged_flag  CHAR(1) CHECK (econ_disadvantaged_flag IN ('Y', 'N'))
);

-- ---------- Activity ---------------------------------------------------------

CREATE TABLE sis.enrollments (
    enrollment_id    TEXT PRIMARY KEY,
    student_id       INTEGER NOT NULL REFERENCES sis.students (student_id),
    cohort_id        TEXT NOT NULL REFERENCES sis.cohorts (cohort_id),
    enroll_date      DATE NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('Active', 'Completed', 'Withdrawn')),
    withdraw_date    DATE,
    withdraw_reason  TEXT,
    UNIQUE (student_id, cohort_id),                       -- one seat per student per cohort
    CHECK (withdraw_date IS NULL OR withdraw_date >= enroll_date),
    CHECK ((status = 'Withdrawn') = (withdraw_date IS NOT NULL))
);

CREATE TABLE sis.attendance (
    attendance_id  TEXT PRIMARY KEY,
    enrollment_id  TEXT NOT NULL REFERENCES sis.enrollments (enrollment_id),
    session_date   DATE NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('Present', 'Absent', 'Excused', 'Tardy')),
    UNIQUE (enrollment_id, session_date)                  -- no double-counted sessions
);

CREATE TABLE sis.grades (
    grade_id       TEXT PRIMARY KEY,
    enrollment_id  TEXT NOT NULL REFERENCES sis.enrollments (enrollment_id),
    course_id      TEXT NOT NULL REFERENCES sis.courses (course_id),
    term_id        TEXT NOT NULL REFERENCES sis.terms (term_id),
    score          NUMERIC(4,1) CHECK (score IS NULL OR score BETWEEN 0 AND 100),
    letter_grade   TEXT NOT NULL CHECK (letter_grade IN ('A', 'B', 'C', 'D', 'F', 'W')),
    UNIQUE (enrollment_id, course_id),
    CHECK ((letter_grade = 'W') = (score IS NULL))        -- withdrawn = no score
);

CREATE TABLE sis.survey_responses (
    response_id    TEXT PRIMARY KEY,
    enrollment_id  TEXT NOT NULL REFERENCES sis.enrollments (enrollment_id),
    survey_date    DATE NOT NULL,
    survey_type    TEXT NOT NULL CHECK (survey_type IN ('Mid-Program', 'End-of-Program', 'Withdrawal')),
    satisfaction   INTEGER CHECK (satisfaction BETWEEN 1 AND 5),
    belonging      INTEGER CHECK (belonging BETWEEN 1 AND 5),
    comment        TEXT
);

-- ---------- External benchmarks ---------------------------------------------

CREATE TABLE sis.ct_benchmarks (
    school_year  TEXT NOT NULL,
    metric       TEXT NOT NULL,
    geography    TEXT NOT NULL,
    value        NUMERIC(5,1) NOT NULL,
    definition   TEXT,
    source       TEXT,
    PRIMARY KEY (school_year, metric, geography)
);

-- ---------- Indexes on foreign keys (speed up joins) -------------------------

CREATE INDEX ix_cohorts_program      ON sis.cohorts (program_id);
CREATE INDEX ix_enrollments_student  ON sis.enrollments (student_id);
CREATE INDEX ix_enrollments_cohort   ON sis.enrollments (cohort_id);
CREATE INDEX ix_attendance_enroll    ON sis.attendance (enrollment_id);
CREATE INDEX ix_grades_enroll        ON sis.grades (enrollment_id);
CREATE INDEX ix_survey_enroll        ON sis.survey_responses (enrollment_id);

-- ---------- Built-in documentation (this IS the start of the data dictionary)

COMMENT ON SCHEMA sis IS 'Source tables (PowerSchool-style). Contains PII. Restricted access.';
COMMENT ON SCHEMA reporting IS 'Dashboard-safe views. Student IDs only, no names or birth dates.';
COMMENT ON TABLE  sis.enrollments IS 'One row per student per cohort. status: Active, Completed or Withdrawn.';
COMMENT ON TABLE  sis.attendance IS 'One row per student per scheduled session up to withdrawal or today.';
COMMENT ON COLUMN sis.attendance.status IS 'Present and Tardy count as attended. Absent and Excused count as missed.';
COMMENT ON COLUMN sis.grades.letter_grade IS 'W = withdrawn before course end; score is NULL.';
COMMENT ON COLUMN sis.students.entry_grade IS 'Grade level at first enrollment (9-12) or Adult.';
COMMENT ON COLUMN sis.students.econ_disadvantaged_flag IS 'Y/N. Synthetic; used only for equity gap analysis.';
COMMENT ON COLUMN sis.ct_benchmarks.value IS 'Percent. Chronic absence = missing 10% or more of days enrolled, for any reason.';

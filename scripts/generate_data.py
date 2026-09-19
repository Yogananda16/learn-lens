"""
LearnLens - synthetic data generator
====================================
Creates PowerSchool-style student data for a fictional learning program.

Outputs (relative to repo root):
  data/clean/*.csv      the "truth" tables (what the data should look like)
  data/raw/*.csv        the same tables with deliberate mess (for the cleaning step)
  data/raw/_answer_key_injected_issues.csv   what mess was added, and how much
  data/external/ct_benchmarks.csv            public CT chronic absenteeism benchmarks

Everything is synthetic. No real student data is used.
Run:  python scripts/generate_data.py
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
SEED = 42
AS_OF = date(2026, 9, 19)  # "today" inside the dataset
CHRONIC_CUTOFF = 0.90  # CT rule: missing 10%+ of days = chronically absent

ROOT = Path(__file__).resolve().parents[1]
CLEAN, RAW, EXT = (
    ROOT / "data" / "clean",
    ROOT / "data" / "raw",
    ROOT / "data" / "external",
)

rng = np.random.default_rng(SEED)
Faker.seed(SEED)
fake = Faker("en_US")


def pick(options, p=None):
    """Pick one item from a list (returns a normal Python object)."""
    return options[int(rng.choice(len(options), p=p))]


# ----------------------------------------------------------------------------
# Reference data: programs, courses, terms, cohorts
# ----------------------------------------------------------------------------
PROGRAMS = [
    # id, name, track, subject, length_weeks, grade_band, sessions_per_week
    ("P01", "Web Development", "High School", "Web Development", 40, "9-12", 2),
    ("P02", "Cybersecurity", "High School", "Cybersecurity", 40, "9-12", 2),
    ("P03", "Game Development", "High School", "Game Development", 40, "9-12", 2),
    ("P04", "AI Foundations", "High School", "Artificial Intelligence", 20, "9-12", 2),
    ("P05", "Quantum Intro", "High School", "Quantum Computing", 4, "11-12", 4),
    ("P06", "Career Readiness", "Adult", "Software Engineering", 26, "Adult", 4),
]
PROG = {
    p[0]: dict(
        zip(
            [
                "program_id",
                "program_name",
                "track",
                "subject",
                "length_weeks",
                "grade_band",
                "sessions_per_week",
            ],
            p,
        )
    )
    for p in PROGRAMS
}

MEETING_DAYS = {
    "P01": (1, 3),
    "P02": (1, 3),
    "P03": (1, 3),
    "P04": (1, 3),
    "P05": (0, 1, 2, 3),
    "P06": (0, 1, 2, 3),
}  # Mon=0

COURSES = {
    "P01": [
        ("Intro to Web Development", 120),
        ("Backend and Databases", 120),
        ("Web Capstone Product", 100),
    ],
    "P02": [
        ("Security Fundamentals", 120),
        ("Networks and Threats", 120),
        ("Security Capstone", 100),
    ],
    "P03": [
        ("Game Design Basics", 120),
        ("Game Programming", 120),
        ("Game Capstone", 100),
    ],
    "P04": [("Python for AI", 60), ("Machine Learning Basics", 60)],
    "P05": [("Quantum Concepts", 20), ("Qiskit Lab", 20)],
    "P06": [
        ("Programming Fundamentals", 180),
        ("Software Engineering Practices", 180),
        ("Portfolio and Career Prep", 100),
    ],
}

COHORT_SPECS = [
    # program, start (a Monday), location, funder (generic on purpose), seats
    ("P01", date(2023, 9, 11), "New Haven", "District Partnership", 24),
    ("P02", date(2023, 9, 11), "Stamford", "Corporate Foundation", 24),
    ("P06", date(2024, 1, 8), "Stamford", "State Workforce Grant", 20),
    ("P04", date(2024, 2, 5), "New Haven", "District Partnership", 20),
    ("P06", date(2024, 8, 12), "Stamford", "State Workforce Grant", 20),
    ("P01", date(2024, 9, 9), "New Haven", "District Partnership", 24),
    ("P03", date(2024, 9, 9), "Stamford", "Corporate Foundation", 24),
    ("P05", date(2025, 2, 3), "New Haven", "University Grant", 10),
    ("P05", date(2025, 6, 16), "New Haven", "University Grant", 10),
    ("P02", date(2025, 9, 8), "Stamford", "Corporate Foundation", 24),
    ("P01", date(2025, 9, 8), "New Haven", "District Partnership", 24),
    (
        "P06",
        date(2026, 4, 20),
        "Stamford",
        "State Workforce Grant",
        20,
    ),  # still running
]

TOWNS = {
    "New Haven": [
        ("New Haven", 0.38),
        ("Hamden", 0.14),
        ("West Haven", 0.10),
        ("Bridgeport", 0.08),
        ("Wallingford", 0.07),
        ("Milford", 0.07),
        ("Ansonia", 0.06),
        ("East Haven", 0.05),
        ("North Haven", 0.05),
    ],
    "Stamford": [
        ("Stamford", 0.52),
        ("Norwalk", 0.20),
        ("Bridgeport", 0.08),
        ("Greenwich", 0.08),
        ("Darien", 0.04),
        ("Fairfield", 0.08),
    ],
}
RACES = [
    "Hispanic/Latino",
    "Black or African American",
    "White",
    "Asian",
    "Two or More Races",
]
RACE_P = [0.32, 0.26, 0.26, 0.09, 0.07]
GENDERS = ["Female", "Male", "Non-binary"]
GENDER_P = [0.47, 0.50, 0.03]


def build_terms():
    rows, n = [], 1
    for y in (2023, 2024, 2025, 2026):  # school year starting in September of y
        sy = f"{y}-{str(y + 1)[2:]}"
        for name, s, e in [
            (f"Fall {y}", date(y, 9, 1), date(y, 12, 31)),
            (f"Spring {y + 1}", date(y + 1, 1, 1), date(y + 1, 6, 14)),
            (f"Summer {y + 1}", date(y + 1, 6, 15), date(y + 1, 8, 31)),
        ]:
            rows.append((f"T{n:02d}", name, s, e, sy))
            n += 1
    return pd.DataFrame(
        rows, columns=["term_id", "term_name", "start_date", "end_date", "school_year"]
    )


TERMS = build_terms()


def term_for(d):
    for r in TERMS.itertuples():
        if r.start_date <= d <= r.end_date:
            return r.term_id, r.term_name
    raise ValueError(f"No term for {d}")


def is_break(d):
    """Days with no sessions: winter break, Thanksgiving week, April break, July 4."""
    return (
        (d.month == 12 and d.day >= 22)
        or (d.month == 1 and d.day <= 1)
        or (d.month == 11 and 22 <= d.day <= 28)
        or (d.month == 4 and 13 <= d.day <= 17)
        or (d.month == 7 and d.day == 4)
    )


# ----------------------------------------------------------------------------
# Clean data simulation
# ----------------------------------------------------------------------------
def make_student(sid, prog, location):
    adult = prog["track"] == "Adult"
    if adult:
        entry_grade = "Adult"
    elif prog["program_id"] == "P05":
        entry_grade = str(pick([11, 12]))
    else:
        entry_grade = str(pick([9, 10, 11, 12], [0.25, 0.27, 0.25, 0.23]))

    gender = pick(GENDERS, GENDER_P)
    first = (
        fake.first_name_female()
        if gender == "Female"
        else fake.first_name_male() if gender == "Male" else fake.first_name()
    )
    town, w = zip(*TOWNS[location])
    home_town = pick(list(town), list(w))
    return {
        "student_id": sid,
        "first_name": first,
        "last_name": fake.last_name(),
        "gender": gender,
        "entry_grade": entry_grade,
        "race_ethnicity": pick(RACES, RACE_P),
        "home_town": home_town,
        "school_district": "N/A" if adult else f"{home_town} Public Schools",
        "econ_disadvantaged_flag": (
            "Y" if rng.random() < (0.60 if adult else 0.55) else "N"
        ),
    }


def dob_for(student, cohort_start):
    if student["entry_grade"] == "Adult":
        age = float(rng.triangular(19, 26, 55))
    else:
        age = int(student["entry_grade"]) + 5 + float(rng.random())
    return cohort_start - timedelta(days=int(age * 365.25))


def simulate():
    programs = pd.DataFrame(
        PROGRAMS,
        columns=[
            "program_id",
            "program_name",
            "track",
            "subject",
            "length_weeks",
            "grade_band",
            "sessions_per_week",
        ],
    )
    courses_rows = []
    for pid, lst in COURSES.items():
        for name, hours in lst:
            courses_rows.append((f"CRS{len(courses_rows) + 1:02d}", pid, name, hours))
    courses = pd.DataFrame(
        courses_rows,
        columns=["course_id", "program_id", "course_name", "contact_hours"],
    )
    course_by_prog = {pid: g for pid, g in courses.groupby("program_id")}

    # cohorts
    cohorts = []
    for i, (pid, start, loc, funder, seats) in enumerate(
        sorted(COHORT_SPECS, key=lambda x: x[1]), 1
    ):
        p = PROG[pid]
        end = (
            start + timedelta(weeks=p["length_weeks"]) - timedelta(days=3)
        )  # ends on a Friday
        cohorts.append(
            {
                "cohort_id": f"C{i:02d}",
                "program_id": pid,
                "cohort_name": f"{p['program_name']} - {term_for(start)[1]}",
                "start_date": start,
                "end_date": end,
                "location": loc,
                "funder": funder,
                "planned_seats": seats,
            }
        )
    cohorts_df = pd.DataFrame(cohorts)

    students, enrollments, attendance, grades, surveys = [], [], [], [], []
    hs_pool = []  # earlier high-school students who might come back
    next_sid, eid, aid, gid, rid = 100001, 1, 1, 1, 1

    for c in cohorts:
        prog = PROG[c["program_id"]]
        adult = prog["track"] == "Adult"
        n = int(round(c["planned_seats"] * rng.uniform(0.88, 1.0)))
        total_days = (c["end_date"] - c["start_date"]).days

        # session calendar
        sessions, d = [], c["start_date"]
        while d <= c["end_date"] and d <= AS_OF:
            if d.weekday() in MEETING_DAYS[c["program_id"]] and not is_break(d):
                sessions.append(d)
            d += timedelta(days=1)

        used = set()
        for _ in range(n):
            # some high-school students return for a second program
            eligible = [
                s
                for s in hs_pool
                if s["student_id"] not in used
                and s["entry_grade"] in ("9", "10")
                and s["_last_end"] < c["start_date"]
                and (c["start_date"] - s["_last_end"]).days < 400
            ]
            if (
                not adult
                and c["program_id"] != "P05"
                and eligible
                and rng.random() < 0.10
            ):
                stu = eligible[int(rng.integers(len(eligible)))]
            else:
                stu = make_student(next_sid, prog, c["location"])
                stu["date_of_birth"] = dob_for(stu, c["start_date"])
                next_sid += 1
                students.append(stu)
                if not adult:
                    hs_pool.append(stu)
            used.add(stu["student_id"])
            stu["_last_end"] = c["end_date"]

            # --- engagement: struggling vs regular, shaped by a few factors
            p_struggle = 0.07 if adult else 0.09
            if stu["entry_grade"] in ("11", "12"):
                p_struggle += 0.04
            if stu["econ_disadvantaged_flag"] == "Y":
                p_struggle += 0.04
            p_struggle += {2023: 0.08, 2024: 0.04, 2025: 0.00, 2026: -0.03}[
                c["start_date"].year
            ]
            struggling = rng.random() < p_struggle
            prop = rng.normal(0.78, 0.08) if struggling else rng.normal(0.96, 0.025)
            prop = float(np.clip(prop, 0.40, 0.995))

            # --- withdrawal
            factor = float(np.clip(prog["length_weeks"] / 40, 0.25, 1.0))
            withdrawn = rng.random() < (0.45 if struggling else 0.09) * factor
            wd, reason = None, None
            if withdrawn:
                elapsed = min(
                    1.0, (min(AS_OF, c["end_date"]) - c["start_date"]).days / total_days
                )
                frac = rng.uniform(0.15, max(0.16, min(0.85, elapsed)))
                wd = c["start_date"] + timedelta(days=int(total_days * frac))
                wd = min(wd, AS_OF)
                reasons = (
                    [
                        "Found employment",
                        "Work or family obligations",
                        "Schedule conflict",
                        "Lost interest",
                    ]
                    if adult
                    else [
                        "Schedule conflict",
                        "Transportation",
                        "Lost interest",
                        "Academic difficulty",
                        "Moved / left area",
                    ]
                )
                reason = pick(reasons)
            status = (
                "Withdrawn"
                if withdrawn
                else ("Completed" if c["end_date"] <= AS_OF else "Active")
            )
            enr_id = f"E{eid:04d}"
            eid += 1
            enrollments.append(
                {
                    "enrollment_id": enr_id,
                    "student_id": stu["student_id"],
                    "cohort_id": c["cohort_id"],
                    "enroll_date": c["start_date"]
                    - timedelta(days=int(rng.integers(3, 22))),
                    "status": status,
                    "withdraw_date": wd,
                    "withdraw_reason": reason,
                }
            )

            # --- attendance
            my_sessions = [s for s in sessions if wd is None or s <= wd]
            for s in my_sessions:
                p = prop
                if wd is not None:
                    left = (wd - s).days
                    if left < 28:  # fading out before leaving
                        p *= 0.60 + 0.40 * (left / 28)
                if rng.random() < p:
                    st = (
                        "Tardy"
                        if rng.random() < (0.12 if struggling else 0.05)
                        else "Present"
                    )
                else:
                    st = "Excused" if rng.random() < 0.40 else "Absent"
                attendance.append(
                    {
                        "attendance_id": f"A{aid:06d}",
                        "enrollment_id": enr_id,
                        "session_date": s,
                        "status": st,
                    }
                )
                aid += 1

            # --- grades (one row per course; courses split the program timeline)
            crs = course_by_prog[c["program_id"]]
            ability = rng.normal(0, 7)
            for k, crow in enumerate(crs.itertuples()):
                slice_end = c["start_date"] + timedelta(
                    days=int(total_days * (k + 1) / len(crs))
                )
                if wd is not None and slice_end > wd:
                    score, letter = None, "W"
                elif slice_end > AS_OF:
                    continue  # course still in progress
                else:
                    score = float(
                        np.clip(
                            76 + ability + 55 * (prop - 0.90) + rng.normal(0, 3.5),
                            35,
                            100,
                        )
                    )
                    score = round(score, 1)
                    letter = (
                        "A"
                        if score >= 90
                        else (
                            "B"
                            if score >= 80
                            else "C" if score >= 70 else "D" if score >= 60 else "F"
                        )
                    )
                grades.append(
                    {
                        "grade_id": f"G{gid:05d}",
                        "enrollment_id": enr_id,
                        "course_id": crow.course_id,
                        "term_id": term_for(slice_end)[0],
                        "score": score,
                        "letter_grade": letter,
                    }
                )
                gid += 1

            # --- surveys
            def add_survey(sdate, stype):
                nonlocal rid
                m_sat, m_bel = (3.0, 2.9) if struggling else (4.3, 4.2)
                if stype == "Withdrawal":
                    m_sat, m_bel = m_sat - 0.5, m_bel - 0.4
                sat = int(np.clip(round(rng.normal(m_sat, 0.7)), 1, 5))
                bel = int(np.clip(round(rng.normal(m_bel, 0.7)), 1, 5))
                surveys.append(
                    {
                        "response_id": f"R{rid:05d}",
                        "enrollment_id": enr_id,
                        "survey_date": sdate,
                        "survey_type": stype,
                        "satisfaction": sat,
                        "belonging": bel,
                        "comment": make_comment(struggling),
                    }
                )
                rid += 1

            mid = c["start_date"] + timedelta(days=total_days // 2)
            if mid <= AS_OF and (wd is None or wd > mid) and rng.random() < 0.75:
                add_survey(mid, "Mid-Program")
            if status == "Completed" and rng.random() < 0.65:
                add_survey(
                    min(AS_OF, c["end_date"] + timedelta(days=int(rng.integers(0, 6)))),
                    "End-of-Program",
                )
            if withdrawn and rng.random() < 0.30:
                add_survey(min(AS_OF, wd + timedelta(days=2)), "Withdrawal")

    students_df = pd.DataFrame(students)[
        [
            "student_id",
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "entry_grade",
            "race_ethnicity",
            "home_town",
            "school_district",
            "econ_disadvantaged_flag",
        ]
    ]
    return {
        "programs": programs,
        "cohorts": cohorts_df,
        "terms": TERMS.copy(),
        "courses": courses,
        "students": students_df,
        "enrollments": pd.DataFrame(enrollments),
        "attendance": pd.DataFrame(attendance),
        "grades": pd.DataFrame(grades),
        "survey_responses": pd.DataFrame(surveys),
    }


POSITIVE = [
    "I liked building real projects instead of just sitting through lectures.",
    "My mentor was patient and explained things until I got it.",
    "It felt like a community. Everyone helped each other out.",
    "The portfolio and career prep sessions were really useful.",
]
NEGATIVE = [
    "The schedule clashed with school and other commitments, so it was hard to keep up.",
    "Getting to the studio was hard. The bus takes forever.",
    "Some weeks moved too fast and I felt lost.",
    "I work part-time and have family duties, so I missed sessions.",
    "I was not always sure what was expected for project deadlines.",
    "I wanted more laptop time, and the wifi was slow.",
]


def make_comment(struggling):
    if rng.random() < 0.25:
        return None  # many people skip the comment box
    p_neg = 0.70 if struggling else 0.20
    parts = []
    for _ in range(int(rng.integers(1, 3))):
        pool = NEGATIVE if rng.random() < p_neg else POSITIVE
        line = pool[int(rng.integers(len(pool)))]
        if line not in parts:
            parts.append(line)
    return " ".join(parts)


def ct_benchmarks():
    """Public CT statewide chronic absenteeism (CSDE / EdSight, K-12)."""
    rows = [("2021-22", 23.7), ("2022-23", 20.0), ("2023-24", 17.7), ("2024-25", 17.2)]
    return pd.DataFrame(
        [
            {
                "school_year": y,
                "metric": "chronic_absenteeism_rate_pct",
                "geography": "Connecticut (statewide, K-12)",
                "value": v,
                "definition": "Share of students missing 10% or more of days enrolled",
                "source": "CT State Dept of Education / EdSight",
            }
            for y, v in rows
        ]
    )


# ----------------------------------------------------------------------------
# Messy copy (for the Excel cleaning phase)
# ----------------------------------------------------------------------------
def corrupt(df, col, prob, fn, log, table, issue):
    """Apply fn to a random share of the non-empty values in df[col]."""
    df[col] = df[col].astype(object)
    ok = df.index[df[col].notna()]
    idx = ok[rng.random(len(ok)) < prob]
    df.loc[idx, col] = [fn(df.at[i, col]) for i in idx]
    log.append((table, col, issue, len(idx)))


def blank_some(
    df, col, n=None, prob=None, log=None, table="", issue="missing value", only=None
):
    df[col] = df[col].astype(object)
    pool = df.index if only is None else df.index[only]
    if n is not None:
        idx = rng.choice(pool, size=min(n, len(pool)), replace=False)
    else:
        idx = pool[rng.random(len(pool)) < prob]
    df.loc[idx, col] = np.nan
    log.append((table, col, issue, len(idx)))


def mix_dates(df, col, log, table, probs=(0.70, 0.22, 0.08)):
    """Turn real dates into a mix of ISO, US and DD-Mon-YYYY strings."""
    n_bad = 0

    def f(v):
        nonlocal n_bad
        if v is None or (not isinstance(v, date) and pd.isna(v)):
            return ""
        r = rng.random()
        if r < probs[0]:
            return v.isoformat()
        n_bad += 1
        return (
            v.strftime("%m/%d/%Y")
            if r < probs[0] + probs[1]
            else v.strftime("%d-%b-%Y")
        )

    df[col] = [f(v) for v in df[col]]
    log.append((table, col, "mixed date formats", n_bad))


def add_dupes(df, frac, log, table, tweak=None):
    dup = df.sample(frac=frac, random_state=SEED).copy()
    if tweak:
        dup = tweak(dup)
    log.append((table, "(row)", "duplicate rows", len(dup)))
    return pd.concat([df, dup], ignore_index=True)


def make_messy(t):
    log = []
    m = {k: v.copy() for k, v in t.items()}

    # ---- students
    s = m["students"]
    gv = {
        "Female": ["Female", "female", "F", "f", "FEMALE"],
        "Male": ["Male", "male", "M", "m"],
        "Non-binary": ["Non-binary", "Nonbinary", "NB"],
    }
    corrupt(
        s,
        "gender",
        0.35,
        lambda v: pick(gv[v]),
        log,
        "students",
        "inconsistent gender labels",
    )

    def case_mess(v):
        r = rng.random()
        return v.lower() if r < 0.4 else v.upper() if r < 0.7 else f" {v} "

    corrupt(
        s,
        "first_name",
        0.05,
        case_mess,
        log,
        "students",
        "inconsistent casing / spaces in name",
    )
    corrupt(
        s,
        "last_name",
        0.05,
        case_mess,
        log,
        "students",
        "inconsistent casing / spaces in name",
    )
    corrupt(
        s,
        "entry_grade",
        0.25,
        lambda v: v if v == "Adult" else pick([f"{v}th", f"Grade {v}", f"grade {v}"]),
        log,
        "students",
        "grade written in different ways",
    )

    def town_mess(v):
        r = rng.random()
        return (
            v.lower()
            if r < 0.3
            else v.upper() if r < 0.55 else v + " " if r < 0.75 else v + ", CT"
        )

    corrupt(s, "home_town", 0.12, town_mess, log, "students", "inconsistent town names")
    blank_some(
        s, "race_ethnicity", prob=0.05, log=log, table="students", issue="missing value"
    )
    blank_some(
        s, "date_of_birth", prob=0.01, log=log, table="students", issue="missing value"
    )
    bad = rng.choice(s.index[s["date_of_birth"].notna()], size=2, replace=False)
    s.at[bad[0], "date_of_birth"] = date(1900, 1, 1)
    s.at[bad[1], "date_of_birth"] = date(2031, 2, 14)
    log.append(("students", "date_of_birth", "impossible dates (1900, 2031)", 2))
    mix_dates(s, "date_of_birth", log, "students")

    def s_tweak(d):
        d["first_name"] = d["first_name"].map(lambda v: " " + str(v).strip().lower())
        return d

    m["students"] = add_dupes(s, 0.03, log, "students", s_tweak)

    # ---- enrollments
    e = m["enrollments"]
    wd_rows = e.index[e["status"] == "Withdrawn"]
    blank_some(
        e,
        "withdraw_date",
        n=4,
        log=log,
        table="enrollments",
        issue="withdrawn but no withdraw date",
        only=e["status"] == "Withdrawn",
    )
    still = [i for i in wd_rows if pd.notna(e.at[i, "withdraw_date"])]
    for i in rng.choice(still, size=3, replace=False):
        e.at[i, "withdraw_date"] = e.at[i, "enroll_date"] - timedelta(days=5)
    log.append(("enrollments", "withdraw_date", "withdraw date before enroll date", 3))
    blank_some(
        e,
        "withdraw_reason",
        n=2,
        log=log,
        table="enrollments",
        issue="missing value",
        only=e["status"] == "Withdrawn",
    )
    sv = {
        "Completed": ["Completed", "completed", "Complete", "COMPLETED"],
        "Withdrawn": ["Withdrawn", "withdrawn", "W", "Dropped"],
        "Active": ["Active", "active", "ACTIVE"],
    }
    corrupt(
        e,
        "status",
        0.30,
        lambda v: pick(sv[v]),
        log,
        "enrollments",
        "inconsistent status labels",
    )
    orph = e.sample(2, random_state=SEED).copy()
    orph["student_id"] = [999901, 999902]
    orph["enrollment_id"] = ["E9001", "E9002"]
    e = pd.concat([e, orph], ignore_index=True)
    log.append(
        ("enrollments", "student_id", "orphan rows (student not in students)", 2)
    )
    mix_dates(e, "enroll_date", log, "enrollments")
    mix_dates(e, "withdraw_date", log, "enrollments")
    m["enrollments"] = add_dupes(e, 0.02, log, "enrollments")

    # ---- attendance
    a = m["attendance"]
    a["session_date"] = a["session_date"].astype(object)
    for i in rng.choice(a.index, size=25, replace=False):
        d = a.at[i, "session_date"]
        a.at[i, "session_date"] = d + timedelta(days=5 - d.weekday())  # a Saturday
    log.append(("attendance", "session_date", "sessions on a weekend", 25))
    for i in rng.choice(a.index, size=10, replace=False):
        a.at[i, "session_date"] = AS_OF + timedelta(days=200)
    log.append(("attendance", "session_date", "dates in the future", 10))
    av = {
        "Present": ["Present", "present", "P", "PRESENT"],
        "Absent": ["Absent", "absent", "A", "Abs"],
        "Excused": ["Excused", "excused", "E", "Exc."],
        "Tardy": ["Tardy", "tardy", "T", "Late"],
    }
    corrupt(
        a,
        "status",
        0.15,
        lambda v: pick(av[v]),
        log,
        "attendance",
        "inconsistent status labels",
    )
    blank_some(
        a, "status", prob=0.005, log=log, table="attendance", issue="missing value"
    )
    mix_dates(a, "session_date", log, "attendance", probs=(0.85, 0.15, 0.0))
    m["attendance"] = add_dupes(a, 0.01, log, "attendance")

    # ---- grades
    g = m["grades"]
    g["score"] = g["score"].astype(object)
    low = g.index[
        (g["letter_grade"] != "W") & (pd.to_numeric(g["score"], errors="coerce") < 65)
    ]
    for i in low[:6]:
        g.at[i, "letter_grade"] = "A"
    log.append(
        ("grades", "letter_grade", "letter does not match score", min(6, len(low)))
    )
    real = g.index[g["letter_grade"] != "W"]
    blank_some(
        g,
        "score",
        n=8,
        log=log,
        table="grades",
        issue="missing score (not a withdrawal)",
        only=g["letter_grade"] != "W",
    )
    for i in rng.choice(
        [j for j in real if pd.notna(g.at[j, "score"])], size=6, replace=False
    ):
        g.at[i, "score"] = pick([105, 110, 120, 850, 950, 1000])
    log.append(("grades", "score", "score above 100", 6))
    for i in rng.choice(
        [j for j in real if pd.notna(g.at[j, "score"])], size=2, replace=False
    ):
        g.at[i, "score"] = -1
    log.append(("grades", "score", "negative score", 2))
    corrupt(
        g,
        "score",
        0.015,
        lambda v: f"{int(round(float(v)))}%",
        log,
        "grades",
        "score stored as text with % sign",
    )
    corrupt(
        g,
        "letter_grade",
        0.05,
        lambda v: v.lower(),
        log,
        "grades",
        "lowercase letter grade",
    )
    m["grades"] = add_dupes(g, 0.003, log, "grades")

    # ---- survey responses
    r = m["survey_responses"]
    for col in ("satisfaction", "belonging"):
        r[col] = r[col].astype(object)
        for i in rng.choice(r.index, size=4, replace=False):
            r.at[i, col] = pick([0, 6, 55])
        log.append(("survey_responses", col, "rating outside 1-5", 4))
        for i in rng.choice(r.index, size=3, replace=False):
            r.at[i, col] = "N/A"
        log.append(("survey_responses", col, "text instead of number (N/A)", 3))
    corrupt(
        r,
        "comment",
        0.06,
        lambda v: f"  {v}  ",
        log,
        "survey_responses",
        "extra spaces in comment",
    )
    corrupt(
        r,
        "comment",
        0.03,
        lambda v: v.upper(),
        log,
        "survey_responses",
        "ALL CAPS comment",
    )
    for i in rng.choice(r.index[r["comment"].notna()], size=4, replace=False):
        r.at[i, "comment"] = pick(["test", "n/a", ".", "asdf"])
    log.append(("survey_responses", "comment", "junk / test comments", 4))
    mix_dates(r, "survey_date", log, "survey_responses")
    m["survey_responses"] = add_dupes(r, 0.01, log, "survey_responses")

    # ---- cohorts
    c = m["cohorts"]
    lv = {
        "New Haven": ["NH", "new haven", "New Haven ", "NEW HAVEN"],
        "Stamford": ["Stamford ", "STAMFORD", "stamford", "Stamford, CT"],
    }
    corrupt(
        c,
        "location",
        0.4,
        lambda v: pick(lv[v]),
        log,
        "cohorts",
        "inconsistent location names",
    )
    c["planned_seats"] = c["planned_seats"].astype(object)
    c.at[int(rng.integers(len(c))), "planned_seats"] = "24 seats"
    log.append(("cohorts", "planned_seats", "number stored as text", 1))
    blank_some(c, "funder", n=1, log=log, table="cohorts", issue="missing value")
    mix_dates(c, "start_date", log, "cohorts")
    mix_dates(c, "end_date", log, "cohorts")

    # shuffle so duplicates are not sitting at the bottom
    for k in ("students", "enrollments", "attendance", "grades", "survey_responses"):
        m[k] = m[k].sample(frac=1, random_state=SEED).reset_index(drop=True)
    return m, log


# ----------------------------------------------------------------------------
# Quick sanity check printed after generation
# ----------------------------------------------------------------------------
def summarize(t):
    e, a, g, c = t["enrollments"], t["attendance"], t["grades"], t["cohorts"]
    per = a.groupby("enrollment_id")["status"].agg(
        sessions="size", attended=lambda s: s.isin(["Present", "Tardy"]).sum()
    )
    per["rate"] = per["attended"] / per["sessions"]
    per["chronic"] = per["rate"] < CHRONIC_CUTOFF
    x = e.merge(per, left_on="enrollment_id", right_index=True).merge(
        c[["cohort_id", "program_id", "start_date"]], on="cohort_id"
    )
    x["year"] = x["start_date"].map(lambda d: d.year)
    x["track"] = x["program_id"].map(lambda p: PROG[p]["track"])
    scores = (
        g[g["score"].notna()]
        .groupby("enrollment_id")["score"]
        .mean()
        .rename("avg_score")
    )
    x = x.merge(scores, left_on="enrollment_id", right_index=True, how="left")

    print("\n=== Row counts (clean) ===")
    for k, v in t.items():
        print(f"  {k:18s} {len(v):>6,}")
    print(
        f"\nUnique students: {t['students']['student_id'].nunique()}  |  enrollments: {len(e)}"
    )
    print(
        f"\nChronic absence (missed 10%+, incl. excused): {x['chronic'].mean():.1%} overall"
    )
    print(
        "  by start year:",
        {int(k): f"{v:.1%}" for k, v in x.groupby("year")["chronic"].mean().items()},
    )
    print(
        "  by track     :",
        {k: f"{v:.1%}" for k, v in x.groupby("track")["chronic"].mean().items()},
    )
    print("\nStatus mix:", e["status"].value_counts().to_dict())
    w = x.groupby("cohort_id")["status"].apply(lambda s: (s == "Withdrawn").mean())
    print("Withdrawal rate by cohort:", {k: f"{v:.0%}" for k, v in w.items()})
    print(
        f"Correlation attendance rate vs avg score: {x[['rate', 'avg_score']].corr().iloc[0, 1]:.2f}"
    )


def main():
    for p in (CLEAN, RAW, EXT):
        p.mkdir(parents=True, exist_ok=True)
    clean = simulate()
    for name, df in clean.items():
        df.to_csv(CLEAN / f"{name}.csv", index=False)
    ct_benchmarks().to_csv(EXT / "ct_benchmarks.csv", index=False)

    messy, log = make_messy(clean)
    for name, df in messy.items():
        df.to_csv(RAW / f"{name}.csv", index=False)
    pd.DataFrame(log, columns=["table", "column", "issue", "rows_affected"]).to_csv(
        RAW / "_answer_key_injected_issues.csv", index=False
    )

    summarize(clean)
    print(
        f"\nDone. Wrote clean -> {CLEAN}\n       raw   -> {RAW}\n       ext   -> {EXT}"
    )


if __name__ == "__main__":
    main()

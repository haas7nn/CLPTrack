"""Reads a csv file of people and creates their accounts. Used by the Add people page.

The file needs a first line with the column names. Two columns are required, username and role.
The others are optional: first_name, last_name, email, student_id, section, supervisor.
The supervisor column holds the username of the student's supervisor.

The rule is all or nothing. If any line has a problem, no account is created and every problem
is listed, so the coordinator fixes the file once and uploads it again.
"""
import csv
import io

from django.db import transaction

from .models import User

REQUIRED = ("username", "role")
OPTIONAL = ("first_name", "last_name", "email", "student_id", "section", "supervisor")
ROLES = {choice for choice, _ in User.Role.choices}
MAX_ROWS = 500

EXAMPLE = (
    "username,first_name,last_name,email,role,student_id,section,supervisor\n"
    "dr.salem,Huda,Salem,huda.salem@example.com,supervisor,,,\n"
    "202300101,Khalid,Jasim,202300101@example.com,student,202300101,8,dr.salem\n"
    "202300102,Fatima,Radhi,202300102@example.com,student,202300102,8,dr.salem\n"
)


def read_rows(uploaded):
    """Turns the uploaded file into a list of rows, or returns a list of problems with the file itself."""
    try:
        text = uploaded.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["The file could not be read. Save it as CSV (comma separated) and try again."]
    reader = csv.DictReader(io.StringIO(text))
    columns = [c.strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in columns]
    if missing:
        return [], [f"The first line must name the columns. Missing: {', '.join(missing)}."]
    rows = []
    for line, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if any(row.values()):
            rows.append((line, row))
    if not rows:
        return [], ["The file has no people in it."]
    if len(rows) > MAX_ROWS:
        return [], [f"The file has more than {MAX_ROWS} people. Split it into smaller files."]
    return rows, []


def check_rows(rows):
    """Finds every problem before anything is created. Returns the new rows, the skipped names and the problems."""
    existing = set(User.objects.values_list("username", flat=True))
    supervisors = set(User.objects.filter(role=User.Role.SUPERVISOR).values_list("username", flat=True))
    supervisors |= {row["username"] for _, row in rows if row.get("role", "").lower() == "supervisor"}
    seen, new, skipped, problems = set(), [], [], []
    for line, row in rows:
        username, role = row.get("username", ""), row.get("role", "").lower()
        if not username:
            problems.append(f"Line {line}: the username is empty.")
            continue
        if username in seen:
            problems.append(f"Line {line}: {username} appears twice in the file.")
            continue
        seen.add(username)
        if role not in ROLES:
            problems.append(f"Line {line}: the role of {username} must be student, supervisor or coordinator.")
            continue
        supervisor = row.get("supervisor", "")
        if supervisor and role != "student":
            problems.append(f"Line {line}: only a student can have a supervisor.")
        elif supervisor and supervisor not in supervisors:
            problems.append(f"Line {line}: the supervisor {supervisor} is not an account and is not in the file.")
        elif username in existing:
            skipped.append(username)
        else:
            new.append(dict(row, role=role))
    return new, skipped, problems


def create_accounts(new, first_password):
    """Creates the accounts, supervisors and coordinators first so students can point at them."""
    counts = {"student": 0, "supervisor": 0, "coordinator": 0}
    with transaction.atomic():
        for row in sorted(new, key=lambda r: r["role"] == "student"):
            user = User(username=row["username"], role=row["role"], first_name=row.get("first_name", ""),
                        last_name=row.get("last_name", ""), email=row.get("email", ""),
                        student_id=row.get("student_id", ""), section=row.get("section", ""),
                        must_change_password=True)
            if row["role"] == "coordinator":
                user.is_staff = user.is_superuser = True   # so the Admin link works for them
            if row.get("supervisor"):
                user.supervisor = User.objects.get(username=row["supervisor"])
            user.set_password(first_password)
            user.save()
            counts[row["role"]] += 1
    return counts

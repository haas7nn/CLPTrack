"""Reads a csv file of people and creates their accounts. Used by the Add people page.

The file needs a first line with the column names. Two columns are required, username and role.
The others are optional: first_name, last_name, email, student_id, section, supervisor.
The supervisor column holds the username of the student's supervisor.

The rule is all or nothing. If any line has a problem, no account is created and every problem
is listed, so the coordinator fixes the file once and uploads it again.

Every new account gets its own random first password. A shared one would let anybody who knows
a classmate's username sign in as them before they do. Coordinators are not created from a file,
because a coordinator can do everything, so that stays a deliberate step in the admin site.
"""
import csv
import io
import secrets

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import User

REQUIRED = ("username", "role")
OPTIONAL = ("first_name", "last_name", "email", "student_id", "section", "supervisor")
ROLES = (User.Role.STUDENT, User.Role.SUPERVISOR)
MAX_ROWS = 500
# letters and digits that are hard to mix up when read from a sheet of paper (no 0, O, 1, l, I)
PASSWORD_LETTERS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"

EXAMPLE = (
    "username,first_name,last_name,email,role,student_id,section,supervisor\n"
    "dr.salem,Huda,Salem,huda.salem@example.com,supervisor,,,\n"
    "202300101,Khalid,Jasim,202300101@example.com,student,202300101,8,dr.salem\n"
    "202300102,Fatima,Radhi,202300102@example.com,student,202300102,8,dr.salem\n"
)


def new_password():
    return "".join(secrets.choice(PASSWORD_LETTERS) for _ in range(10))


def read_rows(uploaded):
    """Turns the uploaded file into a list of rows, or returns a list of problems with the file itself."""
    try:
        text = uploaded.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["The file could not be read. Save it as CSV (comma separated) and try again."]
    reader = csv.DictReader(io.StringIO(text), restkey="_extra")
    columns = [c.strip().lower() for c in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED if c not in columns]
    if missing:
        return [], [f"The first line must name the columns. Missing: {', '.join(missing)}."]
    rows, problems = [], []
    try:
        for line, raw in enumerate(reader, start=2):
            if raw.get("_extra"):
                problems.append(f"Line {line} has more values than the first line. Check for an extra comma.")
                continue
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            if any(row.values()):
                rows.append((line, row))
    except csv.Error:
        return [], ["The file is not a valid CSV file. Open it in a spreadsheet, save it as CSV and try again."]
    if problems:
        return [], problems
    if not rows:
        return [], ["The file has no people in it."]
    if len(rows) > MAX_ROWS:
        return [], [f"The file has more than {MAX_ROWS} people. Split it into smaller files."]
    return rows, []


def build_user(row, role):
    return User(username=row["username"], role=role, first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""), email=row.get("email", ""),
                student_id=row.get("student_id", ""), section=row.get("section", ""),
                must_change_password=True,
                # a student added during the semester is not blamed for deadlines that passed before
                tracked_from=timezone.localdate() if role == User.Role.STUDENT else None)


def check_rows(rows):
    """Finds every problem before anything is created. Returns the new rows, the skipped names and the problems."""
    existing = {name.lower(): name for name in User.objects.values_list("username", flat=True)}
    supervisors = {name.lower() for name in User.objects.filter(role=User.Role.SUPERVISOR).values_list("username", flat=True)}
    supervisors |= {row["username"].lower() for _, row in rows
                    if row.get("role", "").lower() == "supervisor" and row.get("username", "").lower() not in existing}
    seen, new, skipped, problems = set(), [], [], []
    for line, row in rows:
        username, role = row.get("username", ""), row.get("role", "").lower()
        if not username:
            problems.append(f"Line {line}: the username is empty.")
            continue
        if username.lower() in seen:
            problems.append(f"Line {line}: {username} appears twice in the file.")
            continue
        seen.add(username.lower())
        if role == "coordinator":
            problems.append(f"Line {line}: a coordinator cannot be added from a file. Add {username} in Admin.")
            continue
        if role not in ROLES:
            problems.append(f"Line {line}: the role of {username} must be student or supervisor.")
            continue
        supervisor = row.get("supervisor", "")
        if supervisor and role != "student":
            problems.append(f"Line {line}: only a student can have a supervisor.")
            continue
        if supervisor and supervisor.lower() not in supervisors:
            problems.append(f"Line {line}: the supervisor {supervisor} is not a supervisor account and is not in the file.")
            continue
        if username.lower() in existing:
            skipped.append(existing[username.lower()])
            continue
        try:
            # the same checks Django makes on any account: allowed characters, lengths, a real email address
            build_user(row, role).full_clean(exclude=["password", "supervisor"], validate_unique=False)
        except ValidationError as error:
            for field, messages in error.message_dict.items():
                problems.append(f"Line {line}: {field} of {username}: {messages[0]}")
            continue
        new.append(dict(row, role=role))
    return new, skipped, problems


def create_accounts(new):
    """Creates the accounts, supervisors first so students can point at them.

    Returns one line per new account with its first password, which is shown to the coordinator once.
    """
    created = []
    with transaction.atomic():
        for row in sorted(new, key=lambda r: r["role"] == "student"):
            user = build_user(row, row["role"])
            if row.get("supervisor"):
                user.supervisor = User.objects.get(username__iexact=row["supervisor"], role=User.Role.SUPERVISOR)
            password = new_password()
            user.set_password(password)
            user.save()
            created.append({"username": user.username, "name": user.get_full_name(), "role": user.get_role_display(),
                            "password": password})
    return created

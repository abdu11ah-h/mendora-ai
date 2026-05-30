"""Staff role email whitelist."""

STAFF_ROLE_EMAILS = frozenset({
    "tubaaftab76@gmail.com",
    "muhammadabduah26@gmail.com",
})

ROLE_ELIGIBILITY_MESSAGE = "You are not eligible for this role. Please sign in as user."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_staff_email_allowed(email: str) -> bool:
    return normalize_email(email) in STAFF_ROLE_EMAILS


def assert_staff_role_allowed(email: str, role: str) -> None:
    from fastapi import HTTPException

    if role in ("counselor", "admin") and not is_staff_email_allowed(email):
        raise HTTPException(status_code=400, detail=ROLE_ELIGIBILITY_MESSAGE)

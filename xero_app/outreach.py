"""Xero reminder cadence.

Xero actually sends these reminders; the app only *reflects* them. This module
defines the cadence so we can (a) seed demo reminder history that follows it and
(b) classify how far along an overdue invoice is, for the dashboard call-prompt
KPIs. Nothing here sends anything.
"""

# (label, days offset from due date, prompts a phone call)
OUTREACH_STAGES = [
    ("Due in 7 days", -7, False),
    ("Due date reminder", 0, False),
    ("7 days after due date", 7, False),
    ("14 days after due date", 14, True),
    ("21 days after due date", 21, True),
    ("Final demand (60 days)", 60, False),
    ("Action / handover process (65 days)", 65, False),
]

# Days-past-due window where the cadence sits at the 14/21-day reminders and the
# administrator should phone the client (from the 14-day reminder up to final demand).
CALL_MIN, CALL_MAX = 14, 60


def current_stage(days_past_due):
    """Latest reached cadence stage for an invoice -> (label, needs_call)."""
    label, needs_call = "Not yet due", False
    if days_past_due is None:
        return label, needs_call
    for lbl, offset, is_call in OUTREACH_STAGES:
        if days_past_due >= offset:
            label, needs_call = lbl, is_call
    return label, needs_call


def needs_call(days_past_due):
    return days_past_due is not None and CALL_MIN <= days_past_due < CALL_MAX


def is_final_demand(days_past_due):
    return days_past_due is not None and 60 <= days_past_due < 65


def is_handover(days_past_due):
    return days_past_due is not None and days_past_due >= 65


# An invoice's call is "missed" once it has reached the 21-day reminder (a week
# past the first call point) while still in the call window, with no call ever
# logged for it.
MISSED_MIN = 21


def missed_call(days_past_due, ever_called):
    return (not ever_called) and days_past_due is not None and MISSED_MIN <= days_past_due < CALL_MAX


STAGE_LABELS = {
    "call": "Calls required (14/21 days)",
    "missed": "Missed calls",
    "final": "Final demand (60 days)",
    "handover": "Handover (65+ days)",
}


def in_stage(days_past_due, stage):
    """Whether an invoice's days-past-due falls in a dashboard scorecard stage.
    (The 'missed' stage also needs call history, so it's handled by the caller.)"""
    if days_past_due is None:
        return False
    if stage == "call":
        return CALL_MIN <= days_past_due < CALL_MAX
    if stage == "final":
        return 60 <= days_past_due < 65
    if stage == "handover":
        return days_past_due >= 65
    return True

"""SFW public subscription catalogue and display helpers.

Prices are display metadata; the Supabase plan table is authoritative for
billing. Never calculate or activate a paid entitlement from client-side data.
"""

PLANS = (
    {
        "code": "free",
        "name": "Free",
        "amount_kes": 0,
        "billing_interval": "none",
        "description": "Open access to the core SFW research workspace.",
    },
    {
        "code": "student",
        "name": "Student",
        "amount_kes": 299,
        "billing_interval": "month",
        "description": "Affordable monthly access for individual student researchers.",
    },
    {
        "code": "pro_researcher",
        "name": "Pro Researcher",
        "amount_kes": 699,
        "billing_interval": "month",
        "description": "Expanded monthly access for independent researchers.",
    },
    {
        "code": "educator",
        "name": "Educator",
        "amount_kes": 1499,
        "billing_interval": "month",
        "description": "Monthly access for educators supporting research and learning.",
    },
    {
        "code": "institution",
        "name": "Institution",
        "amount_kes": None,
        "billing_interval": "custom",
        "description": "Custom arrangements for schools, universities and research organisations.",
    },
)

_PLAN_BY_CODE = {plan["code"]: plan for plan in PLANS}


def list_plans():
    """Return a fresh list so callers cannot mutate the catalogue constants."""
    return [dict(plan) for plan in PLANS]


def get_plan(plan_code):
    """Return a copy of a known plan, or None for an unknown code."""
    plan = _PLAN_BY_CODE.get(str(plan_code or "").strip().lower())
    return dict(plan) if plan else None


def format_price(plan):
    """Format a plan amount in Kenyan shillings without implying payment status."""
    if plan.get("amount_kes") is None:
        return "Custom pricing"
    amount = int(plan["amount_kes"])
    if amount == 0:
        return "Free"
    suffix = "/month" if plan.get("billing_interval") == "month" else ""
    return f"KES {amount:,}{suffix}"

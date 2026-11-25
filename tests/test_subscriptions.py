from sfw.subscriptions import PLANS, format_price, get_plan, list_plans


def test_subscription_catalog_contains_approved_prices():
    prices = {plan["code"]: plan["amount_kes"] for plan in PLANS}
    assert prices == {
        "free": 0,
        "student": 299,
        "pro_researcher": 699,
        "educator": 1499,
        "institution": None,
    }


def test_subscription_catalog_price_formatting():
    assert format_price(get_plan("free")) == "Free"
    assert format_price(get_plan("student")) == "KES 299/month"
    assert format_price(get_plan("pro_researcher")) == "KES 699/month"
    assert format_price(get_plan("educator")) == "KES 1,499/month"
    assert format_price(get_plan("institution")) == "Custom pricing"


def test_get_plan_is_case_insensitive_and_returns_copy():
    plan = get_plan("STUDENT")
    assert plan["code"] == "student"
    plan["amount_kes"] = 1
    assert get_plan("student")["amount_kes"] == 299


def test_unknown_plan_is_rejected():
    assert get_plan("unlisted") is None


def test_list_plans_returns_independent_records():
    plans = list_plans()
    plans[0]["name"] = "Changed"
    assert list_plans()[0]["name"] == "Free"

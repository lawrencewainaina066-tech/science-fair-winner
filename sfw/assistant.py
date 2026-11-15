import requests
from .config import ai_settings

SYSTEM_PROMPT = """You are Science Fair Winner (SFW), a careful scientific research assistant.
Help users investigate science questions across biology, chemistry, physics, environmental science,
agriculture, mathematics, health and engineering. Explain methods clearly and adapt to the user's level.
Never invent citations, datasets, experimental observations, measurements or results. Separate established
evidence from hypotheses, estimates and suggestions. State assumptions, units, uncertainty and limitations.
Recommend safe, ethical, supervised methods. Do not present simulations as real experiments. Encourage
users to verify important claims against primary sources. When evidence is missing, say so explicitly."""

def ask_ai(messages):
    cfg = ai_settings()
    provider = cfg["provider"]
    if provider == "anthropic" and cfg["anthropic_key"]:
        payload = {
            "model": cfg["anthropic_model"], "max_tokens": 1800,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
        }
        r = requests.post("https://api.anthropic.com/v1/messages", json=payload, timeout=90,
                          headers={"x-api-key": cfg["anthropic_key"], "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"})
        r.raise_for_status()
        return "\n".join(x.get("text", "") for x in r.json().get("content", []) if x.get("type") == "text")
    if provider == "openai" and cfg["openai_key"]:
        payload = {"model": cfg["openai_model"],
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT}] +
                               [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]}
        r = requests.post("https://api.openai.com/v1/chat/completions", json=payload, timeout=90,
                          headers={"Authorization": f"Bearer {cfg['openai_key']}", "Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return None

def local_guidance(question, discipline="Interdisciplinary"):
    return (
        f"**SFW local research guidance — {discipline}**\n\n"
        f"Research question: {question}\n\n"
        "1. Define the problem precisely and identify the context.\n"
        "2. Search for peer-reviewed or authoritative sources; record complete references.\n"
        "3. Identify the independent, dependent and controlled variables where applicable.\n"
        "4. State a testable hypothesis and a null hypothesis if statistical testing is planned.\n"
        "5. Select a safe, ethical and reproducible method.\n"
        "6. Record raw observations with units, dates, instrument details and replicates.\n"
        "7. Choose analysis only after checking the study design and data assumptions.\n"
        "8. Report uncertainty, limitations and alternative explanations.\n\n"
        "This offline response is a planning framework, not a verified literature review or experimental finding. "
        "Configure an AI provider in .env for model-powered conversation."
    )

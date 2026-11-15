import requests
from .config import ai_settings

SYSTEM_PROMPT = """You are Science Fair Winner (SFW), a careful scientific research assistant.
Help users investigate science questions across biology, chemistry, physics, environmental science,
agriculture, mathematics, health and engineering. Explain methods clearly and adapt to the user's level.
Never invent citations, datasets, experimental observations, measurements or results. Separate established
evidence from hypotheses, estimates and suggestions. State assumptions, units, uncertainty and limitations.
Recommend safe, ethical, supervised methods. Do not present simulations as real experiments. Encourage
users to verify important claims against primary sources. When evidence is missing, say so explicitly."""


def _raise_provider_error(response, provider):
    if response.ok:
        return
    try:
        detail = response.json().get("error", {}).get("message", response.text)
    except Exception:
        detail = response.text
    raise RuntimeError(f"{provider} API error ({response.status_code}): {detail[:700]}")


def ask_ai(messages):
    cfg = ai_settings()
    provider = cfg["provider"]

    if provider == "gemini" and cfg["gemini_key"]:
        contents = []
        for message in messages[-12:]:
            role = "model" if message["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(message["content"])}]})
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1800}
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{cfg['gemini_model']}:generateContent"
        )
        r = requests.post(
            url, json=payload, timeout=90,
            headers={"x-goog-api-key": cfg["gemini_key"], "Content-Type": "application/json"}
        )
        _raise_provider_error(r, "Gemini")
        data = r.json()
        return "\n".join(
            part.get("text", "")
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            if part.get("text")
        ).strip()

    if provider == "anthropic" and cfg["anthropic_key"]:
        payload = {
            "model": cfg["anthropic_model"], "max_tokens": 1800,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
        }
        r = requests.post(
            "https://api.anthropic.com/v1/messages", json=payload, timeout=90,
            headers={"x-api-key": cfg["anthropic_key"], "anthropic-version": "2023-06-01",
                     "content-type": "application/json"}
        )
        _raise_provider_error(r, "Anthropic")
        return "\n".join(
            x.get("text", "") for x in r.json().get("content", []) if x.get("type") == "text"
        )

    if provider == "openai" and cfg["openai_key"]:
        payload = {
            "model": cfg["openai_model"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] +
                        [{"role": m["role"], "content": m["content"]} for m in messages[-12:]]
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions", json=payload, timeout=90,
            headers={"Authorization": f"Bearer {cfg['openai_key']}", "Content-Type": "application/json"}
        )
        _raise_provider_error(r, "OpenAI")
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
        "Configure SFW_AI_PROVIDER and the matching provider API key in Streamlit Secrets for model-powered conversation."
    )

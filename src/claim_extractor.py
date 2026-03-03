import json
import ollama
import re


ALLOWED_TYPES = {
    "RequestClaim",
    "CommitmentClaim",
    "ProposalClaim",
    "MeetingAnnouncementClaim",
    "InformationShareClaim"
}


def build_prompt(email):
    return f"""
You are extracting structured business memory from an organizational email.

Extract AT MOST ONE high-impact business claim.

Only extract the SINGLE most important actionable or decision-relevant statement.

Valid types:

1. RequestClaim
   - The sender asks someone to perform a task.

2. CommitmentClaim
   - The sender commits to performing an action.

3. ProposalClaim
   - The sender proposes a significant plan or strategic idea.

4. MeetingAnnouncementClaim
   - The sender schedules or announces a meeting with date/time/location.

5. InformationShareClaim
   - The sender shares important operational, financial, or project-critical information.

Do NOT extract:
- Minor suggestions
- Brainstorming ideas
- Casual discussion
- Greetings
- Small talk
- Test messages
- Low-impact confirmations

If no high-impact business statement exists, return [].

Return ONLY valid JSON.
No explanation.
No markdown.
No additional text.

Output format:

[
  {{
    "type": "RequestClaim | CommitmentClaim | ProposalClaim | MeetingAnnouncementClaim | InformationShareClaim",
    "content": "Clean standalone normalized sentence"
  }}
]

Email body:
{email["body"]}
"""


def correct_type(claim_type, content):
    content_lower = content.lower()

    if content_lower.startswith(("can you", "please", "send", "provide")):
        return "RequestClaim"

    if "meeting" in content_lower and re.search(r"\b\d{1,2}:\d{2}", content_lower):
        return "MeetingAnnouncementClaim"

    if content_lower.startswith(("i will", "we will")):
        return "CommitmentClaim"

    if content_lower.startswith(("i suggest", "i propose")):
        return "ProposalClaim"

    return claim_type


def select_highest_priority(claims):

    type_priority = {
        "MeetingAnnouncementClaim": 5,
        "RequestClaim": 4,
        "CommitmentClaim": 3,
        "ProposalClaim": 2,
        "InformationShareClaim": 1
    }

    def content_strength(text):
        text_lower = text.lower()

        strong_verbs = [
            "schedule",
            "send",
            "provide",
            "plan",
            "hold",
            "attend",
            "develop",
            "prepare",
            "define",
            "establish"
        ]

        score = 0
        for verb in strong_verbs:
            if verb in text_lower:
                score += 1

        return score

    claims_sorted = sorted(
        claims,
        key=lambda c: (
            type_priority.get(c["type"], 0),
            content_strength(c["content"])
        ),
        reverse=True
    )

    return claims_sorted[0]


def extract_claims(email):
    response = ollama.chat(
        model="mistral:7b",
        messages=[
            {"role": "user", "content": build_prompt(email)}
        ]
    )

    raw_output = response["message"]["content"]

    # Strict JSON parsing
    try:
        claims = json.loads(raw_output)
    except Exception:
        json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
        if json_match:
            try:
                claims = json.loads(json_match.group())
            except Exception:
                print("Invalid JSON from model:")
                print(raw_output)
                return []
        else:
            print("Invalid JSON from model:")
            print(raw_output)
            return []

    if not isinstance(claims, list):
        return []

    enriched_claims = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        claim_type = claim.get("type")
        content = claim.get("content")

        if not claim_type or claim_type not in ALLOWED_TYPES:
            continue

        if not content or len(content.split()) < 5:
            continue

        # Deterministic type correction
        claim_type = correct_type(claim_type, content)

        enriched_claim = {
            "type": claim_type,
            "actor": email["from"],
            "targets": email["to"],
            "content": content.strip(),
            "evidence": {
                "message_id": email["message_id"],
                "timestamp": email["date"],
                "excerpt": content.strip(),
                "thread_id": email["thread_id"]
            }
        }

        enriched_claims.append(enriched_claim)

    # Enforce minimal mode (at most one claim)
    if len(enriched_claims) > 1:
        enriched_claims = [select_highest_priority(enriched_claims)]

    return enriched_claims


# ---- Manual test ----
if __name__ == "__main__":
    with open("data/processed_emails.json", "r", encoding="utf-8") as f:
        emails = json.load(f)

    test_emails = emails[:5]  # Keep small for manual testing

    for i, email in enumerate(test_emails):
        print(f"\nEmail {i+1}")
        print("Subject:", email["subject"])

        claims = extract_claims(email)

        print("Claims:")
        print(json.dumps(claims, indent=2, default=str))
        print("-" * 60)
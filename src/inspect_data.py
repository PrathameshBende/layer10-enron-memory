import pandas as pd
from email import message_from_string
from email.utils import parsedate_to_datetime, getaddresses
import hashlib
import json


def parse_email(raw_email):
    msg = message_from_string(raw_email)

    # Parse From
    from_addresses = getaddresses([msg.get("From", "")])
    from_email = from_addresses[0][1] if from_addresses else None

    # Parse To
    to_addresses = getaddresses([msg.get("To", "")])
    to_emails = [addr[1] for addr in to_addresses if addr[1]]

    # Extract clean body
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    parts.append(part.get_payload(decode=True).decode(errors="ignore"))
                except:
                    continue
        body = "\n".join(parts)
    else:
        try:
            body = msg.get_payload(decode=True)
            if body:
                body = body.decode(errors="ignore")
            else:
                body = msg.get_payload()
        except:
            body = msg.get_payload()

    if body:
        body = body.strip()

    parsed = {
        "message_id": msg.get("Message-ID"),
        "date": None,
        "from": from_email,
        "to": to_emails,
        "subject": msg.get("Subject"),
        "body": body
    }

    if msg.get("Date"):
        try:
            parsed["date"] = parsedate_to_datetime(msg.get("Date"))
        except:
            parsed["date"] = msg.get("Date")

    return parsed


def compute_fingerprint(parsed_email):
    content_string = (
        str(parsed_email["from"]) +
        str(parsed_email["to"]) +
        str(parsed_email["subject"]) +
        str(parsed_email["body"])
    )
    return hashlib.sha256(content_string.encode()).hexdigest()


def parse_batch(path, limit=1000):
    df = pd.read_csv(path, nrows=limit)

    parsed_emails = []
    seen_ids = set()
    seen_fingerprints = set()
    duplicate_count = 0

    for _, row in df.iterrows():
        raw_email = row["message"]
        try:
            parsed = parse_email(raw_email)

            msg_id = parsed["message_id"]
            fingerprint = compute_fingerprint(parsed)

            if msg_id in seen_ids or fingerprint in seen_fingerprints:
                duplicate_count += 1
                continue

            seen_ids.add(msg_id)
            seen_fingerprints.add(fingerprint)
            parsed_emails.append(parsed)

        except Exception as e:
            print("Error parsing email:", e)

    print(f"\nTotal processed: {limit}")
    print(f"Unique emails: {len(parsed_emails)}")
    print(f"Duplicates removed: {duplicate_count}")
    with open("data/processed_emails.json", "w", encoding="utf-8") as f:
        json.dump(parsed_emails, f, default=str, indent=2)

    print("\nSaved processed emails to data/processed_emails.json")

    return parsed_emails


if __name__ == "__main__":
    parse_batch("data/emails.csv", limit=1000)
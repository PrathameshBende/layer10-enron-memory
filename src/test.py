from collections import Counter
import re
import json
with open("data/processed_emails.json", "r", encoding="utf-8") as f:
    emails = json.load(f)

emails = emails[:600]

word_counter = Counter()

for email in emails:
    body = email.get("body", "")
    words = re.findall(r"\b[a-zA-Z]{4,}\b", body.lower())
    word_counter.update(words)

print("\nTop 50 words:\n")
for word, count in word_counter.most_common(50):
    print(word, count)
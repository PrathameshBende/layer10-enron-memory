import json

def verify(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Total records:", len(data))

    # Print first record keys for sanity
    if len(data) > 0:
        print("\nKeys in first record:")
        print(data[0].keys())

if __name__ == "__main__":
    verify("data/processed_emails.json")
import json
import hashlib
from collections import defaultdict
import re
from datetime import datetime
import ollama
import time
import pickle

def normalize_subject(subject):
    if not subject:
        return None

    subject = subject.lower().strip()

    prefixes = ["re:", "fw:", "fwd:"]
    changed = True

    while changed:
        changed = False
        for prefix in prefixes:
            if subject.startswith(prefix):
                subject = subject[len(prefix):].strip()
                changed = True

    return subject

class MemoryGraph:
    def __init__(self):
        self.people = set()
        self.messages = {}
        self.sent_edges = defaultdict(list)
        self.received_edges = defaultdict(list)
        self.threads = {}
        self.claims = {}  # claim_id -> claim object
        self.claim_actor_edges = defaultdict(list)  # actor -> claim_ids
        self.claim_target_edges = defaultdict(list)  # target -> claim_ids
        self.claim_evidence = {}  # claim_id -> evidence object

    def add_message(self, message):
        msg_id = message["message_id"]

        if not msg_id:
            return

        self.messages[msg_id] = message

        subject_key = normalize_subject(message["subject"])

        if subject_key:
            thread_id = hashlib.sha256(subject_key.encode()).hexdigest()
        else:
            # fallback: use message_id to create singleton thread
            thread_id = hashlib.sha256(msg_id.encode()).hexdigest()

        message["thread_id"] = thread_id

        if thread_id not in self.threads:
            self.threads[thread_id] = []

        self.threads[thread_id].append(msg_id)

        # ----- Sender -----
        sender = message["from"]
        if sender:
            self.people.add(sender)
            self.sent_edges[sender].append(msg_id)

        # ----- Recipients -----
        recipients = message["to"]
        for recipient in recipients:
            self.people.add(recipient)
            self.received_edges[recipient].append(msg_id)

    def summary(self):
        print(f"Total People: {len(self.people)}")
        print(f"Total Messages: {len(self.messages)}")
        print(f"Total Send Edges: {sum(len(v) for v in self.sent_edges.values())}")
        print(f"Total Receive Edges: {sum(len(v) for v in self.received_edges.values())}")
        print(f"Total Thread Groups (by subject): {len(self.threads)}")
        print(f"Total Claims: {len(self.claims)}")
        print(f"Total Claim-Actor Edges: {sum(len(v) for v in self.claim_actor_edges.values())}")
        print(f"Total Claim-Target Edges: {sum(len(v) for v in self.claim_target_edges.values())}")

    def add_claim(self, claim):
        # Normalize content
        content_norm = claim["content"].strip().lower()

        # Deterministic claim identity (actor + normalized content)
        claim_string = claim["actor"] + content_norm
        claim_id = hashlib.sha256(claim_string.encode()).hexdigest()

        if claim_id not in self.claims:
            # First time seeing this claim
            confidence = self.compute_confidence(claim["content"])

            self.claims[claim_id] = {
                "type": claim["type"],
                "actor": claim["actor"],
                "targets": claim["targets"],
                "content": claim["content"],
                "confidence": confidence,
                "evidence": [claim["evidence"]]
}

            # Actor edge
            self.claim_actor_edges[claim["actor"]].append(claim_id)

            # Target edges
            for target in claim["targets"]:
                self.claim_target_edges[target].append(claim_id)

        else:
            # Duplicate claim — append new evidence
            self.claims[claim_id]["evidence"].append(claim["evidence"])\
                
    def get_claims_by_actor(self, actor):
        claim_ids = self.claim_actor_edges.get(actor, [])
        return [self.claims[cid] for cid in claim_ids]
    
    def compute_confidence(self, content):

        content_lower = content.lower()

        score = 0.3  # lower base

        strong_signals = [
            "need",
            "please",
            "schedule",
            "meeting",
            "propose",
            "send",
            "provide",
            "request",
            "plan",
            "must",
            "attend",
            "make sure"
        ]

        medium_signals = [
            "suggest",
            "think",
            "consider",
            "will",
            "should",
            "how about"
        ]

        informational_signals = [
            "is for sale",
            "is selling",
            "approved",
            "forwarded"
        ]

        # Strong signals
        for word in strong_signals:
            if word in content_lower:
                score += 0.2

        # Medium signals
        for word in medium_signals:
            if word in content_lower:
                score += 0.1

        # Informational signals
        for word in informational_signals:
            if word in content_lower:
                score += 0.05

        # --- Proper time/date detection using regex ---
        if re.search(r"\b\d{1,2}(st|nd|rd|th)\b", content_lower):
            score += 0.1
        # Detect time format like 2:30 or 2:30 PM
        if re.search(r"\b\d{1,2}:\d{2}\s?(am|pm)?\b", content_lower):
            score += 0.2

        # Detect weekday names
        if re.search(r"\b(monday|tuesday|wednesday|thursday|friday)\b", content_lower):
            score += 0.15

        # Detect month names
        if re.search(
            r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
            r"january|february|march|april|june|july|august|"
            r"september|october|november|december)\b",
            content_lower
        ):
            score += 0.15

        # Detect ordinal dates like 10th, 3rd, 21st
        if re.search(r"\b\d{1,2}(st|nd|rd|th)\b", content_lower):
            score += 0.1

        return min(score, 0.95)

    def compute_recency_score(self, evidence_list):
        # Use most recent evidence timestamp
        latest = None

        for ev in evidence_list:
            ts = ev["timestamp"]
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except:
                    continue

            if latest is None or ts > latest:
                latest = ts

        if latest is None:
            return 0.5

        # Days since latest evidence
        days_old = (datetime.now(latest.tzinfo) - latest).days

        # Decay function: newer = closer to 1
        recency_score = max(0.3, 1 / (1 + days_old / 30))

        return recency_score
    
    def retrieve_context(self, actor, min_confidence=0.5, limit=5):
        claim_ids = self.claim_actor_edges.get(actor, [])

        ranked = []

        for cid in claim_ids:
            claim = self.claims[cid]

            if claim["confidence"] < min_confidence:
                continue

            recency = self.compute_recency_score(claim["evidence"])

            # Combined score (confidence weighted more)
            combined_score = 0.7 * claim["confidence"] + 0.3 * recency

            ranked.append((combined_score, claim))

        # Sort highest first
        ranked.sort(key=lambda x: x[0], reverse=True)

        return [item[1] for item in ranked[:limit]]
    
    def build_context_pack(self, claims):
        packs = []

        for claim in claims:
            latest_evidence = max(
                claim["evidence"],
                key=lambda ev: ev["timestamp"]
            )

            pack = {
                "claim": claim["content"],
                "confidence": round(claim["confidence"], 2),
                "actor": claim["actor"],
                "targets": claim["targets"],
                "evidence": {
                    "message_id": latest_evidence["message_id"],
                    "timestamp": latest_evidence["timestamp"],
                    "thread_id": latest_evidence["thread_id"],
                    "excerpt": latest_evidence["excerpt"]
                }
            }

            packs.append(pack)

        return packs

    def answer_question(self, question, actor=None, min_confidence=0.5, limit=5):
        # Retrieve relevant context
        if actor:
            claims = self.retrieve_context(actor, min_confidence, limit)
        else:
            # fallback: use all claims
            claims = sorted(
                self.claims.values(),
                key=lambda c: c["confidence"],
                reverse=True
            )[:limit]

        if not claims:
            return "No relevant memory found."

        # Build lightweight relevance check prompt
        relevance_prompt = f"""
        You are selecting relevant memory claims for answering a question.

        Question:
        {question}

        Claims:
        """

        for i, claim in enumerate(claims):
            relevance_prompt += f"{i+1}. {claim['content']}\n"

        relevance_prompt += """
        Return a list of claim numbers that are directly relevant to the question.
        Return ONLY numbers separated by commas.
        If none are relevant, return: none
        """

        relevance_response = ollama.chat(
            model="mistral:7b",
            messages=[{"role": "user", "content": relevance_prompt}]
        )

        relevance_text = relevance_response["message"]["content"].strip().lower()
        print("\nDEBUG RELEVANCE RESPONSE:\n", relevance_text)
        if relevance_text != "none":
            try:
                numbers = re.findall(r"\d+", relevance_text)
                indices = [int(n) - 1 for n in numbers]
                claims = [claims[i] for i in indices if 0 <= i < len(claims)]
            except:
                pass

        if not claims:
            return "Insufficient grounded information."
        
        #Context block
        context_blocks = []

        for claim in claims:
            latest_evidence = max(
                claim["evidence"],
                key=lambda ev: ev["timestamp"]
            )

            block = (
                f"Claim: {claim['content']}\n"
                f"Confidence: {round(claim['confidence'],2)}\n"
                f"Message ID: {latest_evidence['message_id']}\n"
                f"Timestamp: {latest_evidence['timestamp']}\n"
            )

            context_blocks.append(block)

        context_text = "\n---\n".join(context_blocks)
        
        prompt = f"""
            You are answering a question using the provided memory context.

            Base your answer strictly on the claims below.
            You may make reasonable inferences directly supported by the claims.

            If the context does not contain relevant information, say:
            "Insufficient grounded information."

            Cite the relevant Message IDs in your answer.

            Context:
            {context_text}

            Question:
            {question}
        """

        print("\nDEBUG CONTEXT SENT TO MODEL:\n")
        print(context_text)

        response = ollama.chat(
            model="mistral:7b",
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]

def load_processed_emails(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    emails = load_processed_emails("data/processed_emails.json")

    # limit for testing
    emails = emails[:600]

    from claim_extractor import extract_claims

    graph = MemoryGraph()

    start_time = time.time()
    
    signal_words =  [
        # action verbs
        "will", "would", "should", "need", "must",
        "please", "call", "provide", "send", "request",
        "plan", "propose", "develop", "prepare", "define",

        # business nouns
        "project", "loan", "cost", "price", "market",
        "construction", "meeting", "deadline", "report",
        "budget", "proposal"
    ]

    for idx, email in enumerate(emails, start=1):
        print(f"[{idx}/{len(emails)}] Processing email...", end=" ")

        graph.add_message(email)

        body = email.get("body", "")
        if not body:
            print("Skipped (no body)")
            continue

        body_lower = body.lower()

        if any(word in body_lower for word in signal_words):
            print("Signal detected → Extracting with LLM...", end=" ")
            claims = extract_claims(email)

            if claims:
                for claim in claims:
                    graph.add_claim(claim)
                print(f"Added {len(claims)} claim(s)")
            else:
                print("No claim extracted")
        else:
            print("Skipped (no signal)")
        
    end_time = time.time()
    
    print(f"\nProcessing Time: {round(end_time - start_time, 2)} seconds")
    
    top_claims = graph.retrieve_context(
        actor="phillip.allen@enron.com",
        min_confidence=0.5,
        limit=5
    )

    context_packs = graph.build_context_pack(top_claims)

    with open("memory_graph.pkl", "wb") as f:
        pickle.dump(graph, f)

    print("Memory graph saved.")


    answer = graph.answer_question(
        question="What operational tasks did Phillip assign?",
        actor="phillip.allen@enron.com"
    )

    print(answer)
    graph.summary()
import pickle
from pyvis.network import Network
from build_graph import MemoryGraph

# Load memory graph
with open("memory_graph.pkl", "rb") as f:
    graph = pickle.load(f)

net = Network(
    height="800px",
    width="100%",
    directed=True,
    bgcolor="#111111",
    font_color="white"
)

# Add actor nodes
for person in graph.people:
    net.add_node(
        person,
        label=person.split("@")[0],
        color="#1f78b4",
        title=f"Person: {person}"
    )

# Add claim nodes
for claim_id, claim in graph.claims.items():
    
    claim_text = claim["content"][:80]

    net.add_node(
        claim_id,
        label="Claim",
        color="#33a02c",
        title=f"""
Claim: {claim['content']}
Confidence: {round(claim['confidence'],2)}
"""
    )

    # Actor -> Claim edge
    net.add_edge(claim["actor"], claim_id)

    # Claim -> Evidence nodes
    for ev in claim["evidence"]:

        evidence_id = ev["message_id"]

        net.add_node(
            evidence_id,
            label="Email",
            color="#e31a1c",
            title=f"""
Message ID: {ev['message_id']}
Date: {ev['timestamp']}
Excerpt:
{ev['excerpt']}
"""
        )

        net.add_edge(claim_id, evidence_id)

# Physics layout
net.toggle_physics(True)

# Save interactive graph
net.show("memory_graph_visualization.html", notebook=False)
print("Graph visualization saved as memory_graph_visualization.html")
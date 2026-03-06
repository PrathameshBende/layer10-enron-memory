import pickle
from build_graph import MemoryGraph

with open("memory_graph.pkl", "rb") as f:
    graph = pickle.load(f)

print("Memory graph loaded.\n")

while True:
    question = input("Ask a question (or type 'exit'): ")

    if question.lower() == "exit":
        break

    answer = graph.answer_question(
        question=question,
        actor="phillip.allen@enron.com"
    )

    print("\nAnswer:")
    print(answer)
    print("\n" + "-"*60 + "\n")
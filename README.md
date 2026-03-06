Step 1 — Download Corpus
Download the Enron dataset from Kaggle and place:
python src/visualize_graph.py

Step 2 — Preprocess Emails
python src/inspect_data.py

Step 3 — Build Memory Graph
python src/build_graph.py

Step 4 — Query Memory
python src/query_memory.py

Step 5 — Visualization

Streamlit UI:
streamlit run src/visualize_memory.py

Graph view:
python src/visualize_graph.py
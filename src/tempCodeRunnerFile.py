        response = ollama.chat(
            model="misrtal:7b",
            messages=[{"role": "user", "content": prompt}]
        )
import os
import chromadb
from google import genai

# API Key
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini client
client = genai.Client(api_key=API_KEY)

# ChromaDB setup
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="runbooks")

# ── Load runbooks into ChromaDB ──
def load_runbooks():
    runbook_folder = "runbooks"
    documents = []
    ids = []

    for i, filename in enumerate(os.listdir(runbook_folder)):
        if filename.endswith(".txt"):
            filepath = os.path.join(runbook_folder, filename)
            with open(filepath, "r") as f:
                content = f.read()
                documents.append(content)
                ids.append(str(i))
                print(f"Loaded runbook: {filename}")

    collection.add(documents=documents, ids=ids)
    print(f"\nTotal runbooks loaded: {len(documents)}\n")

# ── Search runbooks ──
def search_runbooks(query):
    results = collection.query(
        query_texts=[query],
        n_results=1
    )
    if results["documents"][0]:
        return results["documents"][0][0]
    return None

# ── SRE Agent ──
def sre_agent(question):
    print(f"Question: {question}\n")

    # Step 1 — Search runbooks first
    print("Searching runbooks...")
    runbook_context = search_runbooks(question)

    if runbook_context:
        print("Runbook found — using as context\n")
        prompt = f"""
You are an SRE Agent.
Use this runbook to answer the question:

RUNBOOK:
{runbook_context}

QUESTION:
{question}

Give a clear and specific answer
based on the runbook above.
"""
    else:
        print("No runbook found — using general knowledge\n")
        prompt = question

    # Step 2 — Send to Gemini
    import time
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )
            print("SRE Agent Response:")
            print("─" * 50)
            print(response.text)
            print("─" * 50)
            break
        except Exception as e:
            if attempt < 2:
                print(f"Retrying in 5 seconds... attempt {attempt+1}")
                time.sleep(5)
            else:
                print(f"Failed after 3 attempts: {e}")

# ── Main ──
if __name__ == "__main__":
    load_runbooks()

    # Test questions
    sre_agent("Pod is in CrashLoopBackOff and exit code is 137")
    print("\n")
    sre_agent("Pod is stuck in Pending state")
    print("\n")
    sre_agent("CPU is very high on our pods")

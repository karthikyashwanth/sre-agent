import os
import time
import subprocess
import chromadb
from google import genai

# API Key
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini client
client = genai.Client(api_key=API_KEY)

# ChromaDB setup
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="runbooks")

# ── Load runbooks ──
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

    collection.add(documents=documents, ids=ids)
    print(f"Loaded {len(documents)} runbooks\n")

# ── Search runbooks ──
def search_runbooks(query):
    results = collection.query(
        query_texts=[query],
        n_results=1
    )
    if results["documents"][0]:
        return results["documents"][0][0]
    return None

# ── Run kubectl command ──
def run_kubectl(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

# ── Detect issues in cluster ──
def detect_issues():
    print("Scanning cluster for issues...")
    pods = run_kubectl("kubectl get pods --all-namespaces")
    print(pods)

    issues = []
    for line in pods.splitlines():
        if "CrashLoopBackOff" in line:
            parts = line.split()
            namespace = parts[0]
            pod_name = parts[1]
            issues.append({
                "type": "CrashLoopBackOff",
                "namespace": namespace,
                "pod": pod_name
            })
        elif "Pending" in line:
            parts = line.split()
            namespace = parts[0]
            pod_name = parts[1]
            issues.append({
                "type": "Pending",
                "namespace": namespace,
                "pod": pod_name
            })

    return issues

# ── Investigate issue ──
def investigate_issue(issue):
    pod = issue["pod"]
    namespace = issue["namespace"]
    issue_type = issue["type"]

    print(f"\nIssue detected: {issue_type}")
    print(f"Pod: {pod}")
    print(f"Namespace: {namespace}")
    print("─" * 50)

    # Get pod logs
    print("Getting pod logs...")
    logs = run_kubectl(
        f"kubectl logs {pod} -n {namespace} --previous --tail=20"
    )

    # Get pod description
    print("Getting pod description...")
    description = run_kubectl(
        f"kubectl describe pod {pod} -n {namespace}"
    )

    # Search runbooks
    print("Searching runbooks...")
    runbook = search_runbooks(issue_type)

    # Build prompt
    prompt = f"""
You are an SRE Agent investigating a Kubernetes issue.

ISSUE TYPE: {issue_type}
POD NAME: {pod}
NAMESPACE: {namespace}

POD LOGS:
{logs}

POD DESCRIPTION (last 50 lines):
{description[-2000:]}

RUNBOOK:
{runbook}

Based on the above information:
1. What is the exact root cause?
2. What is the immediate fix?
3. What kubectl command should be run?

Be specific and concise.
"""

    # Send to Gemini with retry
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            print("\nSRE Agent Analysis:")
            print("─" * 50)
            print(response.text)
            print("─" * 50)
            break
        except Exception as e:
            if attempt < 2:
                print(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"Failed: {e}")

# ── Main ──
if __name__ == "__main__":
    print("=" * 50)
    print("SRE Agent Starting...")
    print("=" * 50)

    load_runbooks()

    # Detect issues
    issues = detect_issues()

    if not issues:
        print("No issues detected. Cluster is healthy.")
    else:
        print(f"\nFound {len(issues)} issue(s)\n")
        for issue in issues:
            investigate_issue(issue)
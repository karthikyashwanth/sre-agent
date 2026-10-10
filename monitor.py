import os
import time
import subprocess
import chromadb
from datetime import datetime
from google import genai

# API Key
API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini client
client = genai.Client(api_key=API_KEY)

# ChromaDB setup
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="runbooks")

# Log file
LOG_FILE = "sre_agent.log"

# ── Logging ──
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

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
    log(f"Loaded {len(documents)} runbooks")

# ── Search runbooks ──
def search_runbooks(query):
    results = collection.query(
        query_texts=[query],
        n_results=1
    )
    if results["documents"][0]:
        return results["documents"][0][0]
    return None

# ── Run kubectl ──
def run_kubectl(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="ignore"
        )
        return result.stdout
    except Exception as e:
        return f"Error: {e}"

# ── Detect issues ──
def detect_issues():
    pods = run_kubectl("kubectl get pods --all-namespaces")
    issues = []

    for line in pods.splitlines():
        if "CrashLoopBackOff" in line:
            parts = line.split()
            issues.append({
                "type": "CrashLoopBackOff",
                "namespace": parts[0],
                "pod": parts[1]
            })
        elif "Pending" in line:
            parts = line.split()
            issues.append({
                "type": "Pending",
                "namespace": parts[0],
                "pod": parts[1]
            })
        elif "OOMKilled" in line:
            parts = line.split()
            issues.append({
                "type": "OOMKilled",
                "namespace": parts[0],
                "pod": parts[1]
            })

    return issues

# ── Investigate issue ──
def investigate_issue(issue):
    pod = issue["pod"]
    namespace = issue["namespace"]
    issue_type = issue["type"]

    log(f"Investigating: {issue_type} on {pod}")

    logs = run_kubectl(
        f"kubectl logs {pod} -n {namespace} --previous --tail=20"
    )
    description = run_kubectl(
        f"kubectl describe pod {pod} -n {namespace}"
    )
    runbook = search_runbooks(issue_type)

    prompt = f"""
You are an SRE Agent.

ISSUE: {issue_type}
POD: {pod}
NAMESPACE: {namespace}

LOGS:
{logs}

DESCRIPTION:
{description[-2000:]}

RUNBOOK:
{runbook}

Provide:
1. Root cause in one line
2. Exact fix in one line
3. kubectl command to run
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            log("─" * 50)
            log(f"ISSUE: {issue_type} — {pod}")
            log("ANALYSIS:")
            for line in response.text.splitlines():
                log(line)
            log("─" * 50)
            break
        except Exception as e:
            if attempt < 2:
                log(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                log(f"Gemini failed: {e}")

# ── Monitor loop ──
def monitor(interval_minutes=5):
    log("=" * 50)
    log("SRE Agent Monitor Started")
    log(f"Scanning every {interval_minutes} minutes")
    log("=" * 50)

    load_runbooks()

    while True:
        log("\nScanning cluster...")
        issues = detect_issues()

        if not issues:
            log("Cluster healthy — no issues found")
        else:
            log(f"Found {len(issues)} issue(s)")
            for issue in issues:
                investigate_issue(issue)

        log(f"Next scan in {interval_minutes} minutes...")
        time.sleep(interval_minutes * 60)

# ── Main ──
if __name__ == "__main__":
    monitor(interval_minutes=5)
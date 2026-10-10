# SRE Agent — AI-Powered Kubernetes Monitor

An intelligent SRE Agent that automatically monitors 
Kubernetes clusters, detects issues, and provides 
AI-powered root cause analysis and fixes.

## Architecture

EKS Cluster → Agent detects issues
│
▼
RAG searches runbooks
│
▼
Gemini AI analyses
│
▼
Root cause + Fix suggested


## Features

- Auto scans EKS cluster every 5 minutes
- Detects CrashLoopBackOff, Pending, OOMKilled
- RAG-powered runbook search using ChromaDB
- AI root cause analysis using Gemini API
- Logs all findings to sre_agent.log

## Tech Stack

- Python
- Google Gemini API
- ChromaDB (vector database)
- kubectl (Kubernetes CLI)
- Amazon EKS

## Setup

1. Install dependencies:
pip install google-genai chromadb sentence-transformers

2. Set API key:
set GEMINI_API_KEY=your-key-here

3. Configure kubectl:
aws eks update-kubeconfig --name your-cluster --region us-east-1

4. Run monitor:
python monitor.py

## Project Structure

sre-agent/
├── monitor.py       # Auto monitoring every 5 mins
├── k8s_agent.py     # kubectl + AI analysis
├── rag.py           # RAG with runbooks
├── runbooks/        # SRE runbooks
│   ├── crashloopbackoff.txt
│   ├── pod-pending.txt
│   └── high-cpu.txt
└── test-pod.yaml    # Test deployment
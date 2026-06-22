# 🌍 Samketan AI: Universal Market Intelligence Agent

Samketan AI is an autonomous, hybrid, multi-agent system designed to democratize enterprise-level market research and document intelligence for MSMEs in Tier-2 and Tier-3 cities. 

Built as a "Strategic Analyst in a Box," Samketan bridges the gap between unstructured local data (PDFs, Tenders, CVs) and real-time global intelligence (Live Web Search).

## 🧠 Architecture: The Multi-Agent Hybrid System

Unlike standard chatbots that guess answers ("hallucinate"), Samketan operates on a strict **Plan-and-Execute** framework using two distinct AI agents:

1. **The Architect (Strategic Planner):** Powered by dynamic LLM routing, the Architect analyzes the user's goal, determines the domain (Business, Politics, Logistics, etc.), and outputs a strict JSON execution strategy.
2. **The Hunter (Web Execution):** An autonomous web-scraper that executes the Architect's search commands in real-time.
3. **The Hybrid Switch (Document Intelligence):** The core application layer. It automatically detects if a task requires public internet data (routes to Hunter) or private document analysis (routes to the internal LLM for PDF parsing).

## 🚀 Key Features

* **Auto-Switching Execution:** Seamlessly pivots between Live Web Search and Private Document Reading.
* **Universal Domain Adaptation:** The AI autonomously adjusts its strategy whether the user is asking for Political Trends, Commodity Prices, or Resume Analysis.
* **Model Auto-Detection:** Built-in fail-safes to query the Google Gemini API for the fastest available model (`flash` or `pro`), preventing 404 crashes and ensuring maximum uptime.
* **Document Parsing:** Ingests complex PDFs (Tenders, Reports, CVs) and injects them directly into the AI's cognitive context.

## 🛠️ Tech Stack
* **Frontend/UI:** Streamlit
* **AI Brain:** Google Gemini API (Generative AI)
* **Web Search Engine:** DuckDuckGo Search API
* **Document Processing:** PyPDF

## ⚙️ Installation & Usage

1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

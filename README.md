# ⚖️ LAW-GPT: Advanced Agentic RAG for Legal Intelligence

LAW-GPT is a state-of-the-art legal intelligence platform powered by an Agentic Retrieval-Augmented Generation (RAG) engine. It is designed to provide precise, context-aware legal responses based on a comprehensive ingestion of statutes, case law, and consumer documents.

## 🚀 Key Features

- **Agentic RAG Engine**: Multi-agent system for clarification, reasoning, and factual retrieval.
- **Comprehensive Data Ingestion**: Automated pipelines for statute processing, case law extraction, and cloud synchronization.
- **Professional Legal UI**: Premium, glassmorphism-inspired interface optimized for legal professionals.
- **Smart Gating**: Expert-level validation of legal queries and response quality.

## 📊 System Architecture & Statistics

### Statistics Overview
- **Core Scripts**: 50+ Specialized Python scripts for data processing and RAG operations.
- **Supported Documents**: Statutes, Case Law (SC, NCDRC), Consumer Acts.
- **Optimization**: 10/10 Quality Score target with 10% speed optimization.

### Architecture Diagram

```mermaid
graph TD
    User([User Query]) --> Gatekeeper{Expert Gatekeeper}
    Gatekeeper --> |Clarification Needed| Clarifier[Clarification Agent]
    Gatekeeper --> |Professional Query| RAG[Agentic RAG Engine]
    
    Clarifier --> User
    
    subgraph Data Layer
        Zilliz[(Zilliz Vector DB)]
        Supabase[(Supabase Metadata)]
        Local[(Local Storage)]
    end
    
    RAG --> |Context Retrieval| DataLayer
    DataLayer --> RAG
    
    RAG --> |Synthesized Response| Reasoning[Reasoning Agent]
    Reasoning --> FinalResponse([Professional Legal Response])
```

## 📂 Project Structure

- `rag_system/`: Core Agentic RAG logic and agent implementations.
- `scripts/`: Data ingestion, testing, and deployment scripts.
- `frontend/`: React/Next.js based professional interface.
- `tests/`: Comprehensive quality and accuracy test suites.

## 🛠️ Local Installation & Setup

Follow these steps to set up and run LAW-GPT on your local machine.

### Prerequisites
- **Python 3.10+** installed on your system.
- **Git** installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Knnivedh/LAW-GPT.git
cd LAW-GPT
```

### 2. Create a Virtual Environment (Recommended)
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install all required Python packages using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example environment file and add your actual API keys:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Open the `.env` file in your text editor and fill in your keys (e.g., `ZILLIZ_TOKEN`, `HF_TOKEN`, `SUPABASE_KEY`).

### 5. Run the Application
You can start the main fastAPI application server using:
```bash
python main.py
```
Alternatively, if you are testing the PageIndex interface:
```bash
python deploy_pageindex_cli.py
```
*(If using the provided batch script on Windows, you can simply run `.\START_ALL.bat`)*

---

---
*Created and maintained by [Knnivedh](https://github.com/Knnivedh)*

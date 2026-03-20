---
description: Trigger the Deep Research Agent using OWL
---

# Deep Research Agent Workflow

To trigger the `DeepResearchAgent`, run the following command with your query.

1.  Run the deep research agent with the user's query as an argument (or it will prompt/default).

```bash
# // turbo
$env:PYTHONIOENCODING='utf-8'; python rag_system/deep_research_agent.py "Your query here"
```

*Note: In the future, we can update the script to accept command-line arguments for the query.*

# LAW-GPT System Architecture And Operations

## 1. Executive Summary

LAW-GPT is not a single-model chatbot. It is a routed legal AI system for Indian law built from these layers:

- FastAPI API gateway
- query guardrails and routing
- clarification engine for personal-case consultations
- agentic RAG engine for planning, retrieval, synthesis, and verification
- parametric retrieval layer for vector and hybrid search
- vectorless statute retrieval layer through PageIndex
- session memory and semantic cache
- Azure App Service deployment with hot-patch startup logic

The current production shape favors correctness and recovery over raw concurrency. It is designed to answer simple legal questions directly, ask clarification questions for case-specific problems, and degrade gracefully when an upstream model or retrieval path has issues.

## 2. Current Live System Status

Latest verified live benchmark state against the hosted backend:

- Core chatbot benchmark: 13/13 pass, 100 percent
- Routing and 5-question clarification benchmark: 16/16 pass, 100 percent
- Context retention benchmark: 19/20 chains pass, 95 percent
- Ground-truth legal QA benchmark: composite 85.68 percent, section citation accuracy 90.33 percent, factual accuracy 81.33 percent

Source reports:

- [tests/results/t12_core_behaviors_20260307_163143.json](tests/results/t12_core_behaviors_20260307_163143.json)
- [tests/results/t11_routing_clarification_20260307_162945.json](tests/results/t11_routing_clarification_20260307_162945.json)
- [tests/results/t6_context_20260307_163525.json](tests/results/t6_context_20260307_163525.json)
- [tests/results/accuracy_report_20260303_094228.json](tests/results/accuracy_report_20260303_094228.json)

## 3. Top-Level Components

### API Layer

Main API entry point:

- [kaanoon_test/advanced_rag_api_server.py](kaanoon_test/advanced_rag_api_server.py)

Responsibilities:

- health and status endpoints
- startup and background initialization
- request validation and session management
- safety refusal
- out-of-scope foreign-law rejection
- invalid section reference rejection
- clarification loop orchestration
- fallback handling on rate limits or partial failures

### Unified Orchestrator

Main orchestrator:

- [kaanoon_test/system_adapters/unified_advanced_rag.py](kaanoon_test/system_adapters/unified_advanced_rag.py)

Responsibilities:

- initialize retrieval stores
- initialize main LLM client manager
- initialize agentic engine
- initialize memory manager
- initialize PageIndex retriever
- route simple and complex paths into the agentic system

### Agentic RAG Engine

Main reasoning loop:

- [kaanoon_test/system_adapters/agentic_rag_engine.py](kaanoon_test/system_adapters/agentic_rag_engine.py)

Core stages:

- memory and cache lookup
- conversation-context injection
- simple direct mode for factual queries
- planning
- retrieval
- synthesis
- verification or reflection
- plan refinement when confidence is low
- memory and cache update after answer generation

### Clarification Engine

Case-consultation state machine:

- [kaanoon_test/system_adapters/clarification_engine.py](kaanoon_test/system_adapters/clarification_engine.py)

Responsibilities:

- detect whether the user is asking a knowledge question or describing a personal legal problem
- ask up to five clarification questions
- maintain question-answer history
- synthesize a final consultation matrix for downstream RAG

### Parametric Retrieval Layer

Main parameter-driven retriever:

- [kaanoon_test/system_adapters/parametric_rag_system.py](kaanoon_test/system_adapters/parametric_rag_system.py)

Responsibilities:

- accept routing parameters such as domain, keywords, sections, case names, and complexity
- build an enhanced query
- choose direct hybrid retrieval for simple and medium queries
- use advanced retrieval with multi-query and HyDE only for complex queries
- rerank results
- build retrieval context for the generator

### Vectorless Statute Retrieval Layer

PageIndex retriever:

- [kaanoon_test/system_adapters/pageindex_retriever.py](kaanoon_test/system_adapters/pageindex_retriever.py)

Responsibilities:

- upload statutes once to a tree index in PageIndex cloud
- use LLM-guided tree traversal rather than vector similarity
- fetch exact text from relevant statute nodes
- fall back cleanly to normal retrieval if PageIndex is unavailable

### Memory Layer

Memory manager:

- [kaanoon_test/system_adapters/persistent_memory.py](kaanoon_test/system_adapters/persistent_memory.py)

Responsibilities:

- short-term conversation memory
- persisted session memory across requests
- long-term user profile memory
- semantic answer cache

### LLM Client Rotation Layer

Provider and key manager:

- [kaanoon_test/utils/client_manager.py](kaanoon_test/utils/client_manager.py)

Responsibilities:

- load Groq and Cerebras keys
- rotate keys after a request count threshold
- rotate immediately on 429 rate-limit events
- map model names when moving between providers

## 4. End-To-End Request Flow

### Block Diagram 1 — Full System Overview

All major layers of the system in one view, grouped by responsibility.

```mermaid
flowchart TD
    subgraph CLIENTS[" CLIENTS "]
        U1[Web UI]
        U2[API Clients]
        U3[Test Runners]
    end

    subgraph GATEWAY[" API GATEWAY  advanced_rag_api_server.py "]
        GW1[Health and Warmup Check]
        GW2[Prompt Injection Strip]
        GW3[Safety Guardrails\nIllegal guidance refusal\nForeign-law rejection\nFake section rejection]
        GW4[Session Lookup]
    end

    subgraph CLARIFICATION[" CLARIFICATION ENGINE  clarification_engine.py "]
        CE1[Query Classifier\nKnowledge vs Case Consultation]
        CE2[Q1 to Q5 Question Loop]
        CE3[Session Store\nDisk-backed persistence]
        CE4[Case Matrix Synthesis]
    end

    subgraph AGENTIC[" AGENTIC RAG ENGINE  agentic_rag_engine.py "]
        AG1[Memory and Cache Lookup]
        AG2[Planner and Router]
        AG3[Retrieval Dispatcher]
        AG4[Synthesiser]
        AG5[Verifier and Reflector]
        AG6[Memory and Cache Update]
    end

    subgraph RETRIEVAL[" RETRIEVAL LAYER "]
        R1[Parametric RAG\nHybrid and Vector Search]
        R2[PageIndex Vectorless\nStatute Tree Retrieval]
        R3[Milvus or Zilliz Stores\nMain and Statute Collections]
    end

    subgraph LLMPROVIDER[" LLM PROVIDER LAYER  client_manager.py "]
        LM1[Groq llama-3.3-70b-versatile\nMain reasoning path]
        LM2[Groq llama-3.1-8b-instant\nSimple fast path]
        LM3[Cerebras llama3.1-70b\nOptional bridge]
        LM4[Key Rotation\nEvery 29 requests or on 429]
    end

    subgraph MEMORY[" MEMORY LAYER  persistent_memory.py "]
        MM1[Short-Term Session Memory\nDisk-backed temp files]
        MM2[Long-Term User Profile]
        MM3[Semantic Answer Cache]
    end

    CLIENTS -->|HTTP POST /api/chat| GW1
    GW1 --> GW2 --> GW3 --> GW4
    GW4 -->|No session| CE1
    GW4 -->|Active session| CE2
    GW3 -->|Blocked| OUT_BLOCK[Direct Safe Response]

    CE1 -->|Simple direct| AG1
    CE1 -->|Needs facts| CE2
    CE2 -->|More questions| CE3
    CE3 -->|Return question| CLIENTS
    CE2 -->|Done| CE4
    CE4 -->|Case matrix| AG1

    AG1 --> MM1
    AG1 --> MM3
    AG1 --> AG2
    AG2 -->|Plan| AG3
    AG3 --> R1
    AG3 --> R2
    R1 --> R3
    AG3 -->|Docs| AG4
    AG4 --> LM1
    AG4 --> LM2
    LM1 --> LM4
    LM2 --> LM4
    LM3 --> LM4
    AG4 -->|Draft answer| AG5
    AG5 -->|Low confidence| AG2
    AG5 -->|Accepted| AG6
    AG6 --> MM1
    AG6 --> MM2
    AG6 --> MM3
    AG6 -->|Final answer| RESP[API Response JSON]
    OUT_BLOCK --> RESP
    RESP -->|HTTP 200| CLIENTS
```

### Block Diagram 2 — End-To-End Runtime Request Trace

Step-by-step trace of a single request from entry to final response.

```mermaid
flowchart TD
    START([fa:fa-user User Sends Message]) --> S1

    subgraph STEP1[" STEP 1 — Gateway Checks "]
        S1[Receive POST /api/chat]
        S2[Check system warmup status]
        S3[Strip prompt injection fragments]
        S4{Safety or scope violation?}
    end

    subgraph STEP2[" STEP 2 — Routing Decision "]
        S5{Session active in store?}
        S6[Resume clarification session]
        S7[Start new clarification flow]
    end

    subgraph STEP3[" STEP 3 — Clarification Loop "]
        S8{Simple direct question?}
        S9[Return question Q1 to Q5]
        S10[Receive user answer]
        S11{All answers collected?}
        S12[Synthesise case matrix]
    end

    subgraph STEP4[" STEP 4 — Agentic RAG "]
        S13[Load session memory and check cache]
        S14{Cache hit?}
        S15[Return cached answer]
        S16[Build retrieval query\nInject conversation context]
        S17[Plan — search domain, strategy, complexity]
        S18[Retrieve from Parametric RAG or PageIndex]
        S19[Synthesise answer with LLM]
        S20[Verify answer quality and word count]
        S21{Quality acceptable?}
        S22[Refine plan and re-retrieve]
    end

    subgraph STEP5[" STEP 5 — Finalise "]
        S23[Update short-term memory]
        S24[Update long-term profile]
        S25[Update semantic cache]
        S26[Build response payload]
    end

    S1 --> S2 --> S3 --> S4
    S4 -->|Yes — blocked| BLOCK[Return safe refusal message]
    S4 -->|No| S5
    S5 -->|Yes| S6 --> S11
    S5 -->|No| S7 --> S8
    S8 -->|Direct| S13
    S8 -->|Needs facts| S9
    S9 --> S10 --> S11
    S11 -->|No| S9
    S11 -->|Yes| S12 --> S13
    S13 --> S14
    S14 -->|Yes| S15
    S14 -->|No| S16 --> S17 --> S18 --> S19 --> S20 --> S21
    S21 -->|No| S22 --> S18
    S21 -->|Yes| S23 --> S24 --> S25 --> S26
    S26 --> END([fa:fa-reply Return Final Answer])
    S15 --> END
    BLOCK --> END
```

### Block Diagram 3 — Component Dependency Map

Shows which module calls which at runtime.

```mermaid
flowchart LR
    subgraph CORE[" CORE API "]
        API[advanced_rag_api_server.py]
    end

    subgraph ORCH[" ORCHESTRATION "]
        UAR[unified_advanced_rag.py]
        AGE[agentic_rag_engine.py]
        CE[clarification_engine.py]
    end

    subgraph RET[" RETRIEVAL "]
        PRAG[parametric_rag_system.py]
        PIR[pageindex_retriever.py]
        ZILLIZ[(Milvus or Zilliz Cloud)]
        PXCLOUD[(PageIndex Cloud Tree)]
    end

    subgraph MEM[" MEMORY "]
        PM[persistent_memory.py\nShort-term, Long-term, Cache]
        TMPFS[(Temp Dir JSON Files)]
    end

    subgraph LLM[" LLM PROVIDERS "]
        CM[client_manager.py]
        GROQ[Groq API]
        CEREBRAS[Cerebras API]
    end

    API -->|init and route| UAR
    API -->|clarification flow| CE
    UAR -->|run query| AGE
    AGE -->|retrieve docs| PRAG
    AGE -->|statute lookup| PIR
    AGE -->|read and write memory| PM
    AGE -->|LLM calls| CM
    PRAG -->|vector search| ZILLIZ
    PIR -->|tree traversal| PXCLOUD
    PIR -->|fallback| ZILLIZ
    PM -->|persist session| TMPFS
    CM -->|primary| GROQ
    CM -->|optional| CEREBRAS
```

### Detailed Logic

1. Request enters FastAPI.
2. API checks whether the system is still warming up.
3. API strips obvious prompt-injection fragments.
4. API applies direct guardrails:
   - illegal guidance refusal
   - foreign-law out-of-scope rejection
   - fake section detection
5. If the session is already in the clarification loop, the answer is fed into the clarification engine.
6. If no clarification session exists, the clarification engine decides whether the query is:
   - greeting
   - irrelevant or out of domain
   - simple direct knowledge question
   - complex personal consultation requiring five questions
7. For simple direct questions, the agentic engine uses lightweight single-pass retrieval and generation.
8. For complex questions, the clarification engine gathers missing case facts.
9. Once clarification is complete, the final synthesized case matrix is sent into the standard RAG path.
10. The agentic engine retrieves evidence, synthesizes the answer, verifies adequacy, and may refine the plan.
11. The answer is returned, while session memory and semantic cache are updated.

## 5. Retrieval Architecture

### Important Distinction

Parametric RAG is not the vectorless retriever.

- Parametric RAG is parameter-driven retrieval optimization over hybrid and advanced search.
- PageIndex is the vectorless statute retriever.

### Block Diagram 4 — Parametric RAG Retrieval Pipeline

```mermaid
flowchart TD
    subgraph INPUT[" INPUT FROM PLANNER "]
        P1[search_domain]
        P2[keywords]
        P3[sections and cases]
        P4[complexity: simple / medium / complex]
    end

    subgraph BUILD[" QUERY BUILD "]
        QE[Enhanced Query Builder\nCombines domain + keywords + sections]
    end

    subgraph DISPATCH[" RETRIEVAL DISPATCH "]
        CX{Complexity Level?}
        SM[Simple or Medium Path\nDirect Hybrid Search\nDoc count = 2 to 5]
        CP[Complex Path\nMulti-Query Expansion\nHyDE Hypothetical Doc\nRe-ranking\nDoc count = 8]
    end

    subgraph FILTER[" POST RETRIEVAL "]
        DF[Domain Metadata Filter]
        CTX[Build Retrieval Context Block]
    end

    GEN[Generator — LLM Synthesis]

    P1 --> QE
    P2 --> QE
    P3 --> QE
    P4 --> CX
    QE --> CX
    CX -->|simple or medium| SM
    CX -->|complex| CP
    SM --> DF
    CP --> DF
    DF --> CTX --> GEN
```

What parametric retrieval uses:

- vector and hybrid search
- metadata hints
- query enhancement
- reranking
- complexity-based document count

What it does not mean:

- it does not mean the retriever is purely model-memory-based
- it does not mean vectorless retrieval

### Block Diagram 5 — Vectorless PageIndex Statute Retrieval

```mermaid
flowchart TD
    subgraph INGEST[" ONE-TIME INGEST "]
        D1[Statute Documents\nIPC, CrPC, CPC, IT Act, etc.]
        D2[PageIndex Cloud Tree Build\nHierarchy indexed by heading and section]
    end

    subgraph QUERY[" QUERY TIME "]
        Q1[User Statute Query\ne.g. Section 420 IPC]
        Q2[Rank Candidate Statutes\nMatch act names]
        Q3[LLM Tree Navigation\nTraverse headings to find section node]
        Q4[Resolve Relevant Node IDs]
        Q5[Fetch Exact Node Text\nfrom PageIndex API]
    end

    subgraph OUTPUT[" OUTPUT "]
        O1[Statute Context Block\nReturned to Agentic Engine]
        O2[Fallback to Zilliz\nIf PageIndex unavailable]
    end

    D1 --> D2
    Q1 --> Q2 --> Q3 --> Q4 --> Q5
    Q5 --> O1
    Q4 -->|PageIndex down| O2
    O1 --> RAG[RAG Synthesis]
    O2 --> RAG
```

This layer is best for:

- exact section lookups
- act and article navigation
- statute text retrieval
- structured legal documents with headings and hierarchy

### Block Diagram 6 — Retrieval Strategy Comparison

```mermaid
flowchart LR
    subgraph VECTOR[" PARAMETRIC RAG — Vector Path "]
        V1[Query Embedding]
        V2[Cosine Similarity Search\nMilvus or Zilliz]
        V3[Top-K Results]
        V4[Domain Filter and Rerank]
    end

    subgraph TREE[" PAGEINDEX — Vectorless Path "]
        T1[Act and Section Name Match]
        T2[Tree Node Navigation\nNo embeddings, no cosine math]
        T3[Exact Section Text]
    end

    Q[User Query] -->|General legal question\nor case facts| V1
    Q -->|Statute or act lookup\nSection-specific question| T1
    V1 --> V2 --> V3 --> V4 --> GEN[Generator]
    T1 --> T2 --> T3 --> GEN
```

## 6. Clarification And Conversation Design

The clarification loop exists because case-consultation queries are usually underspecified.

Examples that should go direct:

- What is FIR?
- What is anticipatory bail?
- Explain Article 21.

Examples that should trigger clarification:

- I was fired without notice, what can I do?
- My landlord did not return my deposit.
- I was cheated by an online seller.

The clarification engine:

- distinguishes knowledge questions from personal-case questions
- supports Hindi and Romanized Hindi detection for direct informational questions
- stores question-answer history
- asks up to five questions
- synthesizes a structured factual matrix before final legal reasoning

The API persists clarification sessions to disk so session continuity survives request-to-request transitions.

### Block Diagram 7 — Clarification Session State Machine

```mermaid
flowchart TD
    subgraph DETECT[" PHASE 1 — Query Classification "]
        D1[Incoming Query]
        D2{Hindi or Informational\nKeyword Detected?}
        D3[Simple Direct Path]
        D4{Personal Case Markers\nPresent?}
        D5[Clarification Required]
    end

    subgraph LOOP[" PHASE 2 — Question Loop (max 5) "]
        L1[Generate Question 1]
        L2[Receive User Answer]
        L3[Store Q and A Pair]
        L4{More facts needed\nand under Q5?}
        L5[Generate Next Question]
    end

    subgraph SYNTH[" PHASE 3 — Synthesis "]
        S1[Build Structured Case Matrix\nFacts: who, what, when, where, monetary value]
        S2[Pass Matrix to Agentic RAG]
        S3[Delete Session from Store]
    end

    D1 --> D2
    D2 -->|Yes| D3
    D2 -->|No| D4
    D4 -->|No| D3
    D4 -->|Yes| D5 --> L1
    L1 --> L2 --> L3 --> L4
    L4 -->|Yes| L5 --> L2
    L4 -->|No or Q5 reached| S1
    S1 --> S2 --> S3
    D3 --> S2
```

## 7. Memory, Session Continuity, And Cache

Current memory model has three main parts:

1. Short-term session memory
2. Long-term user profile memory
3. Semantic cache

### Short-Term Memory

Used for:

- follow-up questions such as under it, that offence, before arrest, what is the penalty under it
- conversation continuity
- clarification loop continuity

Current implementation detail:

- short-term memory is persisted to the temp directory for session reuse across requests
- this was added to reduce context loss on follow-up turns

### Long-Term Memory

Used for:

- user profile
- legal domain interests
- interaction count
- preference-style personalization

### Semantic Cache

Used for:

- repeated or similar queries
- reducing repeated expensive LLM generation
- returning fast cached answers when safe to do so

The system also avoids returning obviously stale cached stubs by checking for error-like phrases and very short low-value answers.

### Block Diagram 8 — Memory Architecture

```mermaid
flowchart TD
    subgraph STMEM[" SHORT-TERM SESSION MEMORY "]
        ST1[Keyed by session_id]
        ST2[Stores last N message turns]
        ST3[Persisted to temp dir JSON\nSurvives across requests]
        ST4[Used for follow-up context\ne.g. under it, that offence, before arrest]
    end

    subgraph LTMEM[" LONG-TERM USER PROFILE "]
        LT1[Keyed by user_id]
        LT2[Legal domain interests]
        LT3[Interaction count]
        LT4[Preference personalization]
    end

    subgraph CACHE[" SEMANTIC ANSWER CACHE "]
        CA1[Keyed by query hash or embedding]
        CA2[Stores past generated answers]
        CA3[Skips short answers and error responses]
        CA4[Returns cached answer if hit]
    end

    REQ[Incoming Request] --> ST1
    REQ --> CA1
    CA1 -->|Cache hit| RESP[Return Cached Response]
    CA1 -->|Cache miss| AGE[Agentic RAG Engine]
    ST1 --> AGE
    LT1 --> AGE
    AGE -->|After answer| ST2
    AGE -->|After answer| LT1
    AGE -->|After answer| CA2
    ST2 --> ST3
```

## 8. LLMs And Provider Strategy

### Main Model Roles

The current code uses multiple model roles:

- Main high-capability reasoning path: Groq-hosted llama-3.3-70b-versatile
- Fast simple direct path: llama-3.1-8b-instant
- Optional provider bridge: Cerebras llama3.1-70b mapping

### Provider Strategy

Provider manager supports:

- multiple Groq keys
- optional Cerebras key
- provider-aware model mapping
- forced rotation on 429

The GitHub workflow is designed for up to:

- 5 Groq keys
- 1 Cerebras key

The local app settings snapshot currently shows only:

- 1 Groq key
- 1 Cerebras key

That means supported architecture and currently observed environment are not necessarily identical. The code supports more keys than the local app-settings export currently proves.

### Block Diagram 9 — LLM Provider Strategy

```mermaid
flowchart TD
    subgraph QUERY_ROUTER[" QUERY ROUTER "]
        QR1{Simple factual\nor direct query?}
    end

    subgraph FAST[" FAST PATH "]
        FP1[Groq llama-3.1-8b-instant\nLow latency, lower cost]
    end

    subgraph MAIN[" MAIN PATH "]
        MP1[Groq llama-3.3-70b-versatile\nFull reasoning, longer answers]
    end

    subgraph FALLBACK[" FALLBACK BRIDGE "]
        FB1[Cerebras llama3.1-70b\nOptional provider when Groq unavailable]
    end

    subgraph ROTATION[" KEY ROTATION  client_manager.py "]
        KR1[Up to 6 loaded keys\nGROQ_API_KEY through GROQ_API_KEY_5\nCEREBRAS_API_KEY]
        KR2[Rotate every 29 requests]
        KR3[Force rotate immediately on 429]
        KR4[Thread-safe with Lock]
    end

    QR1 -->|Yes| FP1
    QR1 -->|No - complex or consultation| MP1
    MP1 -->|429 or outage| FB1
    FP1 --> KR1
    MP1 --> KR1
    FB1 --> KR1
    KR1 --> KR2
    KR1 --> KR3
    KR1 --> KR4
```

## 9. Resilience And Error Handling

### Built-In Guardrails

Current direct-response guardrails include:

- illegal-guidance refusal
- foreign-law out-of-scope refusal
- fake section reference rejection
- greeting detection

### Warmup Handling

If the RAG system is still loading, the API returns 503 with a warming-up message instead of crashing.

### Rate-Limit Handling

For 429 or provider rate-limit errors, the system uses:

- key rotation
- clarification retry logic
- fallback to direct RAG in some cases
- final 429 only if both primary and fallback paths fail

### Clarification Session Safety

The system now:

- persists clarification state to disk
- reloads persisted state rather than trusting only in-memory worker state
- deletes the session before final synthesis to avoid retry collisions

### Retrieval Graceful Degradation

If PageIndex is unavailable:

- statute retrieval falls back to Zilliz or hybrid retrieval

If advanced retrieval fails:

- parametric retrieval returns an empty or reduced result rather than crashing the full request path

## 10. Deployment Architecture

### Current Hosted Platform

The live backend is deployed on Azure App Service.

Relevant files:

- [startup.sh](startup.sh)
- [deploy.ps1](deploy.ps1)
- [.github/workflows/azure-deploy.yml](.github/workflows/azure-deploy.yml)

### Startup Runtime Shape

Current startup script behavior:

- Oryx extracts the app into a temp runtime directory
- startup script hot-patches selected Python files into the extracted runtime
- startup script clears stale bytecode
- app runs with Gunicorn plus UvicornWorker
- worker count is forced to 1

Why one worker is used:

- to avoid clarification-session inconsistency across multiple workers
- to stay inside low-memory Azure tier limits

Current runtime command:

- Gunicorn
- 1 worker
- Uvicorn worker class
- 600 second timeout

### Block Diagram 10 — Deployment Runtime Architecture

```mermaid
flowchart TD
    subgraph AZURE[" AZURE APP SERVICE  Linux Python 3.11 "]
        subgraph DEPLOY[" DEPLOYMENT SLOT "]
            AW[wwwroot\nZip package from GitHub or deploy.ps1]
        end

        subgraph RUNTIME[" RUNTIME SLOT  Oryx extracted to /tmp/... "]
            HP[startup.sh Hot Patch\nOverwrite key Python files before boot]
            PC[Clear __pycache__ stale bytecode]
            GU[Gunicorn\n-w 1  single worker\n--timeout 600 seconds]
            UV[UvicornWorker\nAsync event loop]
            FA[FastAPI Application\nmain.py or main:app]
        end

        subgraph EXTERNAL[" EXTERNAL DEPENDENCIES "]
            MV[(Milvus or Zilliz Cloud\nMain and Statute vector stores)]
            PX[(PageIndex Cloud\nStatute tree index)]
            GR[Groq API\nLLM inference]
            CB[Cerebras API\nOptional LLM bridge]
        end
    end

    AW --> HP --> PC --> GU --> UV --> FA
    FA --> MV
    FA --> PX
    FA --> GR
    FA --> CB
```

## 11. CI/CD

### GitHub Actions Pipeline

Workflow file:

- [.github/workflows/azure-deploy.yml](.github/workflows/azure-deploy.yml)

Main CI/CD steps:

1. checkout repository
2. set up Python 3.11
3. install dependencies for validation
4. build config/.env from GitHub secrets
5. zip the deployment package while excluding heavy local artifacts
6. log into Azure using service principal credentials
7. set Azure App Settings from secrets
8. deploy zip to Azure Web App
9. run health verification

### Block Diagram 11 — CI/CD Pipeline (GitHub Actions)

```mermaid
flowchart TD
    subgraph TRIGGER[" TRIGGER "]
        T1[Push to main branch]
        T2[Manual workflow_dispatch]
    end

    subgraph BUILD[" BUILD STAGE "]
        B1[Checkout repository]
        B2[Set up Python 3.11]
        B3[Install dependencies for validation]
        B4[Write config/.env from GitHub secrets\nGROQ_API_KEY_1..5, CEREBRAS_API_KEY]
        B5[Zip package\nexclude .venv, __pycache__, tests, node_modules]
    end

    subgraph DEPLOY[" DEPLOY STAGE "]
        D1[az login with AZURE_CREDENTIALS]
        D2[Set Azure App Settings\nfrom GitHub secrets]
        D3[az webapp deploy\nupload zip to Azure]
        D4[Health check GET /api/health\nExpect HTTP 200]
        D5[az logout]
    end

    subgraph AZURE_SIDE[" AZURE SIDE "]
        A1[Oryx extracts zip]
        A2[startup.sh hot patches Python files]
        A3[Gunicorn starts with UvicornWorker]
        A4[App ready - serving traffic]
    end

    T1 --> B1
    T2 --> B1
    B1 --> B2 --> B3 --> B4 --> B5
    B5 --> D1 --> D2 --> D3 --> D4 --> D5
    D3 --> A1 --> A2 --> A3 --> A4
    D4 -->|Pass| SUCCESS[Deploy complete]
    D4 -->|Fail| FAIL[Alert — app did not start]
```

### Manual Deploy Path

There is also a manual Kudu-based deploy tool:

- [deploy.ps1](deploy.ps1)

It uploads selected files directly to Azure and restarts the app. This has been useful for hot fixes without rebuilding the full package.

### Block Diagram 12 — Manual Hot-Patch Deploy (deploy.ps1)

```mermaid
flowchart TD
    subgraph LOCAL[" LOCAL MACHINE "]
        L1[Run deploy.ps1]
        L2[Read KUDU_TOKEN from env]
    end

    subgraph UPLOAD[" KUDU VFS UPLOAD  Bearer token auth "]
        U1[PUT advanced_rag_api_server.py]
        U2[PUT pageindex_retriever.py]
        U3[PUT agentic_rag_engine.py]
        U4[PUT persistent_memory.py]
        U5[PUT unified_advanced_rag.py]
        U6[PUT requirements.txt]
        U7[PUT startup.sh]
    end

    subgraph RESTART[" POST UPLOAD "]
        R1[Delete __pycache__ via Kudu]
        R2[POST /api/restart to Azure]
        R3[Poll health endpoint until HTTP 200]
    end

    L1 --> L2 --> U1
    L2 --> U2
    L2 --> U3
    L2 --> U4
    L2 --> U5
    L2 --> U6
    L2 --> U7
    U1 & U2 & U3 & U4 & U5 & U6 & U7 --> R1 --> R2 --> R3
```

## 12. Capacity And Throughput Analysis

### Important Limitation

The current production deployment is intentionally conservative.

Key runtime facts:

- single Gunicorn worker
- one Azure App Service instance
- long-running external LLM calls
- multiple retrieval and verification steps for harder queries
- clarification flows that can span several requests

So the current system is best described as a small-beta or controlled-load deployment, not a high-scale public deployment.

### Throughput From Measured Benchmarks

Observed averages from recent live benchmarks:

- mixed chatbot benchmark average latency: about 3.3 seconds per request
- context-retention benchmark average latency: about 3.2 seconds per request
- ground-truth legal QA benchmark average latency: about 11.0 seconds per request
- full clarification-loop benchmark average per turn: much higher, with final synthesis around 17 to 20 seconds

### Practical Request Capacity

Rough serial request throughput, if the system handled one request at a time:

- at 3.3 seconds average: about 18 requests per minute
- at 11 seconds average: about 5 requests per minute

Because Uvicorn can overlap some network waiting, real throughput can be somewhat better than pure serial math, but the single-worker design still makes the deployment strongly constrained.

### Practical User Capacity Estimate

For the current single-worker Azure setup, realistic rough guidance is:

- simple FAQ style traffic: around 10 to 18 requests per minute total
- mixed real traffic: around 5 to 12 requests per minute total
- clarification-heavy legal consultations: around 2 to 6 requests per minute total

In active-user terms, the current live deployment is most safely treated as:

- around 5 to 15 light active users if they ask occasional direct questions
- around 2 to 5 active users if they are doing long multi-turn case consultations at the same time

This is an estimate, not a guaranteed SLA.

### LLM-Key Rotation Capacity

The provider manager rotates after 29 requests per key.

If fully configured as the CI workflow intends, the code can use up to 6 loaded keys.

That gives a theoretical rotation envelope of:

- 29 times 6 = 174 provider calls before cycling through the full loaded-key pool

But this is not the same as 174 user requests, because:

- one user request may trigger multiple LLM calls
- clarification turns call the model again
- plan and verify loops can create extra calls
- the app server itself is still the stronger bottleneck today

### Bottom Line On Capacity

The current hard bottleneck is more the application runtime shape than the model-key pool.

The biggest concurrency constraints are:

- single Gunicorn worker
- long upstream model latency
- Azure App Service cold starts and low-tier performance
- complex consultations using multiple LLM and retrieval steps

## 13. Error And Resilience Flow

### Block Diagram 13 — Error Handling Decision Tree

```mermaid
flowchart TD
    REQ[Incoming Request] --> WU{System warmed up?}
    WU -->|No| E503[Return 503 warming up]
    WU -->|Yes| GRD{Guardrail triggered?}
    GRD -->|Illegal guidance| EILL[Return refusal — cannot advise illegal acts]
    GRD -->|Foreign law| EFOR[Return OOS — only Indian law]
    GRD -->|Fake section| ESEC[Return clarification — section not found]
    GRD -->|None| RAG[Run RAG pipeline]

    RAG --> LLM{LLM call succeeds?}
    LLM -->|Yes| ANSW[Return answer]
    LLM -->|429 rate limit| ROT{More keys available?}
    ROT -->|Yes| ROTK[Rotate key and retry]
    ROTK --> LLM
    ROT -->|No| FALLB{Direct RAG fallback?}
    FALLB -->|Yes| DFALL[Run direct RAG without agentic loop]
    DFALL --> ANSW
    FALLB -->|No| E429[Return 429 — rate limit]

    RAG --> RET{Retrieval succeeds?}
    RET -->|Yes| LLM
    RET -->|PageIndex down| RETFB[Fallback to Zilliz retrieval]
    RETFB --> LLM
    RET -->|Zilliz down| RETE[Return partial answer with disclaimer]

    RAG --> TOUT{Timeout exceeded?}
    TOUT -->|Yes| E504[Return 504 timeout]
    TOUT -->|No| RET
```

## 14. Conditions Under Which Request Errors Can Still Happen

### Low-Risk, Already Mitigated

- upstream 429 from Groq during clarification
- stale in-memory clarification state
- fake legal section hallucination prompts
- illegal guidance prompts
- foreign-law requests

### Still Possible

1. Cold start or warmup 503
2. Azure restart during active traffic
3. upstream provider outage beyond retry or fallback logic
4. low-memory or long-tail timeout behavior under sustained traffic
5. missing environment variables after deployment
6. PageIndex disabled or not indexed
7. retrieval-store connectivity failures
8. long-request backlog due to single-worker deployment

### Most Likely Real-World Failure Modes On Current Setup

- burst traffic causes queueing and user-perceived slowness
- cold starts return temporary 503 during initialization
- clarification-heavy traffic raises tail latency sharply
- upstream model limits increase fallback frequency

## 15. What To Change If You Need Higher User Volume

If the goal is to support materially more users per minute, the best next steps are:

1. Move off the current low-tier single-worker shape to at least a Basic or Standard Azure plan.
2. Separate clarification-session state into Redis or a proper shared store.
3. Increase worker count after session state is externalized.
4. Keep simple direct path aggressive for factual questions.
5. Add queueing or backpressure for long consultation requests.
6. Add request metrics and P95 latency monitoring.
7. Make sure all intended Groq keys are actually present in the live environment.
8. Keep PageIndex for exact statute traffic so statute lookup load stays efficient.

## 16. Final Assessment

Current system strengths:

- strong routing quality
- full clarification loop working live
- memory continuity mostly strong
- direct-answer speed much better for simple questions
- good guardrails for safety and invalid legal references
- graceful degradation paths exist for several failure modes

Current system limits:

- deployment is not horizontally scalable yet
- single-worker runtime is the main throughput bottleneck
- long complex legal consultations still carry high latency
- broader context retention is strong but not yet perfect

Best single-sentence summary:

LAW-GPT is a hybrid agentic legal AI platform for Indian law that combines routed LLM reasoning, vector and hybrid retrieval, vectorless statute tree search, session memory, and a five-question consultation flow, but its current Azure deployment is optimized for correctness and controlled traffic rather than high-scale concurrency.
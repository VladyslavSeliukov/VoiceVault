# 🎙️ VoiceVault: AI-Native Note Taker

An event-driven backend that turns voice into structured knowledge and solving Message
Delivery Reliability, Multi-Store Consistency, and Semantic Retrieval.

---

## 🛠 Tech Stack

* **Backend**: Python 3.12, FastAPI, Pydantic v2
* **Database**: PostgreSQL 16 (Async SQLAlchemy 2.0 + raw SQL via psycopg3 for
  performance-critical queries)
* **Vector Search**: Qdrant
* **Caching & Idempotency**: Redis 8
* **Message Broker**: RabbitMQ (DLX, Manual ACKs)
* **Background Jobs**: Taskiq (taskiq-aio-pika)
* **Infra & DevOps**: Docker Compose, GitHub Actions (CI/CD)
* **Observability**: Prometheus, Grafana
* **AI / ML**: whisper.cpp (Local STT), Qwen 3.5 (Local LLM), Qdrant (Embeddings)

---

## 🧠 Architecture Deep Dive

### 1. Guaranteed Delivery & Fault Tolerance

* **Problem**: ML model inference (Whisper/Qwen) is resource-heavy. OOM kills, LLM
  timeouts, or API crashes cause silent message drops in background tasks.
* **Solution**: Implemented **Dead Letter Exchanges (DLX)** in RabbitMQ and enforced *
  *Manual Acknowledgments**. The Taskiq worker sends an ACK *only* after the Markdown
  file is physically written to the Obsidian volume and committed to PostgreSQL. Failed
  tasks (e.g., malformed LLM responses after retries) are automatically routed to a DLQ
  for manual inspection or exponential backoff retries.

### 2. Idempotency Layer

* **Problem**: Message brokers provide *at-least-once* delivery. A worker crash after a
  successful Obsidian write but before the RabbitMQ ACK would cause the message to be
  redelivered, triggering the entire ML pipeline again and duplicating the note.
* **Solution**: Implemented an idempotency check using Redis. The system hashes the
  incoming audio payload. If the hash exists (O(1) lookup), the redelivered message is
  instantly acknowledged and dropped, completely preventing duplicate file writes.

### 3. Distributed State Reconciliation (Postgres vs. Qdrant)

* **Problem**: System state is split. Note metadata lives in PostgreSQL (Source of
  Truth), while embeddings live in Qdrant. There is no shared transaction between the
  two stores.
* **Solution**: Vectorization is decoupled into a separate downstream task triggered
  *only* after the Postgres commit succeeds. If Qdrant goes down, the note still safely
  exists in Postgres and Obsidian (fail loud into DLQ, no data loss, RAG is just
  temporarily degraded). A periodic **Reconciliation Job** scans for Postgres notes
  without matching Qdrant vectors and re-enqueues them, healing any state drift.

### 4. Smart Debouncing & LLM Output Validation

* **Thought Fragmentation**: Incoming voice messages trigger a 5-minute rolling debounce
  window in Redis. New messages within the window extend the session, allowing multiple
  thoughts to be merged into a single cohesive note rather than fragmenting context.
* **LLM Hallucinations**: Local models occasionally return malformed JSON. The Qwen
  output is strictly validated through **Pydantic v2** models before any disk I/O
  occurs, ensuring that only perfectly formatted metadata, tags, and action items reach
  the Obsidian vault.

---

### 🏗 Implementation Roadmap

<div align="center">

`VoiceVault v1.0.0`

</div>

- [x] **Phase 1: Skeleton.** Receive voice messages via `aiogram` and save them locally
  to disk. No ML or message brokers involved.
- [x] **Phase 2: STT Integration.** Forward audio to local `whisper.cpp` via HTTP and
  print the raw transcript to the console.
- [x] **Phase 3: LLM Structuring.** Send the transcript to Qwen, generate JSON, and
  enforce strict schema validation using `Pydantic v2`.
- [x] **Phase 3.1: Dual-Storage Routing.** Update the Obsidian service to save the
  raw transcript to an `Inbox` directory and the LLM-generated summary to a
  `Processed` directory. Inject a bidirectional Obsidian link (`[[raw_filename]]`)
  into the summary note for traceability.
- [x] **Phase 4: Synchronous MVP.** Construct a `.md` file with YAML frontmatter and
  write it directly to the Obsidian Volume.
- [x] **Phase 5: Long-Tail Debounce & Manual Flush.** Introduce Redis for batching.
  Implement a 1-hour silence timer to merge spaced-out thoughts into a single context,
  plus an inline button for immediate manual flush when switching topics.
- [x] **Phase 6: RabbitMQ & Taskiq.** Isolate heavy ML processing into asynchronous
  workers. Implement **Manual ACKs** (message is acknowledged *only* after a successful
  physical disk write).
- [x] **Phase 7: Idempotency Layer.** Hash incoming audio payloads in Redis to strictly
  prevent duplicate notes during message redeliveries (at-least-once delivery
  protection).
- [x] **Phase 8: Dead Letter Exchange (DLX).** Route continuously failing tasks (e.g.,
  LLM timeouts, Whisper OOMs) to a DLQ instead of blocking the main queue with infinite
  retries.
- [x] **Phase 9: Vectorization.** Add an independent downstream task to generate
  embeddings for completed notes and store them in Qdrant (linked via PostgreSQL IDs).
    - [x] **Phase 9.1: Dynamic Taxonomy & Tag Management.** Introduce PostgreSQL tables
      to store custom predefined tags. Add Telegram commands to manage this list
      dynamically. Update the LLM system prompt to fetch and enforce these allowed
      topics during classification.
- [x] **Phase 10: RAG Mode.** Implement `/rag` command handling: embed the user's
  question, execute vector search in Qdrant, retrieve full text from Postgres, and
  generate context-aware answers via Qwen.
- [x] **Phase 11: Technical Debt Resolution.** Fast-paced development naturally leaves
  behind technical debt. This phase is dedicated to stabilizing the core architecture
  and preparing the system for production.
    - [x] **Phase 11.1: Comprehensive Review & Refactoring.** Conduct a full project
      audit. Eliminate dead code, unify code conventions, optimize imports, and ensure
      strict type hinting and modular isolation across all services.
        - [x] **11.1.1: Docstring Standardization.**
        - [x] **11.1.2: AI Service Request Timeouts.**
        - [x] **11.1.3: Propper Logging.**
        - [x] **11.1.4: Global Error Handling.**
        - [x] **11.1.5: Docker Configuration & Environment Separation** (Production
          vs. Override profiles, port binding review, `depends_on` strictness).
        - [x] **11.1.6: CI/CD Pipeline Enhancements.**
    - [x] Phase 11.2: Telegram UI & Architecture Refactoring. This phase focuses on
      decoupling the presentation layer from the core business logic. It
      establishes strict domain boundaries by centralizing Telegram routing and
      standardizing
      UI rendering to ensure a stable, maintainable interface.
        - [x] **11.2.1: UI Formatting & Template Extraction.** Configured a global HTML
          ParseMode and implemented Markdown-to-HTML converters for LLM outputs.
          Extracted
          hardcoded UI strings into a centralized template layer to prevent raw markup
          leaks.
        - [x] **11.2.2: Architectural Consolidation (Handlers).** Migrate the legacy
          `basic/handlers.py` into the unified `telegram/handlers` directory. This
          establishes a single source of truth for all Telegram routing and
          interactions.
    - [x] **Phase 12: Prometheus and Grafana**
    - [ ] **Phase 13: End-to-End Testing.** Implement unit and integration tests on
      the stabilized codebase. Validate RabbitMQ queue reliability, database
      transactions, LLM fallback mechanisms, and Telegram UI consistency under load.
        - [x] **Phase 13.1:** Fixed task retry mechanism (implemented Taskiq
          RetryMiddleware and fixed idempotency lock behavior).
        - [ ] **Phase 13.2:** TODO Resolution & Codebase Cleanup

<div align="center">

`VoiceVault v2.0.0`

</div>

- [ ] **Phase 14: Backlog & Future Enhancements.** Additional features and architectural
  improvements conceptualized during the core development phases. These were
  deliberately postponed to maintain initial delivery timelines and prevent scope creep.
    - [ ] **Phase 14.1: Adaptive Index Synchronization (Exponential Backoff).**
      Dynamically adjust the interval for scanning and indexing the Obsidian vault based
      on user activity. Functionally, if no notes are modified, the system increases the
      delay between checks (e.g., from 15m to 30m, then 1h) to conserve resources.
      Technically, this requires storing the "last modified state" in Redis/PostgreSQL
      and implementing stateful evaluation logic within the Taskiq worker to gracefully
      bypass the fixed cron schedule, effectively simulating dynamic jitter without
      maintaining a heavy real-time watchdog daemon.
    - [ ] **Phase 14.2: Scale-to-Zero Local Model Management.** Implement a
      resource-aware middleware to manage memory-intensive local AI models (STT,
      Embeddings). The system will dynamically load models into RAM upon receiving a
      request and automatically unload them after a configured idle timeout. This
      prevents background memory monopolization on the host working machine, effectively
      mimicking the auto-unload behavior of tools like LM Studio/Ollama for isolated
      processes like Whisper.
    - [ ] **Phase 14.3: AI Provider Routing Middleware.** Implement a routing layer to
      dynamically switch between local AI providers based on model architecture.
      Functionally, route MLX model requests to LM Studio and GGUF/Embedding requests
      to Ollama. Technically, this involves abstracting the LLM client interface and
      configuring environment-based routing rules.
    - [ ] **Phase 14.4: Telegram UI: Strict Message Replacement.** Refactor the
      inline keyboard handling. Replace `edit_message` operations with a strict
      "delete and send new" (maybe, implement dedicated function for this) pattern
      to prevent Telegram API state mismatches and UI inconsistencies during rapid user
      interactions.
    - [ ] **Phase 14.5: Telegram UI: Clean Queue Notifications.** Remove redundant
      reply keyboards from the initial "added to queue" notification messages. This
      keeps the chat history visually clean and prevents accidental duplicate task
      submissions while the user waits for processing.
    - [ ] **Phase 14.6: Architectural Isolation: AI Module.** Extract all LLM
      generation, prompting, and vector embedding logic into a dedicated, isolated
      `ai` directory to strictly separate ML infrastructure from business logic.
    - [ ] **Phase 14.8: Scheduled Task Jitter.** Introduce randomized delay intervals
      (jitter) to cron jobs and retry mechanisms. This prevents thundering herd
      problems, smoothing out CPU spikes when multiple scheduled tasks attempt to
      hit the local AI services simultaneously.
    - [ ] **Phase 14.9: Text Message Processing Pipeline.** Expand the bot's input
      capabilities by adding a dedicated pipeline for standard text messages. This
      routes text directly to the AI formatting and vectorization queues, bypassing
      the Whisper STT middleware entirely.
    - [ ] **Phase 14.10: Centralized Exception Registry.** Create a comprehensive
      `exceptions.py` module containing custom, domain-specific exception classes.
      This enforces strict typing, robust error handling, and precise routing within
      the Taskiq workers.
    - [ ] **Phase 14.11: Nightly Vault Analysis Mode.** Implement a scheduled batch
      processing job for off-peak hours. This agentic routine will thoroughly analyze
      the Obsidian vault, map connections between notes, and generate daily insights
      without impacting active daytime hardware resources.
    - [ ] **Phase 14.12: Small-to-Big RAG Retrieval.** Upgrade the vector search
      architecture to implement the "Small-to-Big" retrieval pattern. The system will
      perform semantic searches exclusively against the highly structured, semantically
      dense `Processed` notes to maximize retrieval precision. Once the most relevant
      summaries are identified, the pipeline will dynamically resolve their `source`
      YAML frontmatter links to fetch the corresponding `RAW` transcripts, feeding the
      LLM the complete, uncompressed context for highly detailed answer generation.
    - [ ] **Phase 14.13: Global Fallback Handler.** Implement a catch-all routing
      mechanism at the base of the dispatcher hierarchy (`unhandled_message_fallback`).
      Previously, the bot silently ignored unrecognized inputs — such as arbitrary text,
      typos in commands — leaving the user without clear feedback. This handler ensures
      the system gracefully catches all unhandled updates and explicitly guides the user
      back to supported interaction formats.

<div align="center">

`VoiceVault v2.0.0`

</div>

---

## 💻 Getting Started

**Run Locally**

```bash
git clone https://github.com/VladyslavSeliukov/VoiceVault.git
cd voicevault

# Start the local Whisper server for STT processing
bash scripts/run_whisper.sh

# Start infrastructure (Postgres, RabbitMQ, Redis, Qdrant) and App
docker compose up --build -d

# Run DB Migrations
docker compose exec backend alembic upgrade head

```

* **API Docs (Swagger)**: `http://localhost:8000/docs`
* **Run Tests**: `uv run pytest`

---

## 📬 Contact

**Vladyslav Seliukov** - Python Backend & AI Infrastructure Engineer

* LinkedIn Profile
* seliukovvladyslav@gmail.com

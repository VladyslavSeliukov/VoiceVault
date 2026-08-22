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

### 🏗 Implementation Roadmap

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
- [ ] **Phase 10: RAG Mode.** Implement `/rag` command handling: embed the user's
  question, execute vector search in Qdrant, retrieve full text from Postgres, and
  generate context-aware answers via Qwen.
- [ ] **Phase 11: Technical Debt Resolution.** Fast-paced development naturally leaves
  behind technical debt. This phase is dedicated to stabilizing the core architecture
  and preparing the system for production.
    - [ ] **Phase 11.1: Comprehensive Review & Refactoring.** Conduct a full project
      audit. Eliminate dead code, unify code conventions, optimize imports, and ensure
      strict type hinting and modular isolation across all services.
        - докстринг
        - таймауты на ии вызовах
        - логирование
        - обработку ошибок
        - в целом посмотреть докер компоуз, чекнуть depends_on, закрыть порты и открыть
          в овверрайде (короче, сделать прям здравый прод и овверрдайд для разработки и
          обычный для прода)
        - может добавить что-то в ci cd
    - [ ] **Phase 11.2: End-to-End Testing.** Implement unit and integration tests on
      the stabilized codebase. Validate RabbitMQ queue reliability, database
      transactions, LLM fallback mechanisms, and Telegram UI consistency under load.
- [ ] **Phase 12: Backlog & Future Enhancements.** Additional features and architectural
  improvements conceptualized during the core development phases. These were
  deliberately postponed to maintain initial delivery timelines and prevent scope creep.
    - [ ] **Phase 12.1: Adaptive Index Synchronization (Exponential Backoff).**
      Dynamically adjust the interval for scanning and indexing the Obsidian vault based
      on user activity. Functionally, if no notes are modified, the system increases the
      delay between checks (e.g., from 15m to 30m, then 1h) to conserve resources.
      Technically, this requires storing the "last modified state" in Redis/PostgreSQL
      and implementing stateful evaluation logic within the Taskiq worker to gracefully
      bypass the fixed cron schedule, effectively simulating dynamic jitter without
      maintaining a heavy real-time watchdog daemon.
    - [ ] **Phase 12.2: Scale-to-Zero Local Model Management.** Implement a
      resource-aware middleware to manage memory-intensive local AI models (STT,
      Embeddings). The system will dynamically load models into RAM upon receiving a
      request and automatically unload them after a configured idle timeout. This
      prevents background memory monopolization on the host working machine, effectively
      mimicking the auto-unload behavior of tools like LM Studio/Ollama for isolated
      processes like Whisper.
    - добавить прослойку для выбора lm студио (для mlx моделей) и олама (для gguf и
      эмбедингов)
    - убрать изменения клавиатуры. только удаление и новое сообщение
    - убрать клавиатуру из первого собщения о очереди
    - сделать папку ai под ллм и эмбединги
    - перенести basic/handlers.py к другим хендлерам тг
    - jitler
    - поддержка текстовых сообщений
    - сделать полноценный exceptions.py
    - режим ночного анализа

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

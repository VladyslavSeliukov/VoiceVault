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
- [ ] **Phase 3: LLM Structuring.** Send the transcript to Qwen, generate JSON, and
  enforce strict schema validation using `Pydantic v2`.
- [ ] **Phase 3.1: Dual-Storage Routing.** Update the Obsidian service to save the
  raw transcript to an `Inbox` directory and the LLM-generated summary to a
  `Processed` directory. Inject a bidirectional Obsidian link (`[[raw_filename]]`)
  into the summary note for traceability.
- [x] **Phase 4: Synchronous MVP.** Construct a `.md` file with YAML frontmatter and
  write it directly to the Obsidian Volume.
- [ ] **Phase 5: Long-Tail Debounce & Manual Flush.** Introduce Redis for batching.
  Implement a 1-hour silence timer to merge spaced-out thoughts into a single context,
  plus an inline button for immediate manual flush when switching topics.
- [ ] **Phase 6: RabbitMQ & Taskiq.** Isolate heavy ML processing into asynchronous
  workers. Implement **Manual ACKs** (message is acknowledged *only* after a successful
  physical disk write).
- [ ] **Phase 7: Idempotency Layer.** Hash incoming audio payloads in Redis to strictly
  prevent duplicate notes during message redeliveries (at-least-once delivery
  protection).
- [ ] **Phase 8: Dead Letter Exchange (DLX).** Route continuously failing tasks (e.g.,
  LLM timeouts, Whisper OOMs) to a DLQ instead of blocking the main queue with infinite
  retries.
- [ ] **Phase 9: Vectorization.** Add an independent downstream task to generate
  embeddings for completed notes and store them in Qdrant (linked via PostgreSQL IDs).
- [ ] **Phase 10: RAG Mode.** Implement `/rag` command handling: embed the user's
  question, execute vector search in Qdrant, retrieve full text from Postgres, and
  generate context-aware answers via Qwen.

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

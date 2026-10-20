# SlothDesk AI 🦥

> **"Let your AI do the boring stuff. You take it slow."**

SlothDesk AI is a local-first, privacy-preserving AI productivity agent built for **Hacktoberfest 2026 DEV Challenge Week 3: "Slow and Steady"**. It helps students, developers, and researchers tame messy downloads, disorganized assignments, screenshots, and scattered research PDFs—without cloud subscriptions, without remote telemetry, and without risking accidental file loss.

---

## 🌟 Hacktoberfest 2026: Why "Slow and Steady"?

Modern desktop productivity is often hijacked by frantic hype and rushed tools that blindly upload private documents to third-party cloud APIs. 

**SlothDesk AI embraces the "Slow and Steady" ethos:**
1. **Take It Slow**: Let local AI do the repetitive sorting, categorizing, and renaming while you enjoy your coffee.
2. **Steady and Safe**: Unlike reckless automated scripts, SlothDesk uses a **strict, human-in-the-loop action pipeline**:
   - Files are scanned within explicitly approved boundaries.
   - Proposed changes are presented in an editable review queue.
   - Files are never automatically deleted or overwritten.
   - Every completed move is recorded in SQLite with **1-click verified Undo**.
3. **Open-Weight Independence**: Runs locally via **Gemma 2B** on **Ollama**. Once the open weights are on your drive, SlothDesk operates 100% offline with zero external cloud dependencies.

---

## 📸 Screenshots & UI Preview

*Interactive views featuring warm cream (`#FAF8F2`), forest green (`#1B3B2B`), and sage tones:*

| View | Description | Preview Placeholder |
|---|---|---|
| **Overview Dashboard** | Files scanned, pending suggestions, actions completed, estimated time saved, and the "Lazy Morning Brief". | `[Screenshot Placeholder: Dashboard with metrics and Lazy Morning Brief]` |
| **File Organizer** | Directory scanner with safe recursive traversal and bounded preview drawer. | `[Screenshot Placeholder: Discovered files table with type icons & snippet modal]` |
| **Review & Approval Queue** | Interactive action plan with inline filename editing, category pickers, and safety checks modal. | `[Screenshot Placeholder: Action plan queue with Gemma AI attribution pills]` |
| **Activity History & Undo** | Persistent SQLite audit log with instant one-click verified undo. | `[Screenshot Placeholder: Audit log with executed and undone statuses]` |
| **Settings & AI Diagnostics** | Ollama health monitor, copyable setup guides, and live benchmark evaluation report. | `[Screenshot Placeholder: Live evaluation harness showing 80%+ accuracy and sub-millisecond latencies]` |

---

## 🏗️ Architecture & Pipeline

SlothDesk AI couples a reactive, accessible React 19 frontend with a hardened FastAPI backend running local Gemma inference and a verified SQLite audit pipeline.

```mermaid
flowchart TD
    subgraph UI["Frontend (React 19 + Vite + Tailwind CSS)"]
        A[Dashboard / Overview] --> B[File Organizer & Scanner]
        B --> C[Review & Approval Queue]
        C --> D[Activity History & Undo]
        E[Settings & Benchmark Runner]
    end

    subgraph API["Backend (FastAPI + Python 3.12/3.14)"]
        F["/api/scan (Recursive Bounded Scanner)"]
        G["/api/suggestions (Inference Router)"]
        H["/api/execute (Safe Atomic Organizer)"]
        I["/api/undo (Filesystem Reversal Engine)"]
        J["/api/summary (Lazy Morning Brief)"]
        K["/api/evaluate (Accuracy Benchmark)"]
    end

    subgraph AI["Local Inference Engine"]
        L["Ollama HTTP API (localhost:11434)"]
        M["Google Gemma 2B Open Weights"]
        N["Deterministic Rule Classifier (Safe Offline Fallback)"]
    end

    subgraph Storage["Local Storage & Filesystem"]
        O[("SQLite (Audit Log & Sessions)")]
        P["User Target Directory (Strictly Contained)"]
    end

    B -->|Scan Request| F
    F -->|Discovered Metadata| B
    B -->|Generate Plan| G
    G -->|Query Model| L
    L -->|Inference| M
    L -.->|If Ollama Unavailable| N
    G -->|JSON Suggestions| C
    C -->|Approved Batch| H
    H -->|Atomic Move / Unique Name| P
    H -->|Log Operation| O
    D -->|Request Undo| I
    I -->|Verify & Reverse Move| P
    I -->|Update Status| O
```

---

## 🛠️ Technology Stack

- **Frontend**:
  - React 19 + Vite 8
  - Tailwind CSS v4
  - Lucide Icons
  - Responsive layout (Warm cream `#FAF8F2`, Deep forest green `#1B3B2B`, Muted sage `#4A6E59`)
- **Backend**:
  - Python 3.10 - 3.14 compatible
  - FastAPI (REST API with auto-generated OpenAPI docs)
  - Pydantic v2 (Strict schema validation & untrusted input sanitization)
  - SQLite (Persistent audit logs, scan sessions, undo records)
  - Pytest (Automated test suite)
- **Local AI & Open Weights**:
  - Google Gemma 2B (`gemma2:2b`) running locally via Ollama HTTP API
  - Strictly structured JSON output mode
  - Deterministic metadata fallback when Ollama is unavailable
- **Safety & File Processing**:
  - Python `pathlib` & `shutil`
  - Bounded content extraction (text and `pypdf`)
  - Strict directory traversal rejection (`..` blocking and root isolation)
  - Atomic rename with unique numeric suffixes (`_1`, `_2`) to prevent overwriting

---

## 🚀 Quickstart & Installation (Windows & PowerShell)

### Prerequisites
- Python 3.10+ (tested on Python 3.14 on Windows)
- Node.js 18+ (tested on Node v24)
- *(Optional for AI)* [Ollama](https://ollama.com) installed with `gemma2:2b`

### 1. Clone & Set Up Python Environment
```powershell
# In PowerShell:
git clone https://github.com/your-username/slothdesk-ai.git
cd slothdesk-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Set Up Frontend
```powershell
cd frontend
npm install
npm run build
cd ..
```

### 3. (Optional) Run Local Gemma with Ollama
```powershell
# In a separate terminal:
ollama run gemma2:2b
```
*(If Ollama is not running, SlothDesk AI automatically uses its deterministic metadata fallback so all features remain functional!)*

### 4. Launch SlothDesk AI
You can launch the full application with the FastAPI server (which automatically serves the compiled React frontend at `http://127.0.0.1:8000`):

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
```
Open **`http://localhost:8000`** in your browser.

*(For frontend hot-reloading during development, run `npm run dev` in `frontend/` and visit `http://localhost:5173`.)*

---

## 🧪 Testing & Evaluation

### 1. Run Automated Test Suite
SlothDesk AI includes 14 comprehensive automated tests covering path traversal defense, file scanning, schema validation, safe moves, duplicate avoidance, undo recovery, and API endpoints:

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests -v
```

### 2. Run Live Accuracy & Latency Benchmark
SlothDesk includes a reproducible evaluation harness (`backend/evaluator.py`) testing a labeled sample dataset across categories (Study, Documents, Code, Data, Images, Archives):

```powershell
.\venv\Scripts\python.exe backend/evaluator.py
```

**Actual Measured Benchmark Results:**
- **Deterministic Heuristic Fallback**:
  - Accuracy: **80.0%** (8/10 correct)
  - Average Latency: **0.11 ms**
- **Gemma 2B (Local Ollama)**:
  - Accuracy: **90%+**
  - Average Latency: **~400–900 ms** (on local CPU/GPU)

You can also run this benchmark anytime directly from the **Settings & AI Diagnostics** page in the UI!

---

## ☕ The Lazy Morning Brief

Every morning or on-demand, SlothDesk generates a concise activity summary based on real stored SQLite data:
- Files scanned
- Actions completed
- Files needing review
- Errors or conflicts
- **Configurable Estimated Time Saved**:
  $$\text{Time Saved} = N_{\text{executed}} \times 45\text{ seconds}$$
  *(Accounts for manual file inspection, category folder creation, and renaming. The rate is configurable in Settings).*

---

## 🛡️ Security & Privacy Guarantees

1. **Root Containment**: Every file operation verifies that both the source and target resolve strictly within the user-approved folder. Traversal sequences like `../` or symlinks that point outside are rejected.
2. **Zero Overwrite Guarantee**: Existing files are never overwritten. If `report.pdf` exists at the target, SlothDesk safely renames it to `report_1.pdf`.
3. **No Automatic Deletion**: SlothDesk never deletes files automatically.
4. **Untrusted Input Boundaries**: File text extracted from documents is treated strictly as untrusted data within LLM prompts, preventing indirect prompt injection.
5. **Zero Cloud Telemetry**: All operations happen on your local storage. No document snippets, filenames, or metrics leave your device.

---

## 🤝 Contributing

Contributions to SlothDesk AI are welcome under Hacktoberfest guidelines!
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Ensure all backend tests pass (`pytest backend/tests`).
5. Ensure the frontend builds cleanly (`npm run build` in `frontend/`).
6. Push to the branch and open a Pull Request.

---

## 📄 License & Open-Source Recommendation

SlothDesk AI is released under the **MIT License**.

**Rationale**: The MIT License provides maximum freedom for students, researchers, developers, and educational institutions to inspect, run, modify, and integrate SlothDesk AI into their local workflows without proprietary restrictions or royalties, keeping in full alignment with the open-source spirit of Hacktoberfest.

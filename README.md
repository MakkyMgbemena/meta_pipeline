# Meta Pipeline: Unified AI Automation Engine

Meta Pipeline is a high-integrity, multi-agent automation system designed for enterprise data engineering, digital marketing outreach, and automated business operations. It orchestrates a fleet of specialized AI agents to perform complex, multi-step workflows with built-in verification, financial ledgering, and human-in-the-loop (HITL) safety gates.

## 🚀 Application Overview

The system allows enterprises to automate repetitive tasks—from data cleaning and SEO optimization to social media management—while maintaining strict relational integrity and audit trails. It bridges the gap between raw data processing and finalized, delivered outcomes.

---

## 🏗️ Architecture Skeleton

The application follows a modern decoupled architecture, moving from a user-facing dashboard through a centralized brain to a persistent data vault.

### 1. **Frontend: Mission Control (UI)**
*   **Technology:** Streamlit (`app.py`)
*   **Role:** Provides a real-time dashboard for monitoring system metrics, viewing live logs, and manually triggering missions.
*   **Key Features:** File uploads (Briefs, Assets, CSVs), mission status tracking, and HITL approval interface.

### 2. **Backend: Web Engine (API)**
*   **Technology:** FastAPI (`services/fastapi/api.py`)
*   **Role:** Acts as the gateway for all HTTP communications. It translates UI actions into backend mission triggers.
*   **Key Features:** Asynchronous mission execution, background file processing jobs, and secure webhooks for mission delivery.

### 3. **Orchestration: The Brain (`core/orchestrator.py`)**
*   **Technology:** Python logic with LangChain/LangGraph integration.
*   **Role:** The central nervous system. It manages agent registration, resolves mission routing, and handles the stateful execution of task chains.
*   **Key Components:**
    *   **Registry:** Dynamic mapping of task names to specialized Agent classes.
    *   **Mission Switcher:** Resolves the specific sequence of agents (routing chain) based on client-specific configurations in `config.yaml`.
    *   **Pricing Resolver:** Dynamically determines service costs by climbing the priority ladder (Contract -> Registry -> Brief -> Payload).
    *   **HITL Gate:** An optional safety pause that requires human approval before mission finalization.

### 4. **Agent Layer: Specialized Labor (`core/agents/`)**
*   **Technology:** Standardized `UnifiedAgent` base class.
*   **Role:** Discrete units of work. Examples include:
    *   `SmartCleaner`: Normalizes and prepares tabular data.
    *   `SEOAgent`: Conducts metadata and keyword audits.
    *   `SocialMediaAgent`: A hybrid bridge for API-based and headless social media actions.
    *   `VerifierAgent`: A final safety layer that reconciles output bundles.

### 5. **Data Layer: Persistence Vault (`utils/db_manager.py`)**
*   **Technology:** PostgreSQL (hosted on Google Cloud SQL) with SQLAlchemy ORM.
*   **Role:** Maintains the "Source of Truth" for all client records, financial impacts, and mission histories.
*   **Key Tables:**
    *   `ClientRegistry`: Tracks client lifecycle and synchronization status.
    *   `FinancialLedger`: Records every mission's task, status, revenue impact, and evidence (screenshots).

---

## 🔄 Chronological Execution Flow

When a mission is triggered, the system executes the following sequence:

1.  **Trigger:** A request is received via the Dashboard or API (`/run-mission`).
2.  **Context Assembly:** The Orchestrator loads the **Mission Brief** (client goals, industry, platform) and initializes a shared `context` dictionary.
3.  **Routing Resolution:** The `MissionSwitcher` looks up the client's `routing_chain` in `config.yaml`.
    *   *Example Chain:* `SmartCleaner` -> `SEOAgent` -> `LedgerEntry` -> `VerifierAgent`.
4.  **Chain Execution:** The Orchestrator iterates through the chain:
    *   It instantiates the assigned agent for the current step.
    *   The agent performs its specialized logic (e.g., cleaning a CSV or checking a LinkedIn profile).
    *   Results are appended to the mission `context`.
5.  **Failure Detection:** If any agent reports a `failed` status, the chain halts, and the mission is flagged for review.
6.  **Human-In-The-Loop (Optional):** If `hitl` is enabled in `config.yaml`, the mission pauses. An internal alert is sent, and the system waits for a manual "Approve" signal from the UI.
7.  **Narrative Generation:** A built-in AI client (`ai_client`) synthesizes the raw metrics into a human-readable HTML report based on enterprise templates.
8.  **Finalization & Delivery:**
    *   The `finalize_mission` module executes.
    *   A mission report is dispatched via the **Resend Email API**.
    *   "Before" and "After" screenshots are attached as immutable proof of work.
9.  **Persistence:** The mission result and financial revenue are committed to the PostgreSQL `FinancialLedger`.

---

## 🛠️ Key Directories
- `/core`: Orchestration logic and Agent implementations.
- `/services/fastapi`: API routes and Pydantic models.
- `/utils`: Database management, logging, and configuration loaders.
- `/data`: Mission briefs and internal registry snapshots.
- `/reports`: Visual evidence (screenshots) and generated narrative reports.

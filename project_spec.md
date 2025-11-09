# Project Spec: Automated LinkedIn Post Generator

## 1. Overview

This document outlines the specifications for a local application that automates the creation of LinkedIn posts using a multi-agent architecture. The system will handle topic selection, research, strategic content structuring, writing, reviewing, and image generation. The final output for each run will be a text file containing the post and a corresponding PNG image, saved locally.

## 2. Core Objective

To create a robust, automated pipeline that generates high-quality, strategically-sound LinkedIn posts tailored to a user-defined field of expertise. The system should be resilient, auditable, and configurable.

## 3. High-Level Architecture

The application will be orchestrated by a main controller agent that manages a series of specialized sub-agents. Each agent performs a distinct task and passes its output to the next in the chain. The system will use Google's Gemini models for language and image generation tasks.

### 3.1. Language Models (LLMs)

*   **Core Logic & Text Agents:** `Gemini 2.5 Pro`
*   **AI Image Generator Agent:** `gemini-2.5-flash-image-preview`

### 3.2. Agent Personas & System Prompts

The system uses two specialized personas with detailed system prompts defined in `system_prompts.md`:

1.  **The Strategic Content Architect (Prompt Generator Agent):** This persona acts as a prompt engineer whose sole function is to transform raw technical topics into structured, high-quality user prompts. It analyzes the technical input, infers the target audience and their pain points, creates fresh analogies, and structures the content according to a specific template. This agent does NOT write content—it creates the perfect "ingredients" for the Writer Agent.

2.  **The Witty Expert (Writer Agent):** This persona embodies a brilliant professor who hosts a late-night talk show—deeply knowledgeable but allergic to stuffiness. The Witty Expert uses intellectual sparkle, fresh analogies, dry wit, and rhythmic confidence to distill complex topics into delightful, memorable understanding. The persona follows a specific LinkedIn post structure designed for high engagement: scroll-stopping hook, relatable problem, elegant solution, quantifiable impact, simple action, and memorable sign-off.

**System Prompt Reference:** All system prompts, behavioral guidelines, and persona definitions are maintained in `system_prompts.md`. This file must be consulted when implementing the Prompt Generator Agent and Writer Agent to ensure faithful implementation of their intended behaviors.

### 3.3. Agent Definitions

1.  **Orchestrator Agent:** The central controller. It invokes sub-agents in the correct sequence, handles data flow, manages the character count validation loop, and oversees the error handling and retry logic.
2.  **Topic Agent:** Decides the topic for the day. It queries a local database of previously covered topics to ensure variety and can generate new, relevant topic ideas within the user's specified field.
3.  **Research Agent:** Gathers information, data, and relevant articles on the topic provided by the Topic Agent.
4.  **Prompt Generator Agent (Strategic Content Architect):** Transforms the raw technical topic and research into a structured, high-quality user prompt that will be consumed by the Writer Agent. This agent acts as a prompt engineer, not a content writer, creating the perfect "ingredients" for the Writer Agent by inferring the target audience, their core pain points, key metrics/facts with fresh analogies, and framing the solution. The system prompt for this agent is defined in `system_prompts.md` under "The Strategic Content Architect - User Prompt Engineer."
5.  **Strategic Type Agent:** Designs the structure and strategic angle of the post. It queries a specialized memory bank (RAG-enabled vector store) containing the content of "The Tech Audience Accelerator" newsletter to apply proven content strategies.
6.  **Writer Agent (The Witty Expert):** Drafts the LinkedIn post using the "Witty Expert" persona based on the structured prompt from the Prompt Generator Agent and the strategic guidance from the Strategic Type Agent. This agent embodies a brilliant professor who hosts a late-night talk show—deeply knowledgeable but allergic to stuffiness, distilling complex topics into delightful understanding. The persona and writing guidelines are defined in `system_prompts.md` under "The Witty Expert Persona."
7.  **Reviewer Agent:** Proofreads and refines the draft. It performs two distinct passes:
    *   **Pass 1 (Contextual & Sense Check):** Ensures the post is coherent, logical, and aligns with the inputs from the research and strategy agents.
    *   **Pass 2 (Spelling & Grammar):** Corrects spelling mistakes, grammatical errors, and punctuation.
8.  **Image Prompt Generator Agent:** Creates a descriptive text prompt for the AI Image Generator based on the final, reviewed post content.
9.  **AI Image Generator Agent:** Uses the prompt from the Image Prompt Generator to create a relevant image for the post.

## 4. Detailed Workflow & Data Flow

The application will follow a strict, sequential workflow orchestrated by the Orchestrator Agent.

### 4.1. Onboarding & Configuration

*   Upon first run, the application should prompt the user to select their overarching field/industry.
*   Default options should be: "Data Science (Optimizations & Time-Series Analysis)" and "Generative AI & AI Agents".
*   The user's selection will be saved in a configuration file (`config.json`) and used by the Topic Agent.

### 4.2. Run Execution & Artifacts

For each execution, the system must use a hybrid approach for agent communication:

*   **In-Memory Passing:** Agents within a single run will pass Python data objects directly for speed.
*   **Disk Persistence:** For auditability and debugging, the input and output of every agent step MUST be saved to a unique run directory.

#### 4.2.1. Directory Structure

A new directory will be created for each run with the following structure:
```
runs/
└── {YYYY-MM-DD}-{runId}/
    ├── 00_config.json
    ├── 10_topic.json
    ├── 20_research.json
    ├── 25_structured_prompt.json
    ├── 30_strategy.json
    ├── 40_draft.md
    ├── 50_review.json
    ├── 60_final_post.txt
    ├── 70_image_prompt.txt
    ├── 80_image.png
    ├── prompts/
    │   └── ... (LLM prompts for each step)
    └── completions/
        └── ... (LLM responses for each step)
```

### 4.3. Step-by-Step Workflow

1.  **Initialization:** Orchestrator creates the unique run directory.
2.  **Topic Selection:** Orchestrator calls the **Topic Agent**. The agent queries the `topics.db` to avoid recent topics and selects/generates a new one. The output (e.g., `{"topic": "..."}`) is saved to `10_topic.json`.
3.  **Research:** Orchestrator calls the **Research Agent**, passing the selected topic. The agent performs searches and synthesizes findings. The output (e.g., `{"topic": "...", "sources": [...], "summary": "..."}`) is saved to `20_research.json`.
4.  **Prompt Generation:** Orchestrator calls the **Prompt Generator Agent (Strategic Content Architect)**, passing the raw technical topic and research data. This agent transforms the input into a structured prompt that includes: a clear topic title, inferred target audience, the audience's core pain point, key metrics/facts with a fresh analogy, and the simple solution/code snippet framed as an "Aha!" moment. The output (e.g., `{"structured_prompt": "...", "topic_title": "...", "target_audience": "...", "pain_point": "...", "analogy": "...", "solution": "..."}`) is saved to `25_structured_prompt.json`.
5.  **Strategy:** Orchestrator calls the **Strategic Type Agent**, passing the structured prompt and research summary. This agent queries its RAG memory bank and designs a post structure. The output (e.g., `{"structure": "Hook -> Point 1 -> Example -> CTA", "strategic_angle": "..."}`) is saved to `30_strategy.json`.
6.  **Writing:** Orchestrator calls the **Writer Agent (The Witty Expert)**, providing the structured prompt from the Prompt Generator and the strategic guidance from the Strategic Type Agent. The agent writes the first draft using the Witty Expert persona, which is saved to `40_draft.md`.
7.  **Review:** Orchestrator calls the **Reviewer Agent**. It performs its two passes. The output, including any diffs or changes made, is saved to `50_review.json`.
8.  **Character Count Loop:**
    a. Orchestrator runs a Python script to count the characters of the reviewed post.
    b. **If count < 3000:** The post is approved. The final version is saved to `60_final_post.txt`. Proceed to Step 9.
    c. **If count >= 3000:** The post is rejected. The Orchestrator sends the post back to the **Writer Agent** with instructions to shorten it (e.g., `{"target_max": 2950, "current": 3100}`). The loop returns to Step 6 (Writing) and then Step 7 (Review). This loop continues until the post passes the character count validation.
9.  **Image Prompt Generation:** Orchestrator calls the **Image Prompt Generator Agent** with the final post content. The generated prompt is saved to `70_image_prompt.txt`.
10. **Image Generation:** Orchestrator calls the **AI Image Generator Agent** (`gemini-2.5-flash-image-preview`) with the prompt. The resulting image is saved as `80_image.png`.
11. **Completion:** The run is marked as complete.

## 5. Data Persistence & Logging

### 5.1. SQLite Database (`topics.db`)

The application will use a local SQLite database with two main tables:

*   **`previous_topics`**:
    *   `id` (INTEGER, PRIMARY KEY)
    *   `topic_name` (TEXT, NOT NULL)
    *   `date_posted` (TEXT)
*   **`potential_topics`**:
    *   `id` (INTEGER, PRIMARY KEY)
    *   `topic_name` (TEXT, NOT NULL, UNIQUE)
    *   `field` (TEXT, NOT NULL)

### 5.2. Event Logging (`events.jsonl`)

An append-only log file named `events.jsonl` will be maintained at the root of the project. Each line will be a JSON object representing a single event (e.g., an agent call, a retry attempt, an error).
*   **Format:** `{"timestamp": "...", "run_id": "...", "step": "...", "attempt": 1, "status": "ok/error", "error_type": "...", "duration_ms": 1234, "model": "...", "token_usage": {"prompt": ..., "completion": ...}}`

## 6. Error Handling & Resilience

The system must be built with the following robust error-handling policies.

*   **Standard Agent Output:** All agents must return a standardized JSON object:
    ```json
    {
      "status": "ok" | "error",
      "data": { ... },
      "error": {
        "type": "ModelError",
        "message": "...",
        "retryable": true
      },
      "metrics": { ... }
    }
    ```*   **Retry Policy:** Use automatic retries (max 3 attempts) with exponential backoff for `retryable` errors (e.g., `ModelError`, `ExternalAPITimeout`).
*   **Fallback Strategies:**
    *   **Research:** If no data is found, request a new topic from the Topic Agent (max 2 pivots).
    *   **Writer/Reviewer:** If an LLM error persists, attempt a simplified prompt or use a local, non-AI-based grammar check as a last resort.
    *   **Image Prompt:** If generation fails, create a minimal prompt from the post's summary.
*   **Circuit Breaker:** If 3 consecutive LLM calls fail within a single run, abort the run immediately.
*   **Artifact Integrity:** After writing any JSON artifact, the system must immediately read it back to verify it can be parsed. If parsing fails, raise a `CorruptionError` and abort the run.
*   **Failure Logging:** On any run abortion, create a `run_failed.json` file in the run directory detailing the point of failure.

## 7. Technical & Project Specifications

*   **Language:** Python 3.10+
*   **Project Structure:** A modular structure is required:
    ```
    /project-root
    ├── main.py             # Main execution script
    ├── orchestrator.py
    ├── agents/
    │   ├── __init__.py
    │   ├── topic_agent.py
    │   ├── prompt_generator_agent.py
    │   ├── writer_agent.py
    │   └── ... (other agents)
    ├── core/
    │   ├── llm_clients.py
    │   ├── rag_setup.py
    │   └── ...
    ├── database/
    │   └── topics.db
    ├── runs/                 # For run artifacts
    ├── memory_bank/          # Corpus for RAG
    │   └── ... (newsletter .txt files)
    ├── .env
    ├── requirements.txt
    ├── system_prompts.md     # System prompts for agents
    └── project_spec.md
    ```
*   **API Key Management:** API keys for Google AI Studio must be loaded from a `.env` file in the project root and not be hardcoded.
*   **Dependencies:** Key libraries will include `google-generativeai`, `python-dotenv`, `sqlite3`, and a library for RAG/vector embeddings (e.g., `langchain`, `llama-index`, or `chromadb`).
*   **Execution:** The application will initially be triggered via a command-line interface (e.g., `python main.py`). Future development may include scheduling capabilities.
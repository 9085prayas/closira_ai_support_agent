# Closira Stateful AI Support Agent 

A deterministic, strictly-scoped AI customer support agent built for Bloom Aesthetics Clinic. Powered by the Gemini 2.5 Flash model, this application utilizes structured outputs and Pydantic schemas to prevent hallucinations, manage conversational state, and execute a multi-step lead qualification funnel.

## 🎯 Core Features

* **Zero-Hallucination Guardrails:** The agent is rigidly constrained to a JSON-based Standard Operating Procedure (`sop.json`). It will gracefully refuse to answer questions regarding unlisted services or policies.
* **Deterministic Flow Control:** Bypasses standard open-ended text generation by forcing the LLM to return strictly typed JSON objects on every turn, evaluating boolean logic before responding.
* **Automated Lead Qualification:** Silently extracts user data (treatment area, past history, timeline) in the background while asking only one relevant question per turn to avoid overwhelming the customer.
* **Safety Escalation Hooks:** Automatically halts the session and flags for human intervention if the user exhibits anger, asks medical/clinical questions, attempts price negotiation, or triggers a 2-strike "out-of-scope" limit.
* **Post-Session Intelligence:** Automatically synthesizes the raw chat log into a structured business summary (Customer Intent, SOP Gaps, and Next Actions) upon session termination.

---

## 🏗️ Project Architecture

```text
├── data/
│   └── sop.json                 # The immutable source-of-truth for clinic data
├── test_transcripts/            # Auto-generated markdown logs of test scenarios
├── agent.py                     # Core AI logic, Pydantic schemas, and state management
├── main.py                      # Interactive CLI loop for real-time testing
├── test_runner.py               # Automated testing suite to generate transcripts
├── prompt_design.md             # Explanation of prompt engineering decisions
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your system. 

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
# Clone the repo
git clone [https://github.com/yourusername/closira-ai-support-agent.git](https://github.com/yourusername/closira-ai-support-agent.git)
cd closira-ai-support-agent

# Create and activate virtual environment
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Mac/Linux: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your Google Gemini API key:

```env
GEMINI_API_KEY="your_api_key_here"
```

---

## 💻 Usage

### Interactive CLI Testing
To interact with the agent natively in your terminal, run:

```bash
python main.py
```
* Type your questions naturally.
* The agent will guide you through the flow or answer SOP questions.
* Type `exit` to cleanly close the session and generate the final summary report.

### Automated Test Suite
To automatically verify the agent's logic against edge cases and generate the required markdown transcripts, run the test runner:

```bash
python test_runner.py
```
This script will spin up isolated agent instances, feed them specific conversational paths (In-SOP, Out-of-Scope, Escalation Trigger, Lead Qualification), and output the resulting logs into the `test_transcripts/` directory.

---

## 🧠 Technical Trade-offs & Future Work

* **In-Memory State:** Currently, conversational history and lead profiles are stored in the class instance memory. In a production environment, this state would be externalized to a database like Redis to support stateless, horizontal scaling.
* **Synchronous Execution:** The current CLI relies on blocking, synchronous API calls. For deployment as a WhatsApp/SMS webhook, the architecture would be migrated to FastAPI using `asyncio` to handle concurrent inbound messages efficiently.
* **Schema Adaptation:** Due to strict limitations on open-ended dictionaries (`additionalProperties`) in the free tier of the Gemini Developer API, dynamic dictionaries were refactored into strict Key-Value `ExtractedDetail` objects to ensure reliable JSON parsing.
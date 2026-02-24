# Agvisor

## Overview
An AI-powered board of advisors chatbot designed for all types of agricultural businesses. The app provides expert guidance through a customizable advisory board with 5 core advisors and 4 optional specialist positions, using **multi-agent orchestration** where a Board Chair agent routes questions to the most relevant advisors and synthesizes their responses.

## Current State
- Fully functional Flask web application
- **Multi-agent orchestration** with Board Chair coordinating advisors
- AI chatbot integration using OpenAI via Replit AI Integrations
- User profile system for personalized advice (state, business type, business description)
- **Board Chair smart routing** — analyzes questions and selects 2-4 most relevant advisors
- **Board Summary synthesis** — Chair produces actionable summary after advisor responses
- **"Ask All Advisors" toggle** — user can override smart routing when desired
- **Customizable advisory board** with base + optional advisors
- 5 core board members (always active):
  1. **Finance Director** (Ag Economics & Investment)
  2. **Operations Manager** (Ag Operations & Logistics)
  3. **Marketing Specialist** (Sales & Market Development)
  4. **Legal Specialist** (Federal & State Regulations)
  5. **Risk Advisor** (Risk Management & Insurance)
- 4 optional specialists (user selects based on business type):
  1. **Commodity Risk Advisor** (Commodity Markets & Hedging)
  2. **Livestock & Animal Systems Advisor** (Animal Production & Health)
  3. **Sustainability Advisor** (Environmental Stewardship)
  4. **Agronomist** (Crop Science & Soil Health)
- Business-type-specific suggestions for which optional advisors to add
- **Development database** with fake ag business financial data (20 businesses across 4 performance categories)

## Multi-Agent Orchestration Flow
1. User submits a question
2. **Board Chair** analyzes the question and user's business profile
3. Chair selects 2-4 most relevant advisors (smart routing)
4. Selected advisors respond in parallel with their specialized expertise
5. **Board Chair synthesizes** all responses into a concise Board Summary with key recommendations, points of agreement, trade-offs, and next steps
6. UI displays: routing info → advisor responses → board summary

## Database Schema (Development)
PostgreSQL database with fake financial data for testing and development:

### Tables
- **ag_businesses** (20 rows) — Business profiles with performance_category classification
- **income_statements** (100 rows) — 5 years (2021-2025) of P&L data per business
- **balance_sheets** (100 rows) — 5 years of balance sheet data per business
- **cash_flow_statements** (100 rows) — 5 years of cash flow data per business
- **production_records** (75 rows) — 5 years of production data for 15 applicable businesses
- **key_ratios** (100 rows) — Calculated financial ratios from income/balance data

### Performance Categories (5 businesses each)
1. **Excelling** — Strong revenue growth, high margins (18-30%), healthy balance sheets
2. **Trending Upward** — Moderate growth, improving margins, debt being paid down
3. **Trending Downward** — Declining revenue, eroding margins, increasing debt
4. **Failing** — Revenue collapse, negative margins (-10% to -31%), negative equity

## Project Architecture
```
/
├── main.py                  # Flask app, API routes, orchestration logic
├── agents/                  # Agent modules (one file per agent)
│   ├── __init__.py          # Registry of all agents, exports constants
│   ├── base.py              # BaseAdvisor class, shared OpenAI client, training data loader
│   ├── board_chair.py       # Board Chair — routing & synthesis
│   ├── financial.py         # Finance Director agent
│   ├── operations.py        # Operations Manager agent
│   ├── marketing.py         # Marketing Specialist agent
│   ├── legal.py             # Legal Specialist agent (with state-specific logic)
│   ├── risk.py              # Risk Advisor agent
│   ├── commodity_risk.py    # Commodity Risk Advisor agent
│   ├── livestock.py         # Livestock & Animal Systems agent
│   ├── sustainability.py    # Sustainability Advisor agent
│   └── agronomist.py        # Agronomist agent
├── training_data/           # Domain knowledge files loaded into agent system prompts
│   ├── financial.md         # Ag financial benchmarks, ratios, loan programs
│   ├── operations.md        # Equipment, labor, precision ag, supply chain
│   ├── marketing.md         # Ag marketing channels, pricing, digital marketing
│   ├── legal.md             # Federal/state ag regulations, water rights, labor law
│   ├── risk.md              # Insurance programs (MPCI, PRF, LRP), disaster planning
│   ├── commodity_risk.md    # Futures/options, hedging, basis, margin management
│   ├── livestock.md         # Herd management, nutrition, breeding, production benchmarks
│   ├── sustainability.md    # Certifications, carbon credits, conservation programs
│   └── agronomist.md        # Crop science, soil health, IPM, nutrient management
├── templates/
│   └── index.html           # Chat interface frontend with onboarding modal
├── static/
│   └── style.css            # Styling
├── pyproject.toml           # Python dependencies
└── replit.md                # This file
```

## Key Features
- **Multi-agent orchestration** with Board Chair coordinator
- **Smart routing** — Board Chair selects most relevant advisors per question
- **Board Summary** — synthesized recommendations after advisor responses
- **Ask All Advisors** toggle — override smart routing for full board input
- Conversational AI with agricultural expertise
- **Customizable advisory board** — 5 core + up to 4 optional advisors
- **Drag-and-drop advisor management** in sidebar
- **Smart suggestions** — recommends optional advisors based on business type
- User profile system (business name, state, business type, business description) for personalized advice
- **Business records upload** — CSV/spreadsheet upload for data-driven, personalized advice
- Supports all ag business types: farms, equipment dealers, suppliers, processors, ag tech, consultants, cooperatives, and more
- Position titles displayed instead of individual names
- Legal advisor with federal and state-specific agricultural law knowledge
- Conversation history per advisor
- Clean, responsive chat interface with multi-advisor response display
- Profile saved to localStorage for returning users

## Tech Stack
- **Backend**: Python, Flask
- **AI**: OpenAI GPT via Replit AI Integrations (no API key required, charges billed to credits)
- **Architecture**: Multi-agent orchestration (Board Chair + specialist advisors)
- **Database**: PostgreSQL (development data)
- **Frontend**: HTML, CSS, JavaScript

## Running the Application
The app runs on port 5000 using the "Start application" workflow (`python main.py`).

## Recent Changes
- February 24, 2026: Added training data knowledge files for all 9 advisors — curated domain-specific reference content (11K-16K chars each) loaded into system prompts with caching
- February 24, 2026: Refactored to modular agent architecture — each agent in its own Python file under `agents/` directory
- February 24, 2026: Upgraded to multi-agent orchestration — Board Chair routes questions to relevant advisors, synthesizes Board Summary, added "Ask All Advisors" toggle
- February 11, 2026: Created development database with 20 fake ag businesses, 5 years of financial statements, production records, and key ratios across 4 performance categories
- February 11, 2026: Added drag-and-drop for optional advisors in sidebar — drag from "Available Specialists" to add, click X to remove
- February 11, 2026: Added customizable advisory board with 5 base + 4 optional advisors and business-type suggestions
- February 11, 2026: Broadened to support all ag business types (not just livestock/crops)
- January 28, 2026: Added business records upload (CSV/spreadsheet) for data-driven advice
- January 28, 2026: Updated to have all advisors respond to questions by default
- January 28, 2026: Removed individual names, now showing only position titles
- January 28, 2026: Initial creation of the agricultural advisory board chatbot

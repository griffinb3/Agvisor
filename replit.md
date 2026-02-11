# Agvisor

## Overview
An AI-powered board of advisors chatbot designed for all types of agricultural businesses. The app provides expert guidance through a customizable advisory board with 5 core advisors and 4 optional specialist positions, with personalized advice based on user's state, business type, description, and uploaded business records.

## Current State
- Fully functional Flask web application
- AI chatbot integration using OpenAI via Replit AI Integrations
- User profile system for personalized advice (state, business type, business description)
- **All advisors respond to questions by default** (unless user asks for a specific advisor)
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

## Project Architecture
```
/
├── main.py              # Flask application with API endpoints
├── templates/
│   └── index.html       # Chat interface frontend with onboarding modal
├── static/
│   └── style.css        # Styling
├── pyproject.toml       # Python dependencies
└── replit.md            # This file
```

## Key Features
- Conversational AI with agricultural expertise
- **Customizable advisory board** — 5 core + up to 4 optional advisors
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
- **Frontend**: HTML, CSS, JavaScript

## Running the Application
The app runs on port 5000 using the "Start application" workflow (`python main.py`).

## Recent Changes
- February 11, 2026: Added customizable advisory board with 5 base + 4 optional advisors and business-type suggestions
- February 11, 2026: Broadened to support all ag business types (not just livestock/crops)
- January 28, 2026: Added business records upload (CSV/spreadsheet) for data-driven advice
- January 28, 2026: Updated to have all advisors respond to questions by default
- January 28, 2026: Removed individual names, now showing only position titles
- January 28, 2026: Initial creation of the agricultural advisory board chatbot

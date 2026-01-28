# AgriAdvisor Board

## Overview
An AI-powered board of advisors chatbot designed specifically for agricultural businesses. The app provides expert guidance through six specialized AI advisors covering different aspects of farm management, with personalized advice based on user's state, livestock, crops, and uploaded business records.

## Current State
- Fully functional Flask web application
- AI chatbot integration using OpenAI via Replit AI Integrations
- User profile system for personalized advice (state, livestock, and crops)
- **All advisors respond to questions by default** (unless user asks for a specific advisor)
- Six specialized agricultural advisors (position titles only, no individual names):
  1. **Chief Agronomist** (Crop Science & Soil Health)
  2. **Finance Director** (Farm Economics & Investment)
  3. **Operations Manager** (Farm Operations & Logistics)
  4. **Marketing Strategist** (Sales & Market Development)
  5. **Sustainability Advisor** (Environmental Stewardship)
  6. **Legal Specialist** (Federal & State Regulations)

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
- **All advisors respond simultaneously** unless user asks for a specific advisor
- User profile system (farm name, state, livestock, crops) for personalized advice
- **Business records upload** - CSV/spreadsheet upload for data-driven, personalized advice
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
- January 28, 2026: Added business records upload (CSV/spreadsheet) for data-driven advice
- January 28, 2026: Added custom text inputs for typing additional livestock/crops not in the preset list
- January 28, 2026: Updated to have all advisors respond to questions by default
- January 28, 2026: Removed individual names, now showing only position titles
- January 28, 2026: Added livestock options to user profile (16 livestock types)
- January 28, 2026: Added legal advisor and user profile system (state and crops selection)
- January 28, 2026: Initial creation of the agricultural advisory board chatbot

# AgriAdvisor Board

## Overview
An AI-powered board of advisors chatbot designed specifically for agricultural businesses. The app provides expert guidance through six specialized AI advisors covering different aspects of farm management, with personalized advice based on user's state and crops.

## Current State
- Fully functional Flask web application
- AI chatbot integration using OpenAI via Replit AI Integrations
- User profile system for personalized advice (state and crops)
- Six specialized agricultural advisors:
  1. **Dr. Sarah Chen** - Chief Agronomist (Crop Science & Soil Health)
  2. **Marcus Thompson** - Agricultural Finance Director (Farm Economics)
  3. **Elena Rodriguez** - Operations Manager (Farm Logistics)
  4. **James Okonkwo** - Marketing Strategist (Sales & Markets)
  5. **Dr. Amara Patel** - Sustainability Advisor (Environmental Stewardship)
  6. **Robert Mitchell, JD** - Agricultural Law Specialist (Federal & State Regulations)

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
- User profile system (farm name, state, crops) for personalized advice
- Legal advisor with federal and state-specific agricultural law knowledge
- Conversation history per advisor
- Clean, responsive chat interface
- Advisor switching with context preservation
- Profile saved to localStorage for returning users

## Tech Stack
- **Backend**: Python, Flask
- **AI**: OpenAI GPT via Replit AI Integrations (no API key required, charges billed to credits)
- **Frontend**: HTML, CSS, JavaScript

## Running the Application
The app runs on port 5000 using the "Start application" workflow (`python main.py`).

## Recent Changes
- January 28, 2026: Added legal advisor and user profile system (state and crops selection)
- January 28, 2026: Initial creation of the agricultural advisory board chatbot

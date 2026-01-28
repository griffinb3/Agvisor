# AgriAdvisor Board

## Overview
An AI-powered board of advisors chatbot designed specifically for agricultural businesses. The app provides expert guidance through five specialized AI advisors covering different aspects of farm management.

## Current State
- Fully functional Flask web application
- AI chatbot integration using OpenAI via Replit AI Integrations
- Five specialized agricultural advisors:
  1. **Dr. Sarah Chen** - Chief Agronomist (Crop Science & Soil Health)
  2. **Marcus Thompson** - Agricultural Finance Director (Farm Economics)
  3. **Elena Rodriguez** - Operations Manager (Farm Logistics)
  4. **James Okonkwo** - Marketing Strategist (Sales & Markets)
  5. **Dr. Amara Patel** - Sustainability Advisor (Environmental Stewardship)

## Project Architecture
```
/
├── main.py              # Flask application with API endpoints
├── templates/
│   └── index.html       # Chat interface frontend
├── static/
│   └── style.css        # Styling
├── pyproject.toml       # Python dependencies
└── replit.md            # This file
```

## Key Features
- Conversational AI with agricultural expertise
- Conversation history per advisor
- Clean, responsive chat interface
- Advisor switching with context preservation

## Tech Stack
- **Backend**: Python, Flask
- **AI**: OpenAI GPT via Replit AI Integrations (no API key required, charges billed to credits)
- **Frontend**: HTML, CSS, JavaScript

## Running the Application
The app runs on port 5000 using the "Start application" workflow (`python main.py`).

## Recent Changes
- January 28, 2026: Initial creation of the agricultural advisory board chatbot

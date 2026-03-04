# Agvisor

## Overview
Agvisor is an AI-powered chatbot designed to provide expert agricultural guidance through a customizable advisory board. It uses multi-agent orchestration, where a Board Chair AI routes user questions to the most relevant specialist advisors and synthesizes their responses into actionable summaries. The project aims to offer personalized, data-driven advice to various agricultural businesses, leveraging state-specific data, financial analysis, and real-time market information to enhance decision-making and business performance.

## User Preferences
- The agent should prioritize high-level features.
- The agent should remove all changelogs, update logs, and date-wise entries.
- The agent should consolidate redundant information.
- The agent should prioritize architectural decisions over implementation specifics.
- The agent should focus on what's actually integrated in the external dependencies section.
- The agent should maintain a conversational tone with agricultural expertise.
- The agent should limit advisor responses to one paragraph plus two key suggestions for conciseness.

## System Architecture
The Agvisor application is built as a Flask web application utilizing a multi-agent orchestration pattern. A central `Board Chair` agent is responsible for smart routing user questions to 2-4 most relevant specialist advisors from a customizable board of 5 core and 4 optional members. After parallel processing, the `Board Chair` synthesizes these responses into a comprehensive `Board Summary`. Users can override smart routing via an "Ask All Advisors" toggle or directly address specific advisors.

Each advisor's system prompt is dynamically enriched with a robust context pipeline including:
- Curated domain knowledge from `training_data/*.md` files.
- User profile data (business type, state, description).
- Raw data preview and computed financial ratios/trends from uploaded CSV records via a `Financial Analysis Engine`.
- State-specific agricultural data (profiles, regulations, programs, commodities, extension services) from a PostgreSQL database.
- Seasonal agricultural context and deadlines.
- Live commodity prices with a 1-hour cache.
- Relevant document chunks retrieved via a RAG (Retrieval Augmented Generation) system from curated USDA publications and extension guides.

The UI/UX includes a responsive chat interface, an onboarding modal, and a panel for managing `Saved Action Plans`, which allows users to track recommendations. Advisors' responses are displayed concisely.

Key architectural features include:
- **Financial Analysis Engine**: Automatically computes profitability, liquidity, solvency, efficiency ratios, and year-over-year trends from uploaded financial data.
- **Seasonal Calendar Awareness**: Advisors consider current agricultural seasons, upcoming deadlines, and growing season adjustments.
- **Saved Action Plans**: Users can save board summaries as trackable action plans with progress tracking, priorities, and notes.
- **RAG Document Search**: Keyword-based retrieval from a curated set of agricultural reference documents for context enrichment.
- **Customizable Advisory Board**: Allows users to select optional advisors based on their business type, with smart suggestions provided.
- **State & Business Data Layer**: A PostgreSQL database stores comprehensive agricultural reference data (state profiles, regulations, financial programs, commodities, business benchmarks, extension services) that is injected into advisor prompts for personalized advice.

## External Dependencies
- **AI**: OpenAI GPT (via Replit AI Integrations)
- **Database**: PostgreSQL (for state/business reference data, action plans, RAG documents, and development financial data)
- **Commodity Prices**: Yahoo Finance API (for live commodity prices)
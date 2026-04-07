import re
import json
from agents.base import get_openai_client


ROUTING_PROMPT = """You are the Board Chair of an agricultural advisory board. Your role is to analyze incoming questions and determine which advisors on the board are most relevant to respond.

You must return valid JSON only — no other text.

Given the user's question and their business profile, select exactly 5 of the most relevant advisors from the active board to respond. If fewer than 5 are available, select all of them. Consider:
1. Which advisors have direct expertise related to the question
2. The user's business type and how it relates to each advisor's specialty
3. Cross-functional implications (e.g., a land purchase question involves finance, legal, and possibly operations)

Return a JSON object with this exact structure:
{"selected": ["advisor_id_1", "advisor_id_2", "advisor_id_3", "advisor_id_4", "advisor_id_5"], "rationale": "Brief explanation of why these advisors were selected"}

Only select from the active advisor IDs provided. Always select 5 advisors."""

SYNTHESIS_PROMPT = """You are the Board Chair of an agricultural advisory board. Your role is to synthesize advice from multiple expert advisors into one clear, consolidated response for the user.

Write exactly ONE paragraph that weaves together the most important insights from across the board — prioritize, synthesize, and make it actionable. Speak directly to the user in a warm, confident advisory tone. No bullet points, no headers, no numbered lists. Attribute key points to specific advisors by name when it adds clarity (e.g., "As your Financial Advisor noted..."). Be concrete and specific to their situation.

After the paragraph, on a new line starting with '💡', write ONE single key insight or important consideration the user should keep top of mind — the single most pivotal thing from the board's discussion. This should be a standalone sentence, not a repeat of the paragraph. Write it as a direct, punchy statement (e.g., "💡 Your cash reserve is your single biggest lever for surviving a down season.").

At the very end, on a new line starting with '❓', add ONE focused follow-up question only if it would meaningfully sharpen future advice. Skip the question entirely if the response is already complete. Never ask just to fill space."""


class BoardChair:

    @staticmethod
    def route(message, active_advisors, user_profile=None):
        client = get_openai_client()

        advisor_descriptions = []
        for aid, info in active_advisors.items():
            advisor_descriptions.append(f"- {aid}: {info['title']} ({info['specialty']})")
        advisor_list_str = "\n".join(advisor_descriptions)

        context = ""
        if user_profile:
            parts = []
            if user_profile.get('business_name'):
                parts.append(f"Business: {user_profile['business_name']}")
            if user_profile.get('business_type'):
                parts.append(f"Type: {user_profile['business_type']}")
            if user_profile.get('state'):
                parts.append(f"State: {user_profile['state']}")
            if user_profile.get('business_description'):
                parts.append(f"Description: {user_profile['business_description']}")
            if parts:
                context = "\n\nBusiness Profile:\n" + "\n".join(parts)

        user_content = f"""Active advisors on the board:
{advisor_list_str}
{context}

User's question: {message}

Select 5 advisors (or all if fewer than 5 are available) and return JSON only."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ROUTING_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                max_completion_tokens=256
            )

            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)

            result = json.loads(raw)
            selected = [aid for aid in result.get("selected", []) if aid in active_advisors]
            rationale = result.get("rationale", "")

            if len(selected) < 2:
                selected = list(active_advisors.keys())[:5]
                rationale = "Routing to core advisors for broad coverage."

            return selected, rationale
        except Exception:
            selected = list(active_advisors.keys())[:5]
            return selected, "Consulting core advisors for a comprehensive perspective."

    @staticmethod
    def synthesize(message, advisor_responses, user_profile=None):
        client = get_openai_client()

        responses_text = ""
        for resp in advisor_responses:
            responses_text += f"\n\n**{resp['title']}:**\n{resp['response']}"

        context = ""
        if user_profile:
            parts = []
            if user_profile.get('business_type'):
                parts.append(f"Business Type: {user_profile['business_type']}")
            if user_profile.get('state'):
                parts.append(f"State: {user_profile['state']}")
            if parts:
                context = "\nBusiness context: " + ", ".join(parts)

        user_content = f"""User's original question: {message}
{context}

Advisor responses:{responses_text}

Provide a concise board summary synthesizing the above responses."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYNTHESIS_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                max_completion_tokens=512
            )

            return response.choices[0].message.content
        except Exception:
            return None

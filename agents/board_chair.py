import re
import json
from agents.base import get_openai_client


ROUTING_PROMPT = """You are the Board Chair of an agricultural advisory board. Your role is to analyze incoming questions and determine which advisors on the board are most relevant to respond.

You must return valid JSON only — no other text.

Given the user's question and their business profile, select 2-4 of the most relevant advisors from the active board to respond. Consider:
1. Which advisors have direct expertise related to the question
2. The user's business type and how it relates to each advisor's specialty
3. Cross-functional implications (e.g., a land purchase question involves finance, legal, and possibly operations)

Return a JSON object with this exact structure:
{"selected": ["advisor_id_1", "advisor_id_2"], "rationale": "Brief explanation of why these advisors were selected"}

Only select from the active advisor IDs provided. Select 2-4 advisors unless the question truly requires more perspectives."""

SYNTHESIS_PROMPT = """You are the Board Chair of an agricultural advisory board. Your role is to synthesize the responses from multiple advisors into a clear, actionable board summary.

After reviewing all advisor responses to the user's question, produce a concise synthesis that includes:
1. **Key Recommendations** — The most important action items across all responses
2. **Points of Agreement** — Where advisors align in their advice
3. **Points to Consider** — Any differing perspectives or trade-offs the user should weigh
4. **Suggested Next Steps** — 2-3 concrete next steps the user should take

Keep the summary concise (3-5 bullet points total). Be direct and actionable. Do not simply repeat what the advisors said — synthesize and prioritize. Reference which advisor raised key points when helpful."""


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

Select 2-4 advisors and return JSON only."""

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
                selected = list(active_advisors.keys())[:4]
                rationale = "Routing to core advisors for broad coverage."

            return selected, rationale
        except Exception:
            selected = list(active_advisors.keys())[:4]
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

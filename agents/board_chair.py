import logging

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """You are the Board Chair of an agricultural advisory board. Your role is to synthesize advice from multiple expert advisors into one clear, consolidated response for the user.

Write exactly ONE paragraph that weaves together the most important insights from across the board — prioritize, synthesize, and make it actionable. Speak directly to the user in a warm, confident advisory tone. No bullet points, no headers, no numbered lists. Attribute key points to specific advisors by name when it adds clarity (e.g., "As your Financial Advisor noted..."). Be concrete and specific to their situation.

After the paragraph, on a new line starting with '💡', write ONE single key insight or important consideration the user should keep top of mind — the single most pivotal thing from the board's discussion. This should be a standalone sentence, not a repeat of the paragraph. Write it as a direct, punchy statement (e.g., "💡 Your cash reserve is your single biggest lever for surviving a down season.").

At the very end, on a new line starting with '❓', add ONE focused follow-up question only if it would meaningfully sharpen future advice. Skip the question entirely if the response is already complete. Never ask just to fill space."""

ADVISOR_TOPICS = {
    'financial': [
        'loan', 'finance', 'financial', 'budget', 'cash', 'cash flow', 'cost', 'costs',
        'profit', 'loss', 'capital', 'revenue', 'tax', 'taxes', 'debt', 'income',
        'expense', 'expenses', 'credit', 'funding', 'investment', 'invest', 'grant',
        'interest', 'payment', 'money', 'bank', 'afford', 'purchase', 'buy', 'buying',
        'borrow', 'lend', 'balance', 'depreciation', 'roi', 'return', 'payroll',
        'break-even', 'breakeven', 'margin', 'margins', 'overhead', 'liquidity',
        'solvency', 'ratio', 'ratios', 'forecast', 'projection', 'accounting',
    ],
    'operations': [
        'operation', 'operations', 'process', 'workflow', 'staff', 'employee', 'employees',
        'equipment', 'machinery', 'labor', 'efficiency', 'supply chain', 'logistics',
        'scheduling', 'maintenance', 'facility', 'storage', 'infrastructure', 'capacity',
        'output', 'scale', 'system', 'systems', 'automate', 'automation', 'manage',
        'management', 'hire', 'hiring', 'training', 'optimize',
    ],
    'marketing': [
        'marketing', 'brand', 'market', 'customer', 'customers', 'sales', 'sell', 'selling',
        'advertising', 'promotion', 'social media', 'pricing', 'distribution', 'retail',
        'wholesale', 'export', 'consumer', 'demand', 'buyer', 'buyers', 'direct market',
        'farmers market', 'csa', 'website', 'online', 'digital', 'audience', 'reach',
        'awareness', 'differentiate', 'competitive', 'strategy', 'niche',
    ],
    'legal': [
        'legal', 'law', 'regulation', 'regulations', 'compliance', 'permit', 'permits',
        'zoning', 'contract', 'contracts', 'liability', 'lawsuit', 'environmental',
        'usda', 'certification', 'label', 'labeling', 'right', 'rights', 'entity',
        'llc', 'corporation', 'lease', 'easement', 'deed', 'title', 'dispute',
        'penalty', 'fine', 'attorney', 'lawyer', 'legal advice', 'ordinance',
    ],
    'risk': [
        'risk', 'insurance', 'disaster', 'weather', 'crop failure', 'protection',
        'coverage', 'emergency', 'hazard', 'drought', 'flood', 'storm', 'hail',
        'loss prevention', 'guarantee', 'backup', 'contingency', 'diversify',
        'diversification', 'secure', 'security', 'vulnerable', 'exposure', 'hedge risk',
        'protect', 'safety net', 'crop insurance', 'arc', 'plc', 'fsa',
    ],
    'commodity_risk': [
        'commodity', 'commodities', 'futures', 'hedge', 'hedging', 'grain', 'corn',
        'soybean', 'soybeans', 'wheat', 'cotton', 'basis', 'options', 'price risk',
        'market price', 'spot price', 'contract price', 'forward contract', 'cash sale',
        'elevator', 'cbot', 'nymex', 'price volatility', 'lock price', 'merchandising',
        'storage hedge', 'feed cost', 'input cost hedging',
    ],
    'livestock': [
        'livestock', 'cattle', 'cow', 'cows', 'hog', 'hogs', 'pig', 'pigs', 'pork',
        'poultry', 'chicken', 'chickens', 'turkey', 'dairy', 'milk', 'beef', 'animal',
        'animals', 'herd', 'flock', 'feed', 'grazing', 'pasture', 'breeding',
        'veterinary', 'vet', 'antibiotic', 'vaccine', 'calving', 'farrowing',
        'stocking rate', 'rotational', 'animal health',
    ],
    'sustainability': [
        'sustainability', 'sustainable', 'organic', 'environment', 'environmental',
        'carbon', 'soil health', 'regenerative', 'conservation', 'water', 'climate',
        'esg', 'green', 'organic certification', 'no-till', 'cover crop', 'biodiversity',
        'ecosystem', 'emissions', 'footprint', 'renewable', 'carbon credit', 'stewardship',
        'nutrient management', 'certified', 'certification',
    ],
    'agronomist': [
        'crop', 'crops', 'soil', 'soil test', 'seed', 'seeds', 'fertilizer', 'plant',
        'plants', 'planting', 'agronomy', 'yield', 'yields', 'pest', 'pests', 'disease',
        'diseases', 'weed', 'weeds', 'irrigation', 'variety', 'varieties', 'field',
        'fields', 'harvest', 'rotation', 'cover crop', 'tillage', 'nutrient', 'grow',
        'growing', 'germination', 'herbicide', 'pesticide', 'fungicide', 'insecticide',
        'soil fertility', 'ph', 'micronutrient', 'macronutrient', 'corn', 'soybean',
        'wheat', 'row crop', 'acre', 'acres', 'stand', 'emergence',
    ],
}


class BoardChair:

    @staticmethod
    def route(message, active_advisors, user_profile=None):
        msg_lower = message.lower()
        words = set(msg_lower.split())

        scores = {}
        for advisor_id, keywords in ADVISOR_TOPICS.items():
            if advisor_id not in active_advisors:
                continue
            score = 0
            for kw in keywords:
                if ' ' in kw:
                    if kw in msg_lower:
                        score += 2
                elif kw in words:
                    score += 1
            scores[advisor_id] = score

        sorted_ids = sorted(scores.keys(), key=lambda aid: scores[aid], reverse=True)

        if all(scores[aid] == 0 for aid in sorted_ids):
            selected = sorted_ids[:5] if sorted_ids else list(active_advisors.keys())[:5]
            rationale = "Consulting advisors for a broad perspective on this question."
        else:
            selected = [aid for aid in sorted_ids if scores[aid] > 0][:5]
            if len(selected) < 2:
                selected = sorted_ids[:5]
            rationale = "Advisors selected based on question topic relevance."

        if len(selected) < 2:
            selected = list(active_advisors.keys())[:5]

        return selected, rationale

    @staticmethod
    def synthesize(message, advisor_responses, user_profile=None):
        from agents.base import get_openai_client
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

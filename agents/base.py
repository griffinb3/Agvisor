import os
import logging
from datetime import date
from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None
_training_data_cache = {}

MAX_TRAINING_WORDS = 2000

PRICE_KEYWORDS = {
    'price', 'prices', 'pricing', 'market', 'markets', 'commodity', 'commodities',
    'grain', 'corn', 'soybean', 'soybeans', 'wheat', 'cotton', 'cattle', 'hog',
    'hogs', 'milk', 'futures', 'hedge', 'hedging', 'basis', 'cash price',
    'crop price', 'feed cost', 'input cost', 'sell', 'selling', 'merchandising',
    'elevator', 'contract', 'spot', 'forward',
}


def get_openai_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
            base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        )
    return _client


def load_training_data(file_path):
    if file_path in _training_data_cache:
        return _training_data_cache[file_path]

    try:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        with open(full_path, 'r') as f:
            content = f.read()
        words = content.split()
        if len(words) > MAX_TRAINING_WORDS:
            content = ' '.join(words[:MAX_TRAINING_WORDS]) + '\n\n[Reference truncated]'
        _training_data_cache[file_path] = content
        return content
    except (FileNotFoundError, IOError):
        _training_data_cache[file_path] = None
        return None


def _normalize_words(message):
    import re
    return set(re.sub(r"[^\w\s]", " ", message.lower()).split())


def _is_price_question(message):
    if not message:
        return False
    words = _normalize_words(message)
    msg_lower = message.lower()
    for kw in PRICE_KEYWORDS:
        if ' ' in kw:
            if kw in msg_lower:
                return True
        elif kw in words:
            return True
    return False


class BaseAdvisor:
    title = "Advisor"
    specialty = "General"
    icon = "user"
    system_prompt = "You are an advisor."
    training_data_file = None

    @classmethod
    def info(cls):
        return {
            "title": cls.title,
            "specialty": cls.specialty,
            "icon": cls.icon,
        }

    @classmethod
    def build_system_prompt(cls, user_profile=None, direct_mode=False, message=None):
        base = cls.system_prompt

        if cls.training_data_file:
            training_data = load_training_data(cls.training_data_file)
            if training_data:
                base += f"\n\nREFERENCE KNOWLEDGE:\nUse the following domain knowledge to inform your responses. Reference specific data points, benchmarks, and programs when relevant to the user's question.\n\n{training_data}"

        if user_profile:
            state = user_profile.get('state', '')
            business_name = user_profile.get('business_name', '')
            business_type = user_profile.get('business_type', '')
            business_description = user_profile.get('business_description', '')
            business_data = user_profile.get('business_data')

            context = "\n\nIMPORTANT CONTEXT ABOUT THIS BUSINESS:\n"
            if business_name:
                context += f"- Business Name: {business_name}\n"
            if business_type:
                context += f"- Business Type: {business_type}\n"
            if state:
                context += f"- Location: {state}\n"
            if business_description:
                context += f"- Description: {business_description}\n"

            if business_data:
                context += "\n\nBUSINESS RECORDS PROVIDED:\n"
                context += f"- {business_data.get('summary', 'Business data uploaded')}\n"
                context += f"- Data columns: {', '.join(business_data.get('headers', []))}\n"
                context += "\nSample data from their records:\n"
                for i, row in enumerate(business_data.get('preview', [])[:5]):
                    row_str = ', '.join([f"{k}: {v}" for k, v in list(row.items())[:5]])
                    context += f"  Row {i+1}: {row_str}\n"
                context += "\nUse this business data to provide specific, data-driven advice. Reference their actual numbers when relevant."

            uploaded_doc = user_profile.get('uploaded_document')
            if uploaded_doc:
                doc_text = uploaded_doc.get('text', '')
                doc_words = doc_text.split()
                if len(doc_words) > 3000:
                    doc_text = ' '.join(doc_words[:3000]) + '\n\n[Document truncated for context]'
                context += f"\n\nUPLOADED BUSINESS DOCUMENT (provided by user — {uploaded_doc.get('summary', 'document')}):\n{doc_text}"
                context += "\nUse the content of this document to provide specific, informed advice. Reference relevant details from the document when applicable."

            financial_analysis = user_profile.get('financial_analysis')
            if financial_analysis:
                context += f"\n\nCOMPUTED FINANCIAL ANALYSIS (calculated from uploaded records):\n{financial_analysis}"

            if state or business_type:
                try:
                    from data.query import get_advisor_context
                    local_data = get_advisor_context(state, business_type)
                    if local_data:
                        context += f"\n\nSTATE & INDUSTRY DATA (from database — use these real data points in your advice):\n{local_data}"
                except Exception:
                    pass

            context += "\nTailor all your advice specifically to their location, business type, and operations. Reference relevant state-specific regulations, market conditions, and industry trends when applicable."

            try:
                from data.ag_calendar import get_seasonal_context
                growing_season_start = None
                if state:
                    try:
                        from data.query import _query
                        rows = _query("SELECT growing_season_start FROM state_ag_profiles WHERE state_name = %s", (state,))
                        if rows:
                            growing_season_start = rows[0].get('growing_season_start')
                    except Exception as e:
                        logger.debug(f"Could not fetch growing season: {e}")
                seasonal_context = get_seasonal_context(
                    state_name=state or None,
                    business_type=business_type or None,
                    current_date=date.today(),
                    growing_season_start=growing_season_start,
                )
                if seasonal_context:
                    context += f"\n\nCURRENT SEASONAL CONTEXT & UPCOMING DEADLINES:\n{seasonal_context}"
            except Exception as e:
                logger.warning(f"Failed to load seasonal context: {e}")

            if (state or business_type) and _is_price_question(message):
                try:
                    from data.commodity_prices import get_relevant_prices
                    price_data = get_relevant_prices(state or None, business_type or None)
                    if price_data and "unavailable" not in price_data.lower():
                        context += f"\n\nCURRENT COMMODITY PRICES (live market data):\n{price_data}"
                except Exception as e:
                    logger.warning(f"Failed to load commodity prices: {e}")

            base += context

        has_financial = bool(user_profile and user_profile.get('financial_analysis'))
        if direct_mode:
            base += "\n\nCONVERSATIONAL STYLE: Be direct, warm, and advisory — like a trusted one-on-one advisor. You are speaking directly with this user, so be personal and engaged."
            if has_financial:
                base += " The user has uploaded financial records — reference their specific numbers and trends where relevant to your domain."
            base += "\n\nRESPONSE FORMAT: Write exactly ONE concise paragraph of expert advice. No numbered lists, no bullet points, no headers. Be specific, focused, and tight.\n\nAfter the paragraph, on a new line starting with '💡', write ONE single key insight the user should keep top of mind — the most important takeaway from your expertise on this topic. Write it as a punchy, direct statement (e.g., '💡 Locking in your input costs now protects your margins regardless of what prices do.').\n\nIf one specific piece of information would meaningfully sharpen your next response, add it on a new line starting with '❓' as a direct, focused question. Only ask if genuinely useful — if you have nothing worth asking, omit the ❓ line entirely."
        else:
            base += "\n\nCONVERSATIONAL STYLE: Be direct, warm, and advisory — like a trusted expert contributing to a board discussion. Speak from your specific area of expertise only."
            if has_financial:
                base += " The user has uploaded financial records — reference their specific numbers and trends where relevant to your domain."
            base += "\n\nRESPONSE FORMAT: Write exactly ONE concise paragraph from your expert perspective. No numbered lists, no bullet points, no headers, no follow-up questions. Be specific, focused, and tight. The Board Chair will synthesize all perspectives and handle any follow-up with the user."

        return base

    @classmethod
    def get_response(cls, message, session_id, user_profile, conversation_histories,
                     direct_mode=False, rag_context=None):
        client = get_openai_client()
        advisor_id = cls.get_advisor_id()

        history_key = f"{session_id}_{advisor_id}"
        if history_key not in conversation_histories:
            conversation_histories[history_key] = []

        system_prompt = cls.build_system_prompt(user_profile, direct_mode=direct_mode, message=message)

        if rag_context is None:
            try:
                from data.rag import get_relevant_context
                state = user_profile.get('state') if user_profile else None
                btype = user_profile.get('business_type') if user_profile else None
                rag_context = get_relevant_context(message, top_k=3, state_name=state, business_type=btype)
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG context: {e}")

        if rag_context:
            system_prompt += f"\n\nRELEVANT REFERENCE DOCUMENTS (from USDA publications and extension guides — cite specific details when applicable):\n{rag_context}"

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(conversation_histories[history_key])
        messages.append({"role": "user", "content": message})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_completion_tokens=512
            )

            assistant_message = response.choices[0].message.content

            conversation_histories[history_key].append({"role": "user", "content": message})
            conversation_histories[history_key].append({"role": "assistant", "content": assistant_message})

            if len(conversation_histories[history_key]) > 20:
                conversation_histories[history_key] = conversation_histories[history_key][-20:]

            return {
                'advisor_id': advisor_id,
                'response': assistant_message,
                'title': cls.title,
                'icon': cls.icon
            }
        except Exception as e:
            return {
                'advisor_id': advisor_id,
                'response': f"Error getting response: {str(e)}",
                'title': cls.title,
                'icon': cls.icon
            }

    @classmethod
    def get_advisor_id(cls):
        from agents import ADVISOR_CLASSES
        for aid, klass in ADVISOR_CLASSES.items():
            if klass is cls:
                return aid
        return "unknown"

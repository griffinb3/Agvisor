import os
from openai import OpenAI

_client = None
_training_data_cache = {}


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
        _training_data_cache[file_path] = content
        return content
    except (FileNotFoundError, IOError):
        _training_data_cache[file_path] = None
        return None


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
    def build_system_prompt(cls, user_profile=None):
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

            context += "\nTailor all your advice specifically to their location, business type, and operations. Reference relevant state-specific regulations, market conditions, and industry trends when applicable."

            base += context

        base += "\n\nRESPONSE FORMAT: Keep your response concise. Write ONE short paragraph of analysis or advice, then list your TWO most important suggestions as numbered items. Do not exceed this format."

        return base

    @classmethod
    def get_response(cls, message, session_id, user_profile, conversation_histories):
        client = get_openai_client()
        advisor_id = cls.get_advisor_id()

        history_key = f"{session_id}_{advisor_id}"
        if history_key not in conversation_histories:
            conversation_histories[history_key] = []

        system_prompt = cls.build_system_prompt(user_profile)

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

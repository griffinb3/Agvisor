import os
from openai import OpenAI

_client = None


def get_openai_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
            base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        )
    return _client


class BaseAdvisor:
    title = "Advisor"
    specialty = "General"
    icon = "user"
    system_prompt = "You are an advisor."

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
                max_completion_tokens=1024
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

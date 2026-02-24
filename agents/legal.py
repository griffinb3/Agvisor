from agents.base import BaseAdvisor


class LegalAdvisor(BaseAdvisor):
    title = "Legal Specialist"
    specialty = "Federal & State Regulations"
    icon = "gavel"
    training_data_file = "training_data/legal.md"
    system_prompt = """You are the Legal Specialist on this agricultural advisory board with expertise in both federal and state agricultural regulations. You specialize in:
- Federal agricultural laws and USDA regulations
- State-specific agricultural codes and requirements
- Land use, zoning, and water rights
- Environmental compliance (EPA, Clean Water Act)
- Labor laws specific to agricultural businesses
- Business contracts, partnerships, and liability
- Certifications and licensing requirements
- Agricultural tax law and estate planning
- Chemical, pesticide, and input regulations
- Food safety regulations (FDA, FSMA)

Provide clear, practical legal guidance while noting that you are providing general information and not legal advice. Recommend consulting a licensed attorney for specific legal matters. Always consider both federal regulations and state-specific laws when providing guidance."""

    @classmethod
    def build_system_prompt(cls, user_profile=None):
        base = super().build_system_prompt(user_profile)

        if user_profile:
            state = user_profile.get('state', '')
            business_type = user_profile.get('business_type', '')
            if state:
                base += f"\n\nPay special attention to {state} agricultural laws, regulations, and any state-specific programs or restrictions that apply to their {business_type or 'agricultural'} business."

        return base

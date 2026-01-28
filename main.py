import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Using Replit's AI Integrations service - no API key needed
# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

ADVISORS = {
    "agronomist": {
        "name": "Dr. Sarah Chen",
        "title": "Chief Agronomist",
        "specialty": "Crop Science & Soil Health",
        "icon": "leaf",
        "system_prompt": """You are Dr. Sarah Chen, a Chief Agronomist with 25 years of experience in crop science and soil health. You specialize in:
- Crop rotation strategies and planning
- Soil testing and amendment recommendations
- Pest and disease management
- Sustainable farming practices
- Yield optimization techniques

Provide expert, practical advice tailored to agricultural businesses. Be specific with recommendations and explain the science behind your suggestions when helpful. Always consider the farmer's specific conditions, climate, and resources."""
    },
    "financial": {
        "name": "Marcus Thompson",
        "title": "Agricultural Finance Director",
        "specialty": "Farm Economics & Investment",
        "icon": "chart-line",
        "system_prompt": """You are Marcus Thompson, an Agricultural Finance Director with extensive experience in farm economics. You specialize in:
- Farm budgeting and cash flow management
- Agricultural loans and financing options
- Risk management and crop insurance
- Investment analysis for farm equipment and land
- Grant opportunities and government programs
- Commodity market analysis

Provide sound financial advice specific to agricultural businesses. Help farmers understand their numbers, identify cost savings, and make smart investment decisions."""
    },
    "operations": {
        "name": "Elena Rodriguez",
        "title": "Operations Manager",
        "specialty": "Farm Operations & Logistics",
        "icon": "cogs",
        "system_prompt": """You are Elena Rodriguez, a Farm Operations Manager with expertise in agricultural logistics. You specialize in:
- Equipment selection and maintenance scheduling
- Labor management and workforce planning
- Supply chain and distribution optimization
- Harvest timing and post-harvest handling
- Technology integration and precision agriculture
- Storage and inventory management

Provide practical operational advice to help farms run more efficiently. Focus on actionable improvements that can be implemented realistically."""
    },
    "marketing": {
        "name": "James Okonkwo",
        "title": "Agricultural Marketing Strategist",
        "specialty": "Sales & Market Development",
        "icon": "bullhorn",
        "system_prompt": """You are James Okonkwo, an Agricultural Marketing Strategist helping farms grow their business. You specialize in:
- Direct-to-consumer sales strategies
- Farmers market and CSA program development
- Wholesale and retail buyer relationships
- Brand development for farm products
- Digital marketing for agricultural businesses
- Value-added product opportunities

Help farmers find new markets, improve their pricing strategies, and build stronger customer relationships."""
    },
    "sustainability": {
        "name": "Dr. Amara Patel",
        "title": "Sustainability Advisor",
        "specialty": "Environmental Stewardship",
        "icon": "seedling",
        "system_prompt": """You are Dr. Amara Patel, a Sustainability Advisor focused on environmentally responsible farming. You specialize in:
- Organic certification processes
- Regenerative agriculture practices
- Carbon sequestration and credits
- Water conservation techniques
- Biodiversity and habitat preservation
- Renewable energy for farms

Guide farmers toward sustainable practices that are both environmentally beneficial and economically viable. Help them understand certifications, incentive programs, and long-term benefits."""
    }
}

conversation_histories = {}

@app.route('/')
def index():
    return render_template('index.html', advisors=ADVISORS)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    advisor_id = data.get('advisor', 'agronomist')
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    advisor = ADVISORS.get(advisor_id, ADVISORS['agronomist'])
    
    history_key = f"{session_id}_{advisor_id}"
    if history_key not in conversation_histories:
        conversation_histories[history_key] = []
    
    messages = [
        {"role": "system", "content": advisor['system_prompt']}
    ]
    messages.extend(conversation_histories[history_key])
    messages.append({"role": "user", "content": message})
    
    try:
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=2048
        )
        
        assistant_message = response.choices[0].message.content
        
        conversation_histories[history_key].append({"role": "user", "content": message})
        conversation_histories[history_key].append({"role": "assistant", "content": assistant_message})
        
        if len(conversation_histories[history_key]) > 20:
            conversation_histories[history_key] = conversation_histories[history_key][-20:]
        
        return jsonify({
            'response': assistant_message,
            'advisor': {
                'name': advisor['name'],
                'title': advisor['title']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_history():
    data = request.json
    session_id = data.get('session_id', 'default')
    advisor_id = data.get('advisor')
    
    if advisor_id:
        history_key = f"{session_id}_{advisor_id}"
        if history_key in conversation_histories:
            del conversation_histories[history_key]
    else:
        keys_to_delete = [k for k in conversation_histories if k.startswith(session_id)]
        for key in keys_to_delete:
            del conversation_histories[key]
    
    return jsonify({'status': 'cleared'})

@app.route('/api/advisors')
def get_advisors():
    return jsonify({
        advisor_id: {
            'name': advisor['name'],
            'title': advisor['title'],
            'specialty': advisor['specialty'],
            'icon': advisor['icon']
        }
        for advisor_id, advisor in ADVISORS.items()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

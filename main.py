import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]

LIVESTOCK_OPTIONS = [
    "Beef Cattle", "Dairy Cattle", "Hogs/Pigs", "Poultry - Broilers",
    "Poultry - Layers", "Poultry - Turkeys", "Sheep", "Goats - Meat",
    "Goats - Dairy", "Horses", "Bison/Buffalo", "Alpacas/Llamas",
    "Rabbits", "Fish/Aquaculture", "Bees/Apiary", "Other Livestock"
]

COMMON_CROPS = [
    "Corn", "Soybeans", "Wheat", "Cotton", "Hay/Alfalfa", "Rice",
    "Sorghum", "Barley", "Oats", "Potatoes", "Tomatoes", "Lettuce",
    "Onions", "Carrots", "Apples", "Grapes", "Oranges", "Strawberries",
    "Blueberries", "Almonds", "Pecans", "Walnuts", "Peanuts",
    "Sunflowers", "Canola", "Sugar Beets", "Sugarcane", "Tobacco",
    "Hemp", "Hops", "Vegetables (Mixed)", "Fruits (Mixed)", "Other Crops"
]

def get_advisor_system_prompt(advisor_key, user_profile=None):
    base_prompts = {
        "agronomist": """You are the Chief Agronomist on this agricultural advisory board with 25 years of experience in crop science and soil health. You specialize in:
- Crop rotation strategies and planning
- Soil testing and amendment recommendations
- Pest and disease management
- Sustainable farming practices
- Yield optimization techniques

Provide expert, practical advice tailored to agricultural businesses. Be specific with recommendations and explain the science behind your suggestions when helpful.""",

        "financial": """You are the Finance Director on this agricultural advisory board with extensive experience in farm economics. You specialize in:
- Farm budgeting and cash flow management
- Agricultural loans and financing options
- Risk management and crop insurance
- Investment analysis for farm equipment and land
- Grant opportunities and government programs
- Commodity market analysis

Provide sound financial advice specific to agricultural businesses. Help farmers understand their numbers, identify cost savings, and make smart investment decisions.""",

        "operations": """You are the Operations Manager on this agricultural advisory board with expertise in agricultural logistics. You specialize in:
- Equipment selection and maintenance scheduling
- Labor management and workforce planning
- Supply chain and distribution optimization
- Harvest timing and post-harvest handling
- Technology integration and precision agriculture
- Storage and inventory management

Provide practical operational advice to help farms run more efficiently. Focus on actionable improvements that can be implemented realistically.""",

        "marketing": """You are the Marketing Strategist on this agricultural advisory board helping farms grow their business. You specialize in:
- Direct-to-consumer sales strategies
- Farmers market and CSA program development
- Wholesale and retail buyer relationships
- Brand development for farm products
- Digital marketing for agricultural businesses
- Value-added product opportunities

Help farmers find new markets, improve their pricing strategies, and build stronger customer relationships.""",

        "sustainability": """You are the Sustainability Advisor on this agricultural advisory board focused on environmentally responsible farming. You specialize in:
- Organic certification processes
- Regenerative agriculture practices
- Carbon sequestration and credits
- Water conservation techniques
- Biodiversity and habitat preservation
- Renewable energy for farms

Guide farmers toward sustainable practices that are both environmentally beneficial and economically viable. Help them understand certifications, incentive programs, and long-term benefits.""",

        "legal": """You are the Legal Specialist on this agricultural advisory board with expertise in both federal and state agricultural regulations. You specialize in:
- Federal agricultural laws and USDA regulations
- State-specific agricultural codes and requirements
- Land use, zoning, and water rights
- Environmental compliance (EPA, Clean Water Act)
- Labor laws specific to agricultural workers
- Farm contracts and liability issues
- Organic and specialty crop certifications
- Agricultural tax law and estate planning
- Pesticide and chemical regulations
- Food safety regulations (FDA, FSMA)

Provide clear, practical legal guidance while noting that you are providing general information and not legal advice. Recommend consulting a licensed attorney for specific legal matters. Always consider both federal regulations and state-specific laws when providing guidance."""
    }
    
    base = base_prompts.get(advisor_key, base_prompts["agronomist"])
    
    if user_profile:
        state = user_profile.get('state', '')
        crops = user_profile.get('crops', [])
        livestock = user_profile.get('livestock', [])
        farm_name = user_profile.get('farm_name', '')
        
        context = f"\n\nIMPORTANT CONTEXT ABOUT THIS FARMER:\n"
        if farm_name:
            context += f"- Farm Name: {farm_name}\n"
        if state:
            context += f"- Location: {state}\n"
        if livestock:
            context += f"- Livestock: {', '.join(livestock)}\n"
        if crops:
            context += f"- Crops/Products: {', '.join(crops)}\n"
        
        context += "\nTailor all your advice specifically to their location, crops, and conditions. Reference relevant state-specific regulations, climate considerations, and market conditions when applicable."
        
        if advisor_key == "legal" and state:
            operations = []
            if livestock:
                operations.append(f"livestock ({', '.join(livestock)})")
            if crops:
                operations.append(f"crops ({', '.join(crops)})")
            operations_str = ' and '.join(operations) if operations else 'their farming operation'
            context += f"\n\nPay special attention to {state} agricultural laws, water rights, labor regulations, and any state-specific programs or restrictions that apply to their {operations_str}."
        
        base += context
    
    return base

ADVISORS = {
    "agronomist": {
        "title": "Chief Agronomist",
        "specialty": "Crop Science & Soil Health",
        "icon": "leaf"
    },
    "financial": {
        "title": "Finance Director",
        "specialty": "Farm Economics & Investment",
        "icon": "chart-line"
    },
    "operations": {
        "title": "Operations Manager",
        "specialty": "Farm Operations & Logistics",
        "icon": "cogs"
    },
    "marketing": {
        "title": "Marketing Strategist",
        "specialty": "Sales & Market Development",
        "icon": "bullhorn"
    },
    "sustainability": {
        "title": "Sustainability Advisor",
        "specialty": "Environmental Stewardship",
        "icon": "seedling"
    },
    "legal": {
        "title": "Legal Specialist",
        "specialty": "Federal & State Regulations",
        "icon": "gavel"
    }
}

conversation_histories = {}
user_profiles = {}

@app.route('/')
def index():
    return render_template('index.html', advisors=ADVISORS, states=US_STATES, livestock=LIVESTOCK_OPTIONS, crops=COMMON_CROPS)

@app.route('/api/profile', methods=['POST'])
def save_profile():
    data = request.json
    session_id = data.get('session_id', 'default')
    
    user_profiles[session_id] = {
        'farm_name': data.get('farm_name', ''),
        'state': data.get('state', ''),
        'livestock': data.get('livestock', []),
        'crops': data.get('crops', [])
    }
    
    return jsonify({'status': 'saved', 'profile': user_profiles[session_id]})

@app.route('/api/profile/<session_id>', methods=['GET'])
def get_profile(session_id):
    profile = user_profiles.get(session_id, {})
    return jsonify(profile)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    advisor_id = data.get('advisor', 'agronomist')
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    advisor = ADVISORS.get(advisor_id, ADVISORS['agronomist'])
    user_profile = user_profiles.get(session_id)
    
    history_key = f"{session_id}_{advisor_id}"
    if history_key not in conversation_histories:
        conversation_histories[history_key] = []
    
    system_prompt = get_advisor_system_prompt(advisor_id, user_profile)
    
    messages = [
        {"role": "system", "content": system_prompt}
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
                'title': advisor['title']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def detect_specific_advisor(message):
    """Detect if user is asking for a specific advisor based on keywords"""
    message_lower = message.lower()
    
    advisor_keywords = {
        'agronomist': ['agronomist', 'crop', 'soil', 'pest', 'plant', 'seeds', 'fertilizer', 'yield'],
        'financial': ['finance', 'financial', 'budget', 'loan', 'insurance', 'investment', 'money', 'cost', 'profit', 'grant'],
        'operations': ['operations', 'equipment', 'labor', 'harvest', 'logistics', 'storage', 'machinery', 'workers'],
        'marketing': ['marketing', 'sales', 'market', 'brand', 'customer', 'pricing', 'sell', 'buyer'],
        'sustainability': ['sustainability', 'sustainable', 'organic', 'carbon', 'environment', 'conservation', 'renewable', 'green'],
        'legal': ['legal', 'law', 'regulation', 'compliance', 'contract', 'zoning', 'rights', 'liability', 'attorney', 'lawyer']
    }
    
    title_keywords = {
        'agronomist': ['agronomist'],
        'financial': ['finance director', 'financial'],
        'operations': ['operations manager', 'operations'],
        'marketing': ['marketing strategist', 'marketing'],
        'sustainability': ['sustainability advisor', 'sustainability'],
        'legal': ['legal specialist', 'legal', 'lawyer', 'attorney']
    }
    
    for advisor_id, keywords in title_keywords.items():
        for keyword in keywords:
            pattern = rf'\b{keyword}\b'
            if re.search(pattern, message_lower):
                if any(phrase in message_lower for phrase in ['ask the', 'talk to', 'speak to', 'from the', 'hey ', 'question for']):
                    return advisor_id
    
    return None

def get_advisor_response(advisor_id, message, session_id, user_profile):
    """Get response from a single advisor"""
    advisor = ADVISORS.get(advisor_id, ADVISORS['agronomist'])
    
    history_key = f"{session_id}_{advisor_id}"
    if history_key not in conversation_histories:
        conversation_histories[history_key] = []
    
    system_prompt = get_advisor_system_prompt(advisor_id, user_profile)
    
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
            'title': advisor['title'],
            'icon': advisor['icon']
        }
    except Exception as e:
        return {
            'advisor_id': advisor_id,
            'response': f"Error getting response: {str(e)}",
            'title': advisor['title'],
            'icon': advisor['icon']
        }

@app.route('/api/chat/all', methods=['POST'])
def chat_all():
    """Get responses from all advisors or detect if specific advisor requested"""
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    user_profile = user_profiles.get(session_id)
    
    specific_advisor = detect_specific_advisor(message)
    
    if specific_advisor:
        result = get_advisor_response(specific_advisor, message, session_id, user_profile)
        return jsonify({
            'mode': 'single',
            'responses': [result]
        })
    
    responses = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(get_advisor_response, advisor_id, message, session_id, user_profile): advisor_id
            for advisor_id in ADVISORS.keys()
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                responses.append(result)
            except Exception as e:
                advisor_id = futures[future]
                responses.append({
                    'advisor_id': advisor_id,
                    'response': f"Error: {str(e)}",
                    'title': ADVISORS[advisor_id]['title'],
                    'icon': ADVISORS[advisor_id]['icon']
                })
    
    advisor_order = ['agronomist', 'financial', 'operations', 'marketing', 'sustainability', 'legal']
    responses.sort(key=lambda x: advisor_order.index(x['advisor_id']) if x['advisor_id'] in advisor_order else 99)
    
    return jsonify({
        'mode': 'all',
        'responses': responses
    })

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
            'title': advisor['title'],
            'specialty': advisor['specialty'],
            'icon': advisor['icon']
        }
        for advisor_id, advisor in ADVISORS.items()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

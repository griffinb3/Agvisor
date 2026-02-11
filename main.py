import os
import re
import csv
import io
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


def get_advisor_system_prompt(advisor_key, user_profile=None):
    base_prompts = {
        "agronomist": """You are the Chief Agronomist on this agricultural advisory board with 25 years of experience in crop science, soil health, and agronomy. You specialize in:
- Crop production strategies and planning
- Soil testing and amendment recommendations
- Pest, disease, and weed management
- Sustainable and regenerative practices
- Yield optimization and input management
- Ag product quality and performance

Provide expert, practical advice tailored to agricultural businesses of all types. Be specific with recommendations and explain the science behind your suggestions when helpful.""",

        "financial": """You are the Finance Director on this agricultural advisory board with extensive experience in agricultural economics. You specialize in:
- Business budgeting and cash flow management
- Agricultural loans, financing, and capital planning
- Risk management, insurance, and hedging
- Investment analysis for equipment, land, and expansion
- Grant opportunities and government programs
- Commodity and input market analysis

Provide sound financial advice specific to agricultural businesses of all types. Help them understand their numbers, identify cost savings, and make smart investment decisions.""",

        "operations": """You are the Operations Manager on this agricultural advisory board with expertise in agricultural business operations. You specialize in:
- Equipment selection, maintenance, and fleet management
- Labor management and workforce planning
- Supply chain and distribution optimization
- Logistics, scheduling, and workflow efficiency
- Technology integration and precision agriculture
- Inventory, storage, and facility management

Provide practical operational advice to help agricultural businesses run more efficiently. Focus on actionable improvements that can be implemented realistically.""",

        "marketing": """You are the Marketing Strategist on this agricultural advisory board helping agricultural businesses grow. You specialize in:
- Sales channel strategies (direct, wholesale, retail, B2B)
- Market development and customer acquisition
- Brand development for ag products and services
- Digital marketing for agricultural businesses
- Value-added product and service opportunities
- Pricing strategy and competitive positioning

Help agricultural businesses find new markets, improve their pricing strategies, and build stronger customer relationships.""",

        "sustainability": """You are the Sustainability Advisor on this agricultural advisory board focused on environmental stewardship across the ag industry. You specialize in:
- Certification processes (organic, sustainable, fair trade)
- Regenerative and conservation practices
- Carbon markets and environmental credits
- Water and resource conservation
- Biodiversity and habitat preservation
- Renewable energy and efficiency for ag businesses

Guide agricultural businesses toward sustainable practices that are both environmentally beneficial and economically viable. Help them understand certifications, incentive programs, and long-term benefits.""",

        "legal": """You are the Legal Specialist on this agricultural advisory board with expertise in both federal and state agricultural regulations. You specialize in:
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
    }
    
    base = base_prompts.get(advisor_key, base_prompts["agronomist"])
    
    if user_profile:
        state = user_profile.get('state', '')
        business_name = user_profile.get('business_name', '')
        business_type = user_profile.get('business_type', '')
        business_description = user_profile.get('business_description', '')
        business_data = user_profile.get('business_data')
        
        context = f"\n\nIMPORTANT CONTEXT ABOUT THIS BUSINESS:\n"
        if business_name:
            context += f"- Business Name: {business_name}\n"
        if business_type:
            context += f"- Business Type: {business_type}\n"
        if state:
            context += f"- Location: {state}\n"
        if business_description:
            context += f"- Description: {business_description}\n"
        
        if business_data:
            context += f"\n\nBUSINESS RECORDS PROVIDED:\n"
            context += f"- {business_data.get('summary', 'Business data uploaded')}\n"
            context += f"- Data columns: {', '.join(business_data.get('headers', []))}\n"
            context += f"\nSample data from their records:\n"
            for i, row in enumerate(business_data.get('preview', [])[:5]):
                row_str = ', '.join([f"{k}: {v}" for k, v in list(row.items())[:5]])
                context += f"  Row {i+1}: {row_str}\n"
            context += "\nUse this business data to provide specific, data-driven advice. Reference their actual numbers when relevant."
        
        context += "\nTailor all your advice specifically to their location, business type, and operations. Reference relevant state-specific regulations, market conditions, and industry trends when applicable."
        
        if advisor_key == "legal" and state:
            context += f"\n\nPay special attention to {state} agricultural laws, regulations, and any state-specific programs or restrictions that apply to their {business_type or 'agricultural'} business."
        
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
        "specialty": "Ag Economics & Investment",
        "icon": "chart-line"
    },
    "operations": {
        "title": "Operations Manager",
        "specialty": "Ag Operations & Logistics",
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
    return render_template('index.html', advisors=ADVISORS, states=US_STATES)

@app.route('/api/profile', methods=['POST'])
def save_profile():
    data = request.json
    session_id = data.get('session_id', 'default')
    
    existing_profile = user_profiles.get(session_id, {})
    
    user_profiles[session_id] = {
        'business_name': data.get('business_name', ''),
        'state': data.get('state', ''),
        'business_type': data.get('business_type', ''),
        'business_description': data.get('business_description', ''),
        'business_data': existing_profile.get('business_data', None)
    }
    
    return jsonify({'status': 'saved', 'profile': user_profiles[session_id]})

@app.route('/api/upload-records', methods=['POST'])
def upload_records():
    session_id = request.form.get('session_id', 'default')
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        
        if len(rows) > 100:
            rows = rows[:100]
        
        headers = reader.fieldnames or []
        
        summary = f"Business records with {len(rows)} rows and columns: {', '.join(headers[:10])}"
        
        data_preview = []
        for row in rows[:20]:
            data_preview.append(dict(row))
        
        if session_id not in user_profiles:
            user_profiles[session_id] = {}
        
        user_profiles[session_id]['business_data'] = {
            'summary': summary,
            'headers': headers[:15],
            'preview': data_preview,
            'row_count': len(rows)
        }
        
        return jsonify({
            'status': 'uploaded',
            'summary': summary,
            'row_count': len(rows)
        })
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400

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

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

BASE_ADVISORS = {
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
        "title": "Marketing Specialist",
        "specialty": "Sales & Market Development",
        "icon": "bullhorn"
    },
    "legal": {
        "title": "Legal Specialist",
        "specialty": "Federal & State Regulations",
        "icon": "gavel"
    },
    "risk": {
        "title": "Risk Advisor",
        "specialty": "Risk Management & Insurance",
        "icon": "shield-alt"
    }
}

OPTIONAL_ADVISORS = {
    "commodity_risk": {
        "title": "Commodity Risk Advisor",
        "specialty": "Commodity Markets & Hedging",
        "icon": "chart-bar"
    },
    "livestock": {
        "title": "Livestock & Animal Systems Advisor",
        "specialty": "Animal Production & Health",
        "icon": "horse"
    },
    "sustainability": {
        "title": "Sustainability Advisor",
        "specialty": "Environmental Stewardship",
        "icon": "seedling"
    },
    "agronomist": {
        "title": "Agronomist",
        "specialty": "Crop Science & Soil Health",
        "icon": "leaf"
    }
}

ALL_ADVISORS = {**BASE_ADVISORS, **OPTIONAL_ADVISORS}

BOARD_SUGGESTIONS = {
    "Row Crop Farm": {
        "recommended": ["agronomist", "commodity_risk"],
        "tip": "Row crop operations benefit greatly from an Agronomist for crop planning and soil health, and a Commodity Risk Advisor to manage grain market exposure and hedge positions."
    },
    "Livestock Operation": {
        "recommended": ["livestock", "commodity_risk"],
        "tip": "Livestock operations should consider a Livestock & Animal Systems Advisor for herd management and animal health, and a Commodity Risk Advisor to manage feed cost volatility."
    },
    "Mixed Farming": {
        "recommended": ["agronomist", "livestock", "commodity_risk"],
        "tip": "Mixed operations juggle crops and livestock — an Agronomist, Livestock Advisor, and Commodity Risk Advisor together give you full coverage across your diversified operation."
    },
    "Dairy Operation": {
        "recommended": ["livestock", "commodity_risk"],
        "tip": "Dairy operations benefit from a Livestock & Animal Systems Advisor for herd health and production, plus a Commodity Risk Advisor to manage milk and feed price risk."
    },
    "Specialty Crop / Horticulture": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Specialty crop growers benefit from an Agronomist for crop-specific guidance and a Sustainability Advisor to explore certifications like organic or GAP that can boost margins."
    },
    "Vineyard / Winery": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Vineyards and wineries benefit from an Agronomist for viticulture expertise and a Sustainability Advisor for sustainable growing certifications that resonate with consumers."
    },
    "Orchard": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Orchard operations benefit from an Agronomist for tree crop management and a Sustainability Advisor to explore organic or conservation certifications."
    },
    "Nursery / Greenhouse": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Nursery and greenhouse operations benefit from an Agronomist for plant production expertise and a Sustainability Advisor for energy efficiency and environmental certifications."
    },
    "Ag Equipment Dealer / Service": {
        "recommended": [],
        "tip": "Equipment dealers may not need the production-focused optional advisors, but consider the Sustainability Advisor if you're selling precision ag or conservation equipment."
    },
    "Ag Input Supplier": {
        "recommended": ["agronomist"],
        "tip": "Input suppliers can benefit from an Agronomist to better understand the technical needs of your farming customers and provide informed product recommendations."
    },
    "Grain Elevator / Storage": {
        "recommended": ["commodity_risk"],
        "tip": "Grain elevators and storage operations deal directly with commodity markets — a Commodity Risk Advisor is highly recommended for basis management and hedging strategies."
    },
    "Food Processing / Packing": {
        "recommended": ["sustainability"],
        "tip": "Food processors benefit from a Sustainability Advisor for certifications, waste reduction, and meeting retailer sustainability requirements."
    },
    "Ag Tech / Precision Ag": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Ag tech companies benefit from an Agronomist to ground your solutions in production reality, and a Sustainability Advisor to align with growing ESG and carbon market opportunities."
    },
    "Ag Finance / Lending": {
        "recommended": ["commodity_risk"],
        "tip": "Ag lenders benefit from a Commodity Risk Advisor to better understand the commodity risk exposure of your borrowers."
    },
    "Ag Consulting": {
        "recommended": ["agronomist", "sustainability"],
        "tip": "Ag consultants benefit from an Agronomist and Sustainability Advisor to broaden the expertise you can offer your clients."
    },
    "Cooperative": {
        "recommended": ["commodity_risk", "agronomist"],
        "tip": "Cooperatives can benefit from a Commodity Risk Advisor for member grain marketing programs and an Agronomist to support member production advice."
    },
    "Other Ag Business": {
        "recommended": [],
        "tip": "Review the optional advisors and add any that align with your specific business needs. You can always change your board later."
    }
}


def get_advisor_system_prompt(advisor_key, user_profile=None):
    base_prompts = {
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

        "marketing": """You are the Marketing Specialist on this agricultural advisory board helping agricultural businesses grow. You specialize in:
- Sales channel strategies (direct, wholesale, retail, B2B)
- Market development and customer acquisition
- Brand development for ag products and services
- Digital marketing for agricultural businesses
- Value-added product and service opportunities
- Pricing strategy and competitive positioning

Help agricultural businesses find new markets, improve their pricing strategies, and build stronger customer relationships.""",

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

Provide clear, practical legal guidance while noting that you are providing general information and not legal advice. Recommend consulting a licensed attorney for specific legal matters. Always consider both federal regulations and state-specific laws when providing guidance.""",

        "risk": """You are the Risk Advisor on this agricultural advisory board with deep expertise in agricultural risk management. You specialize in:
- Enterprise risk assessment and mitigation
- Crop and livestock insurance programs (MPCI, PRF, LRP, LGM)
- Business continuity and disaster planning
- Weather and climate risk strategies
- Liability and property risk management
- Succession planning and key-person risk
- Cybersecurity and data protection for ag businesses

Help agricultural businesses identify, quantify, and manage the full spectrum of risks they face. Provide practical risk mitigation strategies and insurance guidance.""",

        "commodity_risk": """You are the Commodity Risk Advisor on this agricultural advisory board with extensive experience in commodity markets and price risk management. You specialize in:
- Futures and options hedging strategies
- Basis analysis and management
- Cash marketing strategies and contracting
- Input cost risk management (fuel, fertilizer, feed)
- Margin management and profit targeting
- Market analysis and price outlook
- Crop and livestock marketing plans

Help agricultural businesses develop and execute effective commodity risk management strategies. Explain complex hedging concepts in practical terms and tailor recommendations to their specific exposure.""",

        "livestock": """You are the Livestock & Animal Systems Advisor on this agricultural advisory board with deep expertise in animal agriculture. You specialize in:
- Herd and flock management strategies
- Animal nutrition and feed formulation
- Breeding, genetics, and reproductive management
- Animal health and disease prevention
- Pasture and rangeland management
- Facility design and animal welfare
- Production record analysis and benchmarking

Provide expert, practical advice on all aspects of livestock and animal production systems. Be specific with recommendations and explain the science behind your suggestions when helpful.""",

        "sustainability": """You are the Sustainability Advisor on this agricultural advisory board focused on environmental stewardship across the ag industry. You specialize in:
- Certification processes (organic, sustainable, fair trade)
- Regenerative and conservation practices
- Carbon markets and environmental credits
- Water and resource conservation
- Biodiversity and habitat preservation
- Renewable energy and efficiency for ag businesses
- ESG reporting and sustainability metrics

Guide agricultural businesses toward sustainable practices that are both environmentally beneficial and economically viable. Help them understand certifications, incentive programs, and long-term benefits.""",

        "agronomist": """You are the Agronomist on this agricultural advisory board with 25 years of experience in crop science, soil health, and agronomy. You specialize in:
- Crop production strategies and planning
- Soil testing and amendment recommendations
- Pest, disease, and weed management
- Sustainable and regenerative practices
- Yield optimization and input management
- Ag product quality and performance
- Precision agriculture and data-driven decisions

Provide expert, practical advice tailored to agricultural businesses of all types. Be specific with recommendations and explain the science behind your suggestions when helpful."""
    }

    base = base_prompts.get(advisor_key, base_prompts["financial"])

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


conversation_histories = {}
user_profiles = {}


@app.route('/')
def index():
    return render_template('index.html',
                           base_advisors=BASE_ADVISORS,
                           optional_advisors=OPTIONAL_ADVISORS,
                           states=US_STATES,
                           board_suggestions=BOARD_SUGGESTIONS)


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
        'selected_advisors': data.get('selected_advisors', []),
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
    advisor_id = data.get('advisor', 'financial')
    session_id = data.get('session_id', 'default')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    advisor = ALL_ADVISORS.get(advisor_id, ALL_ADVISORS['financial'])
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


def get_active_advisors(session_id):
    user_profile = user_profiles.get(session_id, {})
    selected = user_profile.get('selected_advisors', [])
    active = dict(BASE_ADVISORS)
    for advisor_id in selected:
        if advisor_id in OPTIONAL_ADVISORS:
            active[advisor_id] = OPTIONAL_ADVISORS[advisor_id]
    return active


def detect_specific_advisor(message, active_advisors):
    message_lower = message.lower()

    title_keywords = {
        'financial': ['finance director', 'finance'],
        'operations': ['operations manager', 'operations'],
        'marketing': ['marketing specialist', 'marketing'],
        'legal': ['legal specialist', 'legal', 'lawyer', 'attorney'],
        'risk': ['risk advisor', 'risk management'],
        'commodity_risk': ['commodity risk', 'commodity advisor', 'hedging', 'futures'],
        'livestock': ['livestock advisor', 'livestock', 'animal systems', 'animal advisor', 'herd'],
        'sustainability': ['sustainability advisor', 'sustainability'],
        'agronomist': ['agronomist', 'agronomy']
    }

    for advisor_id, keywords in title_keywords.items():
        if advisor_id not in active_advisors:
            continue
        for keyword in keywords:
            pattern = rf'\b{re.escape(keyword)}\b'
            if re.search(pattern, message_lower):
                if any(phrase in message_lower for phrase in ['ask the', 'talk to', 'speak to', 'from the', 'hey ', 'question for']):
                    return advisor_id

    return None


def get_advisor_response(advisor_id, message, session_id, user_profile):
    advisor = ALL_ADVISORS.get(advisor_id, ALL_ADVISORS['financial'])

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
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    user_profile = user_profiles.get(session_id)
    active_advisors = get_active_advisors(session_id)

    specific_advisor = detect_specific_advisor(message, active_advisors)

    if specific_advisor:
        result = get_advisor_response(specific_advisor, message, session_id, user_profile)
        return jsonify({
            'mode': 'single',
            'responses': [result]
        })

    responses = []
    max_workers = len(active_advisors)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_advisor_response, advisor_id, message, session_id, user_profile): advisor_id
            for advisor_id in active_advisors.keys()
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                responses.append(result)
            except Exception as e:
                advisor_id = futures[future]
                advisor = active_advisors[advisor_id]
                responses.append({
                    'advisor_id': advisor_id,
                    'response': f"Error: {str(e)}",
                    'title': advisor['title'],
                    'icon': advisor['icon']
                })

    advisor_order = ['financial', 'operations', 'marketing', 'legal', 'risk', 'commodity_risk', 'livestock', 'sustainability', 'agronomist']
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
        'base': {
            advisor_id: {
                'title': advisor['title'],
                'specialty': advisor['specialty'],
                'icon': advisor['icon']
            }
            for advisor_id, advisor in BASE_ADVISORS.items()
        },
        'optional': {
            advisor_id: {
                'title': advisor['title'],
                'specialty': advisor['specialty'],
                'icon': advisor['icon']
            }
            for advisor_id, advisor in OPTIONAL_ADVISORS.items()
        }
    })


@app.route('/api/suggestions/<business_type>')
def get_suggestions(business_type):
    suggestion = BOARD_SUGGESTIONS.get(business_type, BOARD_SUGGESTIONS['Other Ag Business'])
    return jsonify(suggestion)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

import re
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, session
import os

from agents import (
    ADVISOR_CLASSES, BASE_ADVISORS, OPTIONAL_ADVISORS, ALL_ADVISORS,
    BASE_ADVISOR_IDS, OPTIONAL_ADVISOR_IDS, BoardChair
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

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

conversation_histories = {}
user_profiles = {}

ADVISOR_ORDER = BASE_ADVISOR_IDS + OPTIONAL_ADVISOR_IDS


def get_active_advisors(session_id):
    user_profile = user_profiles.get(session_id, {})
    selected = user_profile.get('selected_advisors', [])
    active = {aid: ALL_ADVISORS[aid] for aid in BASE_ADVISOR_IDS}
    for advisor_id in selected:
        if advisor_id in OPTIONAL_ADVISORS:
            active[advisor_id] = OPTIONAL_ADVISORS[advisor_id]
    return active


def detect_specific_advisor(message, active_advisors):
    message_lower = message.lower()

    explicit_titles = {
        'financial': ['finance director', 'financial advisor', 'finance advisor'],
        'operations': ['operations manager', 'operations advisor'],
        'marketing': ['marketing specialist', 'marketing advisor'],
        'legal': ['legal specialist', 'legal advisor'],
        'risk': ['risk advisor', 'risk manager'],
        'commodity_risk': ['commodity risk advisor', 'commodity advisor', 'commodity risk specialist'],
        'livestock': ['livestock advisor', 'livestock specialist', 'animal systems advisor'],
        'sustainability': ['sustainability advisor', 'sustainability specialist'],
        'agronomist': ['agronomist advisor', 'crop advisor', 'crop specialist']
    }

    for advisor_id, titles in explicit_titles.items():
        if advisor_id not in active_advisors:
            continue
        for title in titles:
            if title in message_lower:
                return advisor_id

    directing_phrases = [
        'ask the', 'talk to', 'speak to', 'speak with',
        'from the', 'hey ', 'question for', 'advice from',
        'what does the', 'what would the', 'what does our',
        'what would our', 'can the', 'only the', 'just the',
        'i want the', "i'd like the", 'i need the',
        'let me ask', 'consult the', 'check with the',
        'directed at', 'only ask',
    ]

    has_directing_phrase = any(phrase in message_lower for phrase in directing_phrases)

    if has_directing_phrase:
        single_word_map = {
            'financial': ['finance', 'financial'],
            'operations': ['operations'],
            'marketing': ['marketing'],
            'legal': ['legal', 'lawyer', 'attorney'],
            'risk': ['risk'],
            'sustainability': ['sustainability'],
            'agronomist': ['agronomist', 'agronomy'],
            'livestock': ['livestock'],
            'commodity_risk': ['commodity risk'],
        }

        for advisor_id, keywords in single_word_map.items():
            if advisor_id not in active_advisors:
                continue
            for keyword in keywords:
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, message_lower):
                    return advisor_id

    return None


def get_advisor_response(advisor_id, message, session_id, user_profile):
    advisor_class = ADVISOR_CLASSES.get(advisor_id)
    if advisor_class:
        return advisor_class.get_response(message, session_id, user_profile, conversation_histories)
    return {
        'advisor_id': advisor_id,
        'response': "Advisor not found.",
        'title': "Unknown",
        'icon': "question"
    }


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

    user_profile = user_profiles.get(session_id)
    result = get_advisor_response(advisor_id, message, session_id, user_profile)

    if 'Error' in result.get('response', ''):
        return jsonify({'error': result['response']}), 500

    return jsonify({
        'response': result['response'],
        'advisor': {
            'title': result['title']
        }
    })


@app.route('/api/chat/all', methods=['POST'])
def chat_all():
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    ask_all = data.get('ask_all', False)

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

    routing_rationale = None
    if ask_all or len(active_advisors) <= 3:
        selected_ids = list(active_advisors.keys())
        routing_rationale = "All active advisors are weighing in on this question."
    else:
        selected_ids, routing_rationale = BoardChair.route(message, active_advisors, user_profile)

    selected_advisors = {aid: active_advisors[aid] for aid in selected_ids if aid in active_advisors}

    if not selected_advisors:
        selected_advisors = {aid: ALL_ADVISORS[aid] for aid in BASE_ADVISOR_IDS}
        routing_rationale = "Consulting core advisors for a comprehensive perspective."

    responses = []
    max_workers = max(1, len(selected_advisors))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_advisor_response, advisor_id, message, session_id, user_profile): advisor_id
            for advisor_id in selected_advisors.keys()
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                responses.append(result)
            except Exception as e:
                advisor_id = futures[future]
                advisor = selected_advisors[advisor_id]
                responses.append({
                    'advisor_id': advisor_id,
                    'response': f"Error: {str(e)}",
                    'title': advisor['title'],
                    'icon': advisor['icon']
                })

    responses.sort(key=lambda x: ADVISOR_ORDER.index(x['advisor_id']) if x['advisor_id'] in ADVISOR_ORDER else 99)

    summary = BoardChair.synthesize(message, responses, user_profile)

    selected_titles = [active_advisors[aid]['title'] for aid in selected_ids if aid in active_advisors]

    return jsonify({
        'mode': 'orchestrated',
        'routing': {
            'selected': selected_ids,
            'selected_titles': selected_titles,
            'rationale': routing_rationale
        },
        'responses': responses,
        'summary': summary
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
        'base': BASE_ADVISORS,
        'optional': OPTIONAL_ADVISORS
    })


@app.route('/api/suggestions/<business_type>')
def get_suggestions(business_type):
    suggestion = BOARD_SUGGESTIONS.get(business_type, BOARD_SUGGESTIONS['Other Ag Business'])
    return jsonify(suggestion)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

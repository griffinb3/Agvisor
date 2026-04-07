import re
import csv
import io
import json
import logging
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
import os
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

from data.financial_analysis import analyze_records, parse_chart_directive

from agents import (
    ADVISOR_CLASSES, BASE_ADVISORS, OPTIONAL_ADVISORS, ALL_ADVISORS,
    BASE_ADVISOR_IDS, OPTIONAL_ADVISOR_IDS, BoardChair
)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

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
    if not selected:
        return {aid: ALL_ADVISORS[aid] for aid in BASE_ADVISOR_IDS}
    return {aid: ALL_ADVISORS[aid] for aid in selected if aid in ALL_ADVISORS}


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


def get_advisor_response(advisor_id, message, session_id, user_profile, direct_mode=False, rag_context=None):
    advisor_class = ADVISOR_CLASSES.get(advisor_id)
    if advisor_class:
        return advisor_class.get_response(message, session_id, user_profile, conversation_histories,
                                          direct_mode=direct_mode, rag_context=rag_context)
    return {
        'advisor_id': advisor_id,
        'response': "Advisor not found.",
        'title': "Unknown",
        'icon': "question"
    }


@app.route('/')
def index():
    return render_template('index.html',
                           all_advisors=ALL_ADVISORS,
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
        'business_data_files': existing_profile.get('business_data_files', []),
        'uploaded_documents': existing_profile.get('uploaded_documents', []),
        'financial_analysis': existing_profile.get('financial_analysis', None),
    }

    return jsonify({'status': 'saved', 'profile': user_profiles[session_id]})


def _recompute_financial_analysis(profile):
    files = profile.get('business_data_files', [])
    if not files:
        profile.pop('financial_analysis', None)
        return
    all_headers = []
    all_rows = []
    for bdf in files:
        for h in bdf.get('headers', []):
            if h not in all_headers:
                all_headers.append(h)
        all_rows.extend(bdf.get('preview', []))
    result = analyze_records(all_headers, all_rows)
    profile['financial_analysis'] = result if result else None


@app.route('/api/upload-records', methods=['POST'])
def upload_records():
    session_id = request.form.get('session_id', 'default')

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        from data.file_parsers import parse_file
        file_bytes = file.read()
        filename = file.filename
        result = parse_file(file_bytes, filename)

        if session_id not in user_profiles:
            user_profiles[session_id] = {}

        profile = user_profiles[session_id]

        if result['type'] == 'tabular':
            if 'business_data_files' not in profile:
                profile['business_data_files'] = []
            profile['business_data_files'] = [f for f in profile['business_data_files'] if f.get('filename') != filename]
            profile['business_data_files'].append({
                'filename': filename,
                'summary': result['summary'],
                'headers': result['headers'],
                'preview': result['preview'],
                'row_count': result['row_count']
            })
            _recompute_financial_analysis(profile)
            return jsonify({
                'status': 'uploaded',
                'type': 'tabular',
                'filename': filename,
                'summary': result['summary'],
                'row_count': result['row_count']
            })
        else:
            if 'uploaded_documents' not in profile:
                profile['uploaded_documents'] = []
            profile['uploaded_documents'] = [d for d in profile['uploaded_documents'] if d.get('filename') != filename]
            profile['uploaded_documents'].append({
                'filename': filename,
                'format': result['format'],
                'text': result['text'],
                'summary': result['summary'],
                'word_count': result.get('word_count', 0),
                'page_count': result.get('page_count'),
                'paragraph_count': result.get('paragraph_count'),
                'line_count': result.get('line_count'),
            })
            return jsonify({
                'status': 'uploaded',
                'type': 'document',
                'filename': filename,
                'summary': result['summary'],
                'format': result['format'],
                'word_count': result.get('word_count', 0),
                'page_count': result.get('page_count'),
            })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400


@app.route('/api/remove-file', methods=['POST'])
def remove_file():
    data = request.json
    session_id = data.get('session_id', 'default')
    filename = data.get('filename')
    file_type = data.get('file_type')

    profile = user_profiles.get(session_id, {})

    if file_type == 'tabular':
        profile['business_data_files'] = [f for f in profile.get('business_data_files', []) if f.get('filename') != filename]
        _recompute_financial_analysis(profile)
    elif file_type == 'document':
        profile['uploaded_documents'] = [d for d in profile.get('uploaded_documents', []) if d.get('filename') != filename]

    return jsonify({'status': 'removed'})


@app.route('/api/get-files', methods=['GET'])
def get_files():
    session_id = request.args.get('session_id', 'default')
    profile = user_profiles.get(session_id, {})
    tabular = [
        {'filename': f['filename'], 'summary': f['summary'], 'row_count': f['row_count'], 'file_type': 'tabular'}
        for f in profile.get('business_data_files', [])
    ]
    documents = [
        {'filename': d['filename'], 'summary': d['summary'], 'word_count': d.get('word_count', 0), 'file_type': 'document'}
        for d in profile.get('uploaded_documents', [])
    ]
    return jsonify({'files': tabular + documents})


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
    result = get_advisor_response(advisor_id, message, session_id, user_profile, direct_mode=True)

    if 'Error' in result.get('response', ''):
        return jsonify({'error': result['response']}), 500

    response_text, chart_data = parse_chart_directive(result['response'], user_profile)

    resp = {
        'response': response_text,
        'advisor': {
            'title': result['title']
        }
    }
    if chart_data:
        resp['chart_data'] = chart_data
    return jsonify(resp)


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
        clean_text, chart_data = parse_chart_directive(result['response'], user_profile)
        result['response'] = clean_text
        single_resp = {'mode': 'single', 'responses': [result]}
        if chart_data:
            single_resp['chart_data'] = chart_data
        return jsonify(single_resp)

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

    shared_rag = None
    try:
        from data.rag import get_relevant_context
        state = user_profile.get('state') if user_profile else None
        btype = user_profile.get('business_type') if user_profile else None
        shared_rag = get_relevant_context(message, top_k=3, state_name=state, business_type=btype)
    except Exception as e:
        logger.warning(f"Failed to retrieve shared RAG context: {e}")

    responses = []
    max_workers = max(1, len(selected_advisors))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_advisor_response, advisor_id, message, session_id, user_profile,
                            False, shared_rag): advisor_id
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

    advisor_chart_data = None
    for r in responses:
        clean_text, cdata = parse_chart_directive(r['response'], user_profile)
        r['response'] = clean_text
        if cdata and advisor_chart_data is None:
            advisor_chart_data = cdata

    summary = BoardChair.synthesize(message, responses, user_profile)

    clean_summary, summary_chart_data = parse_chart_directive(summary, user_profile)
    if summary_chart_data:
        summary = clean_summary
        chart_data = summary_chart_data
    else:
        chart_data = advisor_chart_data

    selected_titles = [active_advisors[aid]['title'] for aid in selected_ids if aid in active_advisors]

    resp = {
        'mode': 'orchestrated',
        'routing': {
            'selected': selected_ids,
            'selected_titles': selected_titles,
            'rationale': routing_rationale
        },
        'responses': responses,
        'summary': summary
    }
    if chart_data:
        resp['chart_data'] = chart_data
    return jsonify(resp)


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    data = request.json
    message = data.get('message', '')
    advisor_id = data.get('advisor', 'financial')
    session_id = data.get('session_id', 'default')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    user_profile = user_profiles.get(session_id)
    advisor_class = ADVISOR_CLASSES.get(advisor_id)

    def generate():
        if not advisor_class:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Advisor not found'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'meta', 'advisor': {'title': advisor_class.title, 'icon': advisor_class.icon}})}\n\n"

        from agents.base import get_openai_client
        openai_client = get_openai_client()

        system_prompt = advisor_class.build_system_prompt(user_profile, direct_mode=True, message=message)

        try:
            from data.rag import get_relevant_context
            state = user_profile.get('state') if user_profile else None
            btype = user_profile.get('business_type') if user_profile else None
            rag_ctx = get_relevant_context(message, top_k=3, state_name=state, business_type=btype)
            if rag_ctx:
                system_prompt += f"\n\nRELEVANT REFERENCE DOCUMENTS (from USDA publications and extension guides — cite specific details when applicable):\n{rag_ctx}"
        except Exception:
            pass

        history_key = f"{session_id}_{advisor_id}"
        history = conversation_histories.get(history_key, [])
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        full_text = ''
        try:
            stream = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_completion_tokens=512,
                stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ''
                if delta:
                    full_text += delta
                    yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

            if history_key not in conversation_histories:
                conversation_histories[history_key] = []
            conversation_histories[history_key].append({"role": "user", "content": message})
            conversation_histories[history_key].append({"role": "assistant", "content": full_text})
            if len(conversation_histories[history_key]) > 20:
                conversation_histories[history_key] = conversation_histories[history_key][-20:]

            yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    )


@app.route('/api/chat/all/stream', methods=['POST'])
def chat_all_stream():
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    ask_all = data.get('ask_all', False)

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    user_profile = user_profiles.get(session_id)
    active_advisors = get_active_advisors(session_id)

    def generate():
        from agents.base import get_openai_client
        from agents.board_chair import SYNTHESIS_PROMPT
        openai_client = get_openai_client()

        specific_advisor = detect_specific_advisor(message, active_advisors)

        if specific_advisor:
            adv_class = ADVISOR_CLASSES.get(specific_advisor)
            adv_info = active_advisors.get(specific_advisor, {})
            yield f"data: {json.dumps({'type': 'meta', 'mode': 'single', 'advisor': {'title': adv_info.get('title', 'Advisor'), 'icon': adv_info.get('icon', 'user')}})}\n\n"

            system_prompt = adv_class.build_system_prompt(user_profile, direct_mode=False, message=message) if adv_class else ""
            try:
                from data.rag import get_relevant_context
                state = user_profile.get('state') if user_profile else None
                btype = user_profile.get('business_type') if user_profile else None
                rag_ctx = get_relevant_context(message, top_k=3, state_name=state, business_type=btype)
                if rag_ctx:
                    system_prompt += f"\n\nRELEVANT REFERENCE DOCUMENTS:\n{rag_ctx}"
            except Exception:
                pass

            history_key = f"{session_id}_{specific_advisor}"
            history = conversation_histories.get(history_key, [])
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": message})

            full_text = ''
            try:
                stream = openai_client.chat.completions.create(
                    model="gpt-4o-mini", messages=messages, max_completion_tokens=512, stream=True
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ''
                    if delta:
                        full_text += delta
                        yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

                if history_key not in conversation_histories:
                    conversation_histories[history_key] = []
                conversation_histories[history_key].append({"role": "user", "content": message})
                conversation_histories[history_key].append({"role": "assistant", "content": full_text})
                if len(conversation_histories[history_key]) > 20:
                    conversation_histories[history_key] = conversation_histories[history_key][-20:]

                yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        if ask_all or len(active_advisors) <= 3:
            selected_ids = list(active_advisors.keys())
            routing_rationale = "All active advisors are weighing in on this question."
        else:
            selected_ids, routing_rationale = BoardChair.route(message, active_advisors, user_profile)

        selected_advisors = {aid: active_advisors[aid] for aid in selected_ids if aid in active_advisors}
        if not selected_advisors:
            selected_advisors = {aid: ALL_ADVISORS[aid] for aid in BASE_ADVISOR_IDS}
            routing_rationale = "Consulting core advisors for a comprehensive perspective."

        selected_titles = [active_advisors[aid]['title'] for aid in selected_ids if aid in active_advisors]
        yield f"data: {json.dumps({'type': 'meta', 'mode': 'orchestrated', 'routing': {'selected': list(selected_advisors.keys()), 'selected_titles': selected_titles, 'rationale': routing_rationale}})}\n\n"

        shared_rag = None
        try:
            from data.rag import get_relevant_context
            state = user_profile.get('state') if user_profile else None
            btype = user_profile.get('business_type') if user_profile else None
            shared_rag = get_relevant_context(message, top_k=3, state_name=state, business_type=btype)
        except Exception:
            pass

        responses = []
        max_workers = max(1, len(selected_advisors))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(get_advisor_response, aid, message, session_id, user_profile,
                                False, shared_rag): aid
                for aid in selected_advisors.keys()
            }
            for future in as_completed(futures):
                try:
                    responses.append(future.result())
                except Exception as e:
                    aid = futures[future]
                    adv = selected_advisors[aid]
                    responses.append({'advisor_id': aid, 'response': f"Error: {str(e)}",
                                      'title': adv['title'], 'icon': adv['icon']})

        responses.sort(key=lambda x: ADVISOR_ORDER.index(x['advisor_id']) if x['advisor_id'] in ADVISOR_ORDER else 99)
        yield f"data: {json.dumps({'type': 'advisor_responses', 'responses': responses})}\n\n"

        responses_text = ""
        for resp in responses:
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

        synth_messages = [
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": f"User's original question: {message}\n{context}\n\nAdvisor responses:{responses_text}\n\nProvide a concise board summary synthesizing the above responses."}
        ]

        full_text = ''
        try:
            stream = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=synth_messages,
                max_completion_tokens=512,
                stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ''
                if delta:
                    full_text += delta
                    yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    )


@app.route('/api/charts', methods=['GET'])
def get_charts():
    session_id = request.args.get('session_id', 'default')
    user_profile = user_profiles.get(session_id, {})

    business_data_files = user_profile.get('business_data_files', [])
    if not business_data_files:
        return jsonify({'has_data': False, 'message': 'No financial data uploaded'})

    all_headers = []
    all_rows = []
    for bdf in business_data_files:
        for h in bdf.get('headers', []):
            if h not in all_headers:
                all_headers.append(h)
        all_rows.extend(bdf.get('preview', []))

    try:
        from data.financial_analysis import get_chart_data
        chart_data = get_chart_data(all_rows, all_headers)
    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return jsonify({'has_data': False, 'message': 'Could not generate chart data'})

    return jsonify(chart_data)


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


def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def estimate_time(desc):
    lower = desc.lower()
    if any(w in lower for w in ['hire', 'launch', 'expand', 'certify', 'train', 'construct', 'build']):
        return '1–3 months'
    if any(w in lower for w in ['plan', 'budget', 'monitor', 'track', 'evaluate', 'assess', 'develop strategy']):
        return '2–4 weeks'
    if any(w in lower for w in ['implement', 'set up', 'create', 'prepare', 'install', 'configure', 'establish', 'update']):
        return '1–2 weeks'
    if any(w in lower for w in ['contact', 'call', 'schedule', 'apply', 'submit', 'register', 'sign up', 'enroll']):
        return '3–5 days'
    if any(w in lower for w in ['review', 'check', 'read', 'research', 'verify', 'confirm', 'look into', 'explore']):
        return '1–2 days'
    return '1–2 weeks'


ACTION_VERBS = [
    'review', 'contact', 'apply', 'submit', 'schedule', 'create', 'implement',
    'consider', 'explore', 'develop', 'build', 'monitor', 'track', 'update',
    'register', 'evaluate', 'research', 'check', 'verify', 'consult', 'plan',
    'budget', 'prepare', 'establish', 'set up', 'identify', 'assess', 'secure',
    'obtain', 'pursue', 'negotiate', 'diversify', 'reduce', 'increase',
    'analyze', 'ensure', 'leverage', 'optimize', 'upgrade', 'expand', 'hire',
    'train', 'certify', 'enroll', 'sign up', 'reach out', 'look into',
]

ACTION_PHRASES = [
    'you should', 'you need to', 'you must', 'you could', 'you can',
    'we recommend', 'we suggest', 'it is recommended', 'consider',
    'next step', 'key action', 'prioritize', 'focus on', 'make sure',
    'take advantage', 'take action', 'important to',
]


def _classify_item(desc):
    lower = desc.lower()
    priority = 'medium'
    if any(w in lower for w in ['immediate', 'urgent', 'critical', 'asap', 'right away', 'now']):
        priority = 'high'
    elif any(w in lower for w in ['consider', 'optional', 'long-term', 'eventually', 'when possible']):
        priority = 'low'
    return priority, estimate_time(desc)


def extract_action_items(text, advisor_source=None):
    """Extract bullet-point action items from text."""
    items = []
    for line in text.strip().split('\n'):
        stripped = line.strip()
        match = re.match(r'^(?:\d+[\.\)]\s*|[-*•]\s+)(.*)', stripped)
        if match:
            desc = match.group(1).strip()
            if len(desc) > 10:
                priority, te = _classify_item(desc)
                items.append({
                    'description': desc,
                    'advisor_source': advisor_source,
                    'priority': priority,
                    'time_estimate': te
                })
    return items


def extract_prose_action_items(text, advisor_source=None):
    """Extract action items from paragraph prose by detecting imperative/recommendation sentences."""
    items = []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    seen = set()
    for sent in sentences:
        sent = sent.strip().strip('"\'')
        if len(sent) < 15 or len(sent) > 250:
            continue
        lower = sent.lower()
        is_action = (
            any(lower.startswith(v) for v in ACTION_VERBS) or
            any(p in lower for p in ACTION_PHRASES)
        )
        if not is_action:
            continue
        clean = re.sub(r'^(you should|you need to|you must|we recommend that you|we suggest you?)\s+', '', sent, flags=re.IGNORECASE).strip()
        clean = clean.rstrip('.')
        if len(clean) < 12:
            continue
        key = clean.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        priority, te = _classify_item(clean)
        items.append({
            'description': clean,
            'advisor_source': advisor_source,
            'priority': priority,
            'time_estimate': te
        })
    return items


ESTIMATE_DAYS = {
    '1–2 days':  2,
    '3–5 days':  5,
    '1–2 weeks': 14,
    '2–4 weeks': 28,
    '1–3 months': 45,
}
PRIORITY_OFFSET = {'high': 0, 'medium': 3, 'low': 7}


def suggest_due_date(time_estimate, priority='medium', stagger=0):
    """Return a suggested due date based on time estimate, priority, and position."""
    base = ESTIMATE_DAYS.get(time_estimate, 14)
    p_off = PRIORITY_OFFSET.get(priority, 0)
    total = base + p_off + (stagger * 2)
    return (date.today() + timedelta(days=total)).isoformat()


def _get_session_id():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    return session['session_id']


@app.route('/api/plans', methods=['POST'])
def create_plan():
    data = request.json
    session_id = _get_session_id()
    title = data.get('title', 'Action Plan')
    items = data.get('items', [])
    advisor_response = data.get('advisor_response', '')
    advisor_source = data.get('advisor_source', None)
    advisor_responses = data.get('advisor_responses', [])

    if not items:
        if advisor_responses:
            seen_descs = set()
            for ar in advisor_responses:
                src = ar.get('advisor_id') or ar.get('advisor_source') or advisor_source
                text = ar.get('response', '')
                bullet_items = extract_action_items(text, src)
                prose_items = extract_prose_action_items(text, src) if not bullet_items else []
                for it in (bullet_items or prose_items):
                    key = it['description'].lower()[:80]
                    if key not in seen_descs:
                        seen_descs.add(key)
                        items.append(it)
        if not items and advisor_response:
            items = extract_action_items(advisor_response, advisor_source)
            if not items:
                items = extract_prose_action_items(advisor_response, advisor_source)

    if not items:
        return jsonify({'error': 'No action items could be extracted or provided'}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO action_plans (session_id, title) VALUES (%s, %s) RETURNING id, created_at",
                (session_id, title)
            )
            plan_row = cur.fetchone()
            plan_id = plan_row[0]
            plan_created_at = plan_row[1]

            created_items = []
            priority_stagger = {'high': 0, 'medium': 0, 'low': 0}
            for item in items:
                desc = item.get('description', '')
                priority = item.get('priority', 'medium')
                te = item.get('time_estimate') or estimate_time(desc)
                due_date = item.get('due_date') or suggest_due_date(
                    te, priority, priority_stagger.get(priority, 0)
                )
                priority_stagger[priority] = priority_stagger.get(priority, 0) + 1
                cur.execute(
                    """INSERT INTO action_items (plan_id, description, advisor_source, priority, due_date, notes, time_estimate)
                       VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, created_at""",
                    (plan_id, desc,
                     item.get('advisor_source', advisor_source),
                     priority,
                     due_date,
                     item.get('notes', None),
                     te)
                )
                item_row = cur.fetchone()
                created_items.append({
                    'id': item_row[0],
                    'description': desc,
                    'advisor_source': item.get('advisor_source', advisor_source),
                    'priority': priority,
                    'status': 'pending',
                    'due_date': due_date,
                    'notes': item.get('notes', None),
                    'time_estimate': te,
                    'created_at': item_row[1].isoformat()
                })
        conn.commit()
        conn.close()

        return jsonify({
            'id': plan_id,
            'session_id': session_id,
            'title': title,
            'status': 'active',
            'created_at': plan_created_at.isoformat(),
            'items': created_items
        }), 201
    except Exception:
        return jsonify({'error': 'Failed to create plan'}), 500


@app.route('/api/plans', methods=['GET'])
def get_plans():
    session_id = _get_session_id()
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM action_plans WHERE session_id = %s AND status != 'archived' ORDER BY created_at DESC",
                (session_id,)
            )
            plans = cur.fetchall()

            result = []
            for plan in plans:
                cur.execute(
                    "SELECT * FROM action_items WHERE plan_id = %s ORDER BY created_at ASC",
                    (plan['id'],)
                )
                items = cur.fetchall()
                plan_dict = dict(plan)
                plan_dict['created_at'] = plan_dict['created_at'].isoformat()
                plan_dict['items'] = []
                for item in items:
                    item_dict = dict(item)
                    item_dict['created_at'] = item_dict['created_at'].isoformat()
                    if item_dict.get('due_date'):
                        item_dict['due_date'] = item_dict['due_date'].isoformat()
                    plan_dict['items'].append(item_dict)
                result.append(plan_dict)
        conn.close()
        return jsonify(result)
    except Exception:
        return jsonify({'error': 'Failed to fetch plans'}), 500


@app.route('/api/plans/<int:plan_id>/items/<int:item_id>', methods=['PUT'])
def update_plan_item(plan_id, item_id):
    session_id = _get_session_id()
    data = request.json
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ap.id FROM action_plans ap JOIN action_items ai ON ai.plan_id = ap.id WHERE ap.id = %s AND ai.id = %s AND ap.session_id = %s",
                (plan_id, item_id, session_id)
            )
            if not cur.fetchone():
                conn.close()
                return jsonify({'error': 'Item not found'}), 404

            updates = []
            values = []
            allowed_fields = ['status', 'priority', 'notes', 'due_date', 'description', 'time_estimate']
            for field in allowed_fields:
                if field in data:
                    updates.append(f"{field} = %s")
                    values.append(data[field])

            if not updates:
                conn.close()
                return jsonify({'error': 'No fields to update'}), 400

            values.extend([item_id, plan_id])
            cur.execute(
                f"UPDATE action_items SET {', '.join(updates)} WHERE id = %s AND plan_id = %s",
                values
            )
        conn.commit()
        conn.close()
        return jsonify({'status': 'updated'})
    except Exception:
        return jsonify({'error': 'Failed to update item'}), 500


@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    session_id = _get_session_id()
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM action_plans WHERE id = %s AND session_id = %s", (plan_id, session_id))
            if not cur.fetchone():
                conn.close()
                return jsonify({'error': 'Plan not found'}), 404
            cur.execute("UPDATE action_plans SET status = 'archived' WHERE id = %s", (plan_id,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'archived'})
    except Exception:
        return jsonify({'error': 'Failed to delete plan'}), 500


if __name__ == '__main__':
    try:
        from seed_state_data import seed_all
        seed_all()
    except Exception as e:
        print(f"Note: Could not initialize state data: {e}")
    try:
        from data.rag import seed_rag_documents
        seed_rag_documents()
    except Exception as e:
        print(f"Note: Could not seed RAG documents: {e}")
    app.run(host='0.0.0.0', port=5000, debug=True)

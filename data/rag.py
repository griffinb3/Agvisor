import os
import re
import math
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter

logger = logging.getLogger(__name__)

_idf_cache = {}
_doc_count_cache = {}


def _get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])


STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'can', 'shall', 'not', 'no', 'nor',
    'so', 'if', 'then', 'than', 'that', 'this', 'these', 'those', 'it',
    'its', 'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she',
    'they', 'them', 'their', 'what', 'which', 'who', 'whom', 'how',
    'when', 'where', 'why', 'all', 'each', 'any', 'both', 'few', 'more',
    'most', 'some', 'such', 'about', 'up', 'out', 'just', 'also', 'very',
    'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
}


def _tokenize(text):
    words = re.findall(r'[a-z0-9]+', text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


def _compute_tf(tokens):
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {word: count / total for word, count in counts.items()}


def _compute_relevance(query_tokens, doc_tokens, doc_category, query_text):
    if not query_tokens or not doc_tokens:
        return 0.0

    query_tf = _compute_tf(query_tokens)
    doc_tf = _compute_tf(doc_tokens)

    shared_terms = set(query_tokens) & set(doc_tokens)
    if not shared_terms:
        return 0.0

    score = 0.0
    for term in shared_terms:
        score += query_tf.get(term, 0) * doc_tf.get(term, 0)

    coverage = len(shared_terms) / len(set(query_tokens))
    score = score * (0.5 + 0.5 * coverage)

    category_keywords = {
        'financial': ['loan', 'credit', 'finance', 'money', 'cost', 'budget', 'debt', 'grant', 'funding', 'investment', 'capital'],
        'risk': ['insurance', 'risk', 'crop insurance', 'disaster', 'protection', 'coverage', 'loss', 'claim'],
        'crop': ['crop', 'plant', 'seed', 'soil', 'harvest', 'yield', 'irrigation', 'fertilizer', 'pest', 'weed'],
        'livestock': ['cattle', 'livestock', 'herd', 'animal', 'beef', 'dairy', 'poultry', 'feed', 'breeding', 'veterinary'],
        'sustainability': ['conservation', 'sustainable', 'environment', 'carbon', 'organic', 'water quality', 'erosion', 'habitat'],
        'marketing': ['market', 'sell', 'price', 'buyer', 'brand', 'direct', 'wholesale', 'value added', 'consumer'],
    }

    query_lower = query_text.lower()
    if doc_category in category_keywords:
        for kw in category_keywords[doc_category]:
            if kw in query_lower:
                score *= 1.5
                break

    return score


def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break

    return chunks


def create_rag_documents_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id SERIAL PRIMARY KEY,
                source VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding TEXT,
                state_relevance VARCHAR,
                business_type_relevance VARCHAR
            );
        """)
    conn.commit()


def store_document(source, category, title, text, state_relevance=None, business_type_relevance=None):
    chunks = chunk_text(text)
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(
                    """INSERT INTO rag_documents 
                       (source, category, title, chunk_text, state_relevance, business_type_relevance)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (source, category, title, chunk, state_relevance, business_type_relevance)
                )
        conn.commit()
        logger.info(f"Stored {len(chunks)} chunks for '{title}'")
        return len(chunks)
    except Exception as e:
        logger.error(f"Failed to store document: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def search_similar(query_text, top_k=5, category=None, state_name=None, business_type=None):
    conn = _get_connection()
    try:
        conditions = []
        params = []

        if category:
            conditions.append("category = %s")
            params.append(category)

        if state_name:
            conditions.append("(state_relevance IS NULL OR state_relevance = %s)")
            params.append(state_name)

        if business_type:
            conditions.append("(business_type_relevance IS NULL OR business_type_relevance = %s)")
            params.append(business_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"SELECT id, source, category, title, chunk_text FROM rag_documents WHERE {where_clause}",
                params
            )
            rows = cur.fetchall()

        if not rows:
            return []

        query_tokens = _tokenize(query_text)
        if not query_tokens:
            return []

        results = []
        for row in rows:
            doc_tokens = _tokenize(row['chunk_text'] + ' ' + row['title'])
            score = _compute_relevance(query_tokens, doc_tokens, row['category'], query_text)
            if score > 0:
                results.append({
                    'id': row['id'],
                    'source': row['source'],
                    'category': row['category'],
                    'title': row['title'],
                    'chunk_text': row['chunk_text'],
                    'similarity': score
                })

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return []
    finally:
        conn.close()


DOCUMENT_REGISTRY = [
    {
        "file": "usda_fsa_loans.md",
        "source": "USDA FSA",
        "category": "financial",
        "title": "FSA Loan Programs"
    },
    {
        "file": "usda_nrcs_programs.md",
        "source": "USDA NRCS",
        "category": "sustainability",
        "title": "NRCS Conservation Programs"
    },
    {
        "file": "crop_insurance_basics.md",
        "source": "USDA RMA",
        "category": "risk",
        "title": "Federal Crop Insurance Guide"
    },
    {
        "file": "financial_planning_ag.md",
        "source": "Extension Service",
        "category": "financial",
        "title": "Financial Planning for Ag Businesses"
    },
    {
        "file": "crop_production_practices.md",
        "source": "Extension Service",
        "category": "crop",
        "title": "Crop Production Best Practices"
    },
    {
        "file": "livestock_management.md",
        "source": "Extension Service",
        "category": "livestock",
        "title": "Livestock Management Guide"
    },
    {
        "file": "marketing_value_added.md",
        "source": "Extension Service",
        "category": "marketing",
        "title": "Marketing and Value-Added Agriculture"
    },
    {
        "file": "risk_management_insurance.md",
        "source": "USDA RMA",
        "category": "risk",
        "title": "Risk Management and Insurance Programs"
    },
    {
        "file": "beginning_farmer_resources.md",
        "source": "USDA",
        "category": "financial",
        "title": "Beginning Farmer Resources"
    },
    {
        "file": "sustainability_conservation.md",
        "source": "USDA NRCS",
        "category": "sustainability",
        "title": "Sustainability and Conservation Programs"
    },
]


def seed_rag_documents():
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM rag_documents")
            count = cur.fetchone()[0]
            if count > 0:
                logger.info(f"RAG documents already seeded ({count} chunks). Skipping.")
                return count

        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag_documents")
        total_chunks = 0

        for doc in DOCUMENT_REGISTRY:
            file_path = os.path.join(docs_dir, doc["file"])
            if not os.path.exists(file_path):
                logger.warning(f"RAG document not found: {file_path}")
                continue

            with open(file_path, "r") as f:
                text = f.read()

            chunks_stored = store_document(
                source=doc["source"],
                category=doc["category"],
                title=doc["title"],
                text=text,
            )
            total_chunks += chunks_stored

        logger.info(f"RAG seeding complete: {total_chunks} total chunks stored")
        return total_chunks

    except Exception as e:
        logger.error(f"Failed to seed RAG documents: {e}")
        return 0
    finally:
        conn.close()


def get_relevant_context(query_text, top_k=3, state_name=None, business_type=None):
    results = search_similar(
        query_text,
        top_k=top_k,
        state_name=state_name,
        business_type=business_type
    )

    if not results:
        return None

    min_score = 0.001
    sections = []
    for r in results:
        if r['similarity'] < min_score:
            continue
        sections.append(f"[{r['title']}] ({r['source']} — {r['category']})\n{r['chunk_text']}")

    if not sections:
        return None

    return "\n\n---\n\n".join(sections)

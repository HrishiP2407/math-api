from flask import Flask, request, jsonify
import requests
import re
import os

app = Flask(__name__)

def extract_numbers(query):
    return [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', query)]

def clean_number(result):
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return round(result, 4)

def detect_operation(query):
    q = query.lower()
    if re.search(r'\bmultiply\b|\bproduct\b|\btimes\b', q) or '*' in q:
        return 'multiply'
    if re.search(r'\bdivide\b|\bdivision\b|\bquotient\b|\bdivided\b|\bper\b', q) or '/' in q:
        return 'divide'
    if re.search(r'\bsubtract\b|\bdifference\b|\bminus\b|\bdeduct\b|\bless\b|\bfrom\b', q):
        return 'subtract'
    if re.search(r'\badd\b|\bsum\b|\bplus\b|\btotal\b|\baddition\b', q) or '+' in q:
        return 'add'
    return None

def is_prime(n):
    n = int(n)
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def filter_numbers(numbers, query):
    q = query.lower()
    if re.search(r'\beven\b', q):
        return [n for n in numbers if int(n) % 2 == 0]
    if re.search(r'\bodd\b', q):
        return [n for n in numbers if int(n) % 2 != 0]
    if re.search(r'\bprime\b', q):
        return [n for n in numbers if is_prime(n)]
    if re.search(r'\bpositive\b', q):
        return [n for n in numbers if n > 0]
    if re.search(r'\bnegative\b', q):
        return [n for n in numbers if n < 0]
    return numbers

def handle_math(query):
    numbers = extract_numbers(query)
    if not numbers:
        return None
    op = detect_operation(query)
    if op is None:
        return None

    # Apply any filters (even, odd, prime, etc.)
    filtered = filter_numbers(numbers, query)
    if not filtered:
        return "0"

    q = query.lower()

    if op == 'add':
        result = sum(filtered)
    elif op == 'multiply':
        result = 1
        for n in filtered:
            result *= n
    elif op == 'subtract':
        if len(filtered) == 2:
            a, b = filtered[0], filtered[1]
            result = b - a if re.search(r'\bfrom\b', q) else a - b
        else:
            result = filtered[0]
            for n in filtered[1:]:
                result -= n
    elif op == 'divide':
        if len(filtered) < 2:
            return None
        a, b = filtered[0], filtered[1]
        if b == 0:
            return "Division by zero is not allowed."
        result = a / b

    result = clean_number(result)
    return str(result)

def call_groq(query):
    api_key = os.environ.get("GROQ_API_KEY", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise answer engine. Answer in the shortest way possible. For YES/NO questions reply only YES or NO in uppercase. For math reply like 'The sum is 25.' For facts give only the direct answer. No explanation. No extra words."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "max_tokens": 100,
        "temperature": 0
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=15
    )
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

@app.route('/v1/answer', methods=['POST'])
def answer():
    try:
        data = request.get_json(force=True)
        query = data.get('query', '').strip()

        math_result = handle_math(query)
        if math_result:
            return jsonify({"output": math_result})

        output = call_groq(query)
        return jsonify({"output": output})

    except Exception as e:
        return jsonify({"output": f"Error: {str(e)}"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "running", "endpoint": "POST /v1/answer"})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
"""
Mobile-friendly Meeting Assistant UI.

This is a separate UI design branch for the Interface.ai project.
It provides a clean, mobile-first web interface similar to the
meeting assistant design shared by the user.
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json
import re
import urllib.request
import urllib.error

app = Flask(__name__)

OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'llama3.2:latest'


def call_ollama(prompt, model=OLLAMA_MODEL):
    """Call a local Ollama instance and return the generated text."""
    system = (
        'You are a meeting summary assistant. You always summarize the provided transcript. '
        'Never say the transcript is too short. Never ask for more information. '
        'Never explain that you cannot do it. Always output plain text bullet points.'
    )
    payload = json.dumps({
        'model': model,
        'system': system,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.2, 'num_predict': 200}
    }).encode('utf-8')

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('response', '').strip()
    except urllib.error.HTTPError as e:
        return f'<strong>Ollama error</strong><br>Status {e.code}: {e.read().decode("utf-8")}'
    except Exception as e:
        return f'<strong>Could not reach Ollama</strong><br>{str(e)}'


def build_prompt(option, transcript='', previous=''):
    """Build a prompt for the requested summary option."""
    label = option.replace('_', ' ').replace('-', ' ').title()

    # Strip HTML from previous summary so the prompt stays plain text
    previous_plain = re.sub(r'<[^>]+>', '', previous)

    if transcript:
        parts = []
        if previous:
            parts.append(f'Here is the previous {label} summary:\n\n{previous_plain}\n\n')
        parts.append(f'Here is the new meeting transcript:\n\n{transcript}\n\n')
        if previous_plain.strip():
            parts.append(
                f'You are a meeting assistant. Generate an updated, concise meeting {label} that combines '
                f'the previous summary with the new transcript. '
                f'Return the result as plain text using bullet points (•) and line breaks. '
                f'Do not use any HTML tags. Keep it under 8 lines. '
                f'Even if the transcript is short, do your best to extract useful points. '
                f'Do not ask for more information. Do not say you cannot do it. Just provide the summary.'
            )
        else:
            parts.append(
                f'You are a meeting assistant. Generate a concise meeting {label} from the transcript. '
                f'Return the result as plain text using bullet points (•) and line breaks. '
                f'Do not use any HTML tags. Keep it under 8 lines. '
                f'Even if the transcript is short, do your best to extract useful points. '
                f'Do not ask for more information. Do not say you cannot do it. Just provide the summary.'
            )
        return '\n'.join(parts)

    return (
        f'You are a meeting assistant. Generate a concise meeting {label} '
        f'for a weekly sync that covered Q4 roadmap, migration project progress, '
        f'testing allocation, and a follow-up meeting on Friday. '
        f'Return the result as plain text using bullet points (•) and line breaks. '
        f'Do not use any HTML tags. Keep it under 6 lines.'
    )


def generate_summary_content(option, transcript='', previous=''):
    """Generate an AI summary using local Ollama."""
    if not transcript or not transcript.strip():
        return {
            'title': 'AI ' + option.replace('_', ' ').replace('-', ' ').title(),
            'text': 'No transcript yet\nStart recording and speak to generate a real summary.'
        }

    prompt = build_prompt(option, transcript, previous)
    response = call_ollama(prompt)

    # Clean up common prompt failures, meta responses, stray HTML and special chars
    response = response.replace('Not enough content to summarize.', '').strip()
    response = re.sub(r'<[^>]+>', '', response)
    response = response.replace('\u2022', '-')
    response = response.strip()

    # Remove meta responses where Ollama asks for more info or complains
    meta_phrases = [
        r"I'm ready to assist.*?(?:\.|\n)",
        r"I don't see a previous.*?(?:\.|\n)",
        r"I don't see a transcript.*?(?:\.|\n)",
        r"Previous meeting summary not provided.*?(?:\.|\n)",
        r"Please provide it.*?(?:\.|\n)",
        r"Please share.*?(?:\.|\n)",
        r"I can help.*?(?:\.|\n)",
        r"If you have any questions.*?(?:\.|\n)",
        r"Let me know.*?(?:\.|\n)",
        r"However,.*?(?:\.|\n)",
        r"Unfortunately.*?\.",
        r"I cannot provide.*?(?:\.|\n)",
    ]
    for pattern in meta_phrases:
        response = re.sub(pattern, '', response, flags=re.IGNORECASE).strip()

    if not response or not response.strip('•').strip():
        response = 'No usable summary could be generated.\n• Try speaking more clearly\n• Check that the transcript captured your voice'

    label = option.replace('_', ' ').replace('-', ' ').title()
    if not response.startswith(label):
        response = f'{label}\n{response}'

    return {
        'title': 'AI ' + label,
        'text': response
    }


@app.route('/')
def meeting_assistant():
    """Render the meeting assistant mobile UI."""
    return render_template('index.html', active_tab='meeting')


@app.route('/home')
def home():
    """Home view placeholder."""
    return render_template('index.html', active_tab='home')


@app.route('/activity')
def activity():
    """Activity view placeholder."""
    return render_template('index.html', active_tab='activity')


@app.route('/meeting')
def meeting():
    """Meeting view (default)."""
    return render_template('index.html', active_tab='meeting')


@app.route('/profile')
def profile():
    """Profile view placeholder."""
    return render_template('index.html', active_tab='profile')


@app.route('/settings')
def settings():
    """Settings view placeholder."""
    return render_template('index.html', active_tab='settings')


@app.route('/api/summary', methods=['GET', 'POST'])
def api_summary():
    """Return AI-generated summary content for the requested option."""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        option = data.get('option', 'summary')
        transcript = data.get('transcript', '')
        previous = data.get('previous', '')
    else:
        option = request.args.get('option', 'summary')
        transcript = request.args.get('transcript', '')
        previous = request.args.get('previous', '')

    content = generate_summary_content(option, transcript, previous)
    return jsonify({
        'option': option,
        'title': content['title'],
        'text': content['text'],
        'generated_at': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

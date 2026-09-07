"""
Mobile-friendly Meeting Assistant UI.

This is a separate UI design branch for the Interface.ai project.
It provides a clean, mobile-first web interface similar to the
meeting assistant design shared by the user.
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json
import urllib.request
import urllib.error

app = Flask(__name__)

OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'llama3.2:latest'


def call_ollama(prompt, model=OLLAMA_MODEL):
    """Call a local Ollama instance and return the generated text."""
    payload = json.dumps({
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.4}
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


def build_prompt(option):
    """Build a prompt for the requested summary option."""
    label = option.replace('_', ' ').replace('-', ' ').title()

    return (
        f'You are a meeting assistant. Generate a concise meeting {label} '
        f'for a weekly sync that covered Q4 roadmap, migration project progress, '
        f'testing allocation, and a follow-up meeting on Friday. '
        f'Return the result as a short HTML snippet using only <strong> and <br> tags '
        f'and bullet points (•). Keep it under 6 lines. Do not include markdown code blocks.'
    )


def generate_summary_content(option):
    """Generate an AI summary using local Ollama."""
    prompt = build_prompt(option)
    response = call_ollama(prompt)

    return {
        'title': 'AI ' + option.replace('_', ' ').replace('-', ' ').title(),
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


@app.route('/api/summary')
def api_summary():
    """Return AI-generated summary content for the requested option."""
    option = request.args.get('option', 'summary')
    content = generate_summary_content(option)
    return jsonify({
        'option': option,
        'title': content['title'],
        'text': content['text'],
        'generated_at': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

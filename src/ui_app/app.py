"""
Mobile-friendly Meeting Assistant UI.

This is a separate UI design branch for the Interface.ai project.
It provides a clean, mobile-first web interface similar to the
meeting assistant design shared by the user.
"""

from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)


def generate_summary_content(option):
    """Generate a mock AI summary for the requested option type."""
    templates = {
        'summary': {
            'title': 'AI Summary',
            'text': ('<strong>Meeting Summary</strong><br><br>'
                     '<strong>Key Points:</strong><br>'
                     '• Discussed Q4 roadmap and priorities<br>'
                     '• Reviewed progress on migration project<br>'
                     '• Action items assigned to team leads<br>'
                     '• Follow-up meeting scheduled for Friday')
        },
        'qa': {
            'title': 'Questions & Answers',
            'text': ('<strong>Q: What is the deadline for the migration?</strong><br>'
                     'A: End of Q4.<br><br>'
                     '<strong>Q: Who owns the testing allocation?</strong><br>'
                     'A: Jane Doe will coordinate with QA.<br><br>'
                     '<strong>Q: Next follow-up?</strong><br>'
                     'A: Friday at 2 PM.')
        },
        'actions': {
            'title': 'Action Items',
            'text': ('<strong>Action Items</strong><br><br>'
                     '• John: Draft architecture proposal by Monday<br>'
                     '• Jane: Allocate QA resources by Wednesday<br>'
                     '• Team: Review migration plan before Friday<br>'
                     '• All: Update project timeline in Jira')
        },
        'decisions': {
            'title': 'Decisions',
            'text': ('<strong>Decisions Made</strong><br><br>'
                     '• Move forward with the new architecture proposal<br>'
                     '• Allocate additional QA resources for testing<br>'
                     '• Keep weekly sync cadence until launch<br>'
                     '• Escalate blockers to leadership within 24 hours')
        }
    }

    if option in templates:
        return templates[option]

    label = option.replace('_', ' ').replace('-', ' ').title()
    return {
        'title': 'AI ' + label,
        'text': ('<strong>' + label + '</strong><br><br>'
                 '• Key ' + label.lower() + ' point 1 from the discussion<br>'
                 '• Key ' + label.lower() + ' point 2 captured by AI<br>'
                 '• Relevant ' + label.lower() + ' detail from the meeting<br>'
                 '• Follow-up consideration for ' + label.lower())
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


@app.route('/api/summary/<option>')
def api_summary(option):
    """Return AI-generated summary content for the requested option."""
    content = generate_summary_content(option)
    return jsonify({
        'option': option,
        'title': content['title'],
        'text': content['text'],
        'generated_at': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

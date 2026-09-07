"""
Mobile-friendly Meeting Assistant UI.

This is a separate UI design branch for the Interface.ai project.
It provides a clean, mobile-first web interface similar to the
meeting assistant design shared by the user.
"""

from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def meeting_assistant():
    """Render the meeting assistant mobile UI."""
    return render_template('index.html')


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

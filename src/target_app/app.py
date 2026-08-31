"""
Legacy-like bank admin console target application.

This is a simple Flask application that mimics a legacy bank admin console
with table-based layouts, no test IDs, and dynamic IDs - typical of the
real-world bank applications this system is designed to automate.

It provides a multi-step flow: member lookup → account details → update balance.
"""

from flask import Flask, render_template_string, request, redirect, url_for, session
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dev-secret-key-for-demo-only'

# Mock database of members
MEMBERS_DB = {
    "12345": {
        "name": "John Smith",
        "savings_balance": 5432.10,
        "checking_balance": 1234.56,
        "account_status": "Active",
        "member_since": "2020-01-15"
    },
    "67890": {
        "name": "Jane Doe",
        "savings_balance": 9876.54,
        "checking_balance": 3456.78,
        "account_status": "Active",
        "member_since": "2019-06-20"
    },
    "11111": {
        "name": "Bob Johnson",
        "savings_balance": 0.00,
        "checking_balance": 100.00,
        "account_status": "Inactive",
        "member_since": "2021-03-10"
    }
}

# Legacy-style HTML templates (table-based, no test IDs, dynamic IDs)
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Bank Admin Console</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }
        .header { background-color: #003366; color: white; padding: 10px; }
        .container { background-color: white; padding: 20px; margin-top: 20px; }
        table { border-collapse: collapse; width: 100%; }
        td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #003366; color: white; }
        input[type="text"] { padding: 5px; width: 200px; }
        input[type="submit"] { padding: 8px 16px; background-color: #003366; color: white; border: none; cursor: pointer; }
        input[type="submit"]:hover { background-color: #004488; }
        .error { color: red; font-weight: bold; }
        .success { color: green; font-weight: bold; }
        .nav-bar { background-color: #cccccc; padding: 10px; margin-bottom: 20px; }
        .nav-bar a { margin-right: 20px; text-decoration: none; color: #003366; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Legacy Bank Admin Console v2.1</h1>
    </div>
    <div class="nav-bar">
        <a href="/">Home</a>
        <a href="/lookup">Member Lookup</a>
        <a href="/accounts">Account Management</a>
    </div>
    <div class="container">
        {{ content|safe }}
    </div>
</body>
</html>
"""


@app.route('/')
def home():
    """Home page with system status."""
    return render_template_string(HOME_TEMPLATE, content=f"""
<h2>Welcome to Bank Admin Console</h2>
<table>
    <tr>
        <td><strong>System Status:</strong></td>
        <td>Online</td>
    </tr>
    <tr>
        <td><strong>Last Backup:</strong></td>
        <td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
    </tr>
    <tr>
        <td><strong>Active Sessions:</strong></td>
        <td>{random.randint(1, 10)}</td>
    </tr>
</table>
<p>Use the navigation bar above to access system functions.</p>
""")


@app.route('/lookup', methods=['GET', 'POST'])
def lookup():
    """Member lookup page."""
    error = None
    success = None
    member = None
    member_id = request.form.get('member_id') or request.args.get('member_id', '')
    random_id = str(random.randint(10000, 99999))
    
    if request.method == 'POST':
        member_id = request.form.get('member_id', '').strip()
        
        if not member_id:
            error = "Member ID is required"
        elif member_id not in MEMBERS_DB:
            error = f"Member not found: {member_id}"
        else:
            member = MEMBERS_DB[member_id]
            success = f"Member found: {member['name']}"
    
    content = f"""
<h2>Member Lookup</h2>
"""
    if error:
        content += f'<p class="error">{error}</p>'
    if success:
        content += f'<p class="success">{success}</p>'
    
    content += """
<table>
    <tr>
        <td>Enter Member ID:</td>
        <td>
            <form method="POST" action="/lookup">
                <input type="text" name="member_id" id="member_LOOKUPID" value="MEMBERID">
                <input type="submit" value="Lookup Member" id="btn_LOOKUPID">
            </form>
        </td>
    </tr>
</table>
"""
    
    if member:
        content += f"""
<h3>Member Found</h3>
<table>
    <tr>
        <th>Field</th>
        <th>Value</th>
    </tr>
    <tr>
        <td>Member ID</td>
        <td>{member_id}</td>
    </tr>
    <tr>
        <td>Name</td>
        <td>{member['name']}</td>
    </tr>
    <tr>
        <td>Savings Balance</td>
        <td id="savings_balance_LOOKUPID">${member['savings_balance']}</td>
    </tr>
    <tr>
        <td>Checking Balance</td>
        <td id="checking_balance_LOOKUPID">${member['checking_balance']}</td>
    </tr>
    <tr>
        <td>Account Status</td>
        <td>{member['account_status']}</td>
    </tr>
    <tr>
        <td>Member Since</td>
        <td>{member['member_since']}</td>
    </tr>
</table>
<p>
    <a href="/update_balance/{member_id}">Update Balance</a> |
    <a href="/lookup">Another Lookup</a>
</p>
"""
    
    content = content.replace('MEMBERID', random_id)
    content = content.replace('LOOKUPID', random_id)
    
    return render_template_string(HOME_TEMPLATE, content=content)


@app.route('/update_balance/<member_id>', methods=['GET', 'POST'])
def update_balance(member_id):
    """Update balance page."""
    error = None
    random_id = str(random.randint(10000, 99999))
    
    if member_id not in MEMBERS_DB:
        return redirect(url_for('lookup'))
    
    member = MEMBERS_DB[member_id]
    
    if request.method == 'POST':
        # Redirect to confirmation page
        account_type = request.form.get('account_type')
        new_balance = request.form.get('new_balance', '').strip()
        
        if not new_balance:
            error = "Balance amount is required"
        else:
            try:
                # Validate it's a number
                float(new_balance)
                session['pending_update'] = {
                    'account_type': account_type,
                    'new_balance': new_balance
                }
                return redirect(url_for('confirm_update', member_id=member_id))
            except ValueError:
                error = "Balance must be a valid number"
    
    content = f"""
<h2>Update Account Balance</h2>
<p>Member: {member['name']} (ID: {member_id})</p>
<table>
    <tr>
        <td>Current Savings Balance:</td>
        <td>${member['savings_balance']}</td>
    </tr>
    <tr>
        <td>Current Checking Balance:</td>
        <td>${member['checking_balance']}</td>
    </tr>
</table>
"""
    if error:
        content += f'<p class="error">{error}</p>'
    
    content += f"""
<h3>Enter New Balance</h3>
<form method="POST" action="/update_balance/{member_id}">
    <table>
        <tr>
            <td>Account Type:</td>
            <td>
                <select name="account_type" id="account_select_UPDATEID">
                    <option value="savings">Savings</option>
                    <option value="checking">Checking</option>
                </select>
            </td>
        </tr>
        <tr>
            <td>New Balance Amount:</td>
            <td>
                <input type="text" name="new_balance" id="balance_input_UPDATEID" value="">
            </td>
        </tr>
        <tr>
            <td colspan="2">
                <input type="submit" value="Update Balance" id="update_btn_UPDATEID">
                <a href="/lookup">Cancel</a>
            </td>
        </tr>
    </table>
</form>
"""
    
    content = content.replace('UPDATEID', random_id)
    
    return render_template_string(HOME_TEMPLATE, content=content)


@app.route('/confirm_update/<member_id>', methods=['GET', 'POST'])
def confirm_update(member_id):
    """Confirmation page for balance update."""
    random_id = str(random.randint(10000, 99999))
    
    if member_id not in MEMBERS_DB:
        return redirect(url_for('lookup'))
    
    member = MEMBERS_DB[member_id]
    
    if request.method == 'POST':
        account_type = request.form.get('account_type')
        new_balance = float(request.form.get('new_balance'))
        
        # Update the balance
        if account_type == 'savings':
            member['savings_balance'] = new_balance
        elif account_type == 'checking':
            member['checking_balance'] = new_balance
        
        return redirect(url_for('update_success', member_id=member_id, account_type=account_type, new_balance=new_balance))
    
    # Get pending update from session
    pending = session.get('pending_update', {})
    account_type = pending.get('account_type', 'savings')
    new_balance = pending.get('new_balance', '0')
    
    current_balance = member['savings_balance'] if account_type == 'savings' else member['checking_balance']
    
    content = f"""
<h2>Confirm Balance Update</h2>
<p>Please review and confirm the following change:</p>
<table>
    <tr>
        <th>Field</th>
        <th>Current Value</th>
        <th>New Value</th>
    </tr>
    <tr>
        <td>Member ID</td>
        <td>{member_id}</td>
        <td>{member_id}</td>
    </tr>
    <tr>
        <td>Account Type</td>
        <td>{account_type.capitalize()}</td>
        <td>{account_type.capitalize()}</td>
    </tr>
    <tr>
        <td>Balance</td>
        <td>${current_balance}</td>
        <td>${new_balance}</td>
    </tr>
</table>
<form method="POST" action="/confirm_update/{member_id}">
    <input type="hidden" name="account_type" value="{account_type}">
    <input type="hidden" name="new_balance" value="{new_balance}">
    <input type="submit" value="Confirm Update" id="confirm_btn_CONFIRMID">
    <a href="/update_balance/{member_id}">Cancel</a>
</form>
"""
    
    content = content.replace('CONFIRMID', random_id)
    
    return render_template_string(HOME_TEMPLATE, content=content)


@app.route('/update_success/<member_id>')
def update_success(member_id):
    """Success page after balance update."""
    account_type = request.args.get('account_type', 'savings')
    new_balance = request.args.get('new_balance', '0')
    
    content = f"""
<h2>Balance Update Successful</h2>
<p class="success">The account balance has been updated successfully.</p>
<table>
    <tr>
        <td>Member ID:</td>
        <td>{member_id}</td>
    </tr>
    <tr>
        <td>Account Type:</td>
        <td>{account_type.capitalize()}</td>
    </tr>
    <tr>
        <td>New Balance:</td>
        <td>${new_balance}</td>
    </tr>
    <tr>
        <td>Timestamp:</td>
        <td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
    </tr>
</table>
<p><a href="/lookup">Return to Member Lookup</a></p>
"""
    
    return render_template_string(HOME_TEMPLATE, content=content)


@app.route('/accounts')
def accounts():
    """Account management page (placeholder)."""
    return render_template_string(HOME_TEMPLATE, content="<h2>Account Management</h2><p>Feature under development.</p><p>This page is a placeholder for demonstration purposes.</p>")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# Meeting Assistant UI - Design Branch

This is a separate `ui-design` branch that adds a mobile-friendly **Meeting Assistant** web UI to the project. It does not modify or break the original Interface.ai computer-use automation system.

## What This Branch Contains

A clean, mobile-first web interface with:
- **Bottom navigation**: Home, Activity, Meeting, Profile, Settings
- **Recording controls**: Start/pause recording with animated status
- **Tabs**: General / Technical
- **Think button**: Generates a sample AI summary
- **Upload button**: Simulates file upload for meeting files
- **AI Summary**: Collapsible summary section
- **Transcript**: Live transcript with auto-updates

## How to Run

```bash
# Make sure you are on the ui-design branch
git checkout ui-design

# Start the UI server
python -m src.ui_app.app
```

Open `http://localhost:8080` in your browser.

## Files Added

```
src/ui_app/
├── app.py              # Flask server for the UI
├── __init__.py
├── static/
│   ├── css/style.css   # Mobile-first responsive styles
│   └── js/app.js       # Interactive UI logic
└── templates/index.html # Main UI template
```

## Screenshots

The UI is designed to look like a native mobile meeting assistant app, with a clean white/purple color scheme, rounded cards, and smooth interactions.

## Notes

- This is a design/prototype branch.
- It does not integrate with the automation system.
- The original `master` branch remains focused on the Interface.ai take-home assignment.

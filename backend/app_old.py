# mcp_project_portal/backend/app.py
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes and all origins

# --- Data Loading (MCP manages its programs/projects) ---
PROJECT_DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'projects.json')

def load_projects():
    """Loads project data from the JSON file."""
    try:
        with open(PROJECT_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {PROJECT_DATA_FILE} not found. Serving empty project list.")
        return []
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {PROJECT_DATA_FILE}. Serving empty project list.")
        return []

PROJECTS_DB = load_projects()

# --- API Endpoints (Interfaces for the User Grid to access Program info) ---

@app.route('/categories', methods=['GET'])
def get_categories():
    """Returns a list of unique project categories."""
    if not PROJECTS_DB:
        return jsonify({"categories": []})
    categories = sorted(list(set(project.get("category", "Uncategorized") for project in PROJECTS_DB)))
    return jsonify({"categories": categories})

@app.route('/projects', methods=['GET'])
def get_projects():
    """Returns a list of projects, filterable by category, difficulty, and keyword."""
    category_filter = request.args.get('category')
    difficulty_filter = request.args.get('difficulty')
    keyword_filter = request.args.get('keyword', '').lower().strip()

    filtered_projects = PROJECTS_DB

    if category_filter:
        filtered_projects = [
            p for p in filtered_projects if p.get("category", "").lower() == category_filter.lower()
        ]

    if difficulty_filter:
        filtered_projects = [
            p for p in filtered_projects if p.get("difficulty", "").lower() == difficulty_filter.lower()
        ]

    if keyword_filter:
        temp_projects = []
        for p in filtered_projects:
            # Check name, description, category, difficulty, suggested_tech, and keywords
            match = (
                keyword_filter in p.get("name", "").lower() or
                keyword_filter in p.get("description", "").lower() or
                keyword_filter in p.get("category", "").lower() or
                keyword_filter in p.get("difficulty", "").lower() or
                any(keyword_filter in tech.lower() for tech in p.get("suggested_tech", [])) or
                any(keyword_filter in kw.lower() for kw in p.get("keywords", []))
            )
            if match:
                temp_projects.append(p)
        filtered_projects = temp_projects
    
    # Your frontend expects {"data": [...]}
    # If filters are applied and no results, it's a valid empty result for the query,
    # not a 404 on the endpoint itself.
    return jsonify({"data": filtered_projects})


@app.route('/projects/<project_id>', methods=['GET'])
def get_project_details(project_id):
    """Returns details for a specific project by its ID."""
    project = next((p for p in PROJECTS_DB if p.get("id") == project_id), None)
    if project:
        return jsonify(project)
    else:
        return jsonify({"error": "Project not found", "message": f"No project with ID {project_id} exists."}), 404

if __name__ == '__main__':
    print("MCP Backend Initializing...")
    print(f"Loaded {len(PROJECTS_DB)} projects from data store.")
    if not PROJECTS_DB:
        print("WARNING: No project data loaded. Check 'backend/data/projects.json'.")
    print("MCP Server ready and listening on port 5000.")
    app.run(debug=True, port=5000)
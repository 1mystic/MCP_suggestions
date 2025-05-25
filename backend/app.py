# mcp_project_portal/backend/app.py
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re # For keyword matching in MCP suggestion

app = Flask(__name__)
CORS(app)

# --- Data Loading ---
DEV_TASKS_DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'dev_tasks.json')

def load_data(file_path, data_name="items"):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {file_path} not found. Serving empty list for {data_name}.")
        return []
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {file_path}. Serving empty list for {data_name}.")
        return []

DEV_TASKS_DB = load_data(DEV_TASKS_DATA_FILE, "development tasks")

# --- MCP Knowledge Base (Simplified) ---
# This represents our backend's understanding of what different MCPs can do.
# In a real system, this could be much more sophisticated.
MCP_CAPABILITIES = {
    "Sequential Thinking MCP": {
        "keywords": ["plan", "architect", "design", "decompose", "refactor complex", "multi-step", "structure"],
        "description": "Breaks complex tasks into smaller, logical steps. Useful for planning, system design, and large refactors.",
        "use_case_trigger": "Task involves high-level planning or complex, multi-stage changes."
    },
    "Puppeteer MCP / Playwright MCP": {
        "keywords": ["ui test", "browser automation", "scrape", "form submission", "frontend validation", "e2e test", "user interaction"],
        "description": "Equips AI with browser automation powers (Puppeteer for Chrome, Playwright for cross-browser).",
        "use_case_trigger": "Task involves interacting with web UIs, testing frontend, or scraping web data."
    },
    "Memory Bank MCP / Knowledge Graph Memory MCP": {
        "keywords": ["context", "remember", "codebase navigation", "relationships", "multi-file", "project understanding"],
        "description": "Provides centralized or graph-based memory for AI agents to recall information and understand code relationships.",
        "use_case_trigger": "Task requires understanding of a large codebase or remembering context across multiple steps/files."
    },
    "GitHub MCP": {
        "keywords": ["github", "issue", "pr", "pull request", "repository", "commit", "ci", "version control"],
        "description": "Connects AI to GitHub's API for managing issues, PRs, code, and CI workflows.",
        "use_case_trigger": "Task involves interacting with a GitHub repository (e.g., creating issues, managing PRs)."
    },
    "DuckDuckGo MCP": {
        "keywords": ["search", "find documentation", "resolve error", "research", "explore concept"],
        "description": "Enables AI to fetch real-time information via web search.",
        "use_case_trigger": "Task requires looking up external information, error messages, or documentation."
    },
    "Desktop Commander MCP": {
        "keywords": ["terminal", "shell command", "local file", "execute script", "run command", "browse files", "inspect logs"],
        "description": "Provides AI with safe, local terminal access for file operations and command execution.",
        "use_case_trigger": "Task involves running local scripts, managing files, or executing terminal commands."
    },
    "Serena MCP / Refactoring Engine": {
        "keywords": ["refactor", "code change", "extract function", "migrate module", "performance tune code"],
        "description": "A smart, context-aware refactoring engine for multi-step code changes.",
        "use_case_trigger": "Task is focused on refactoring code, improving structure, or applying specific code transformations."
    },
    "Supabase MCP / Database MCP": {
        "keywords": ["database", "sql", "query", "schema", "manage records", "supabase", "postgresql", "mongodb"],
        "description": "Allows AI agents to directly query and manipulate databases.",
        "use_case_trigger": "Task involves direct database interaction, schema changes, or data manipulation."
    },
    "Digma MCP Server / APM MCP": {
        "keywords": ["observability", "performance issue", "runtime data", "telemetry", "apm", "bottleneck", "test flakiness"],
        "description": "Taps into runtime observability data (APM) to inform AI decisions.",
        "use_case_trigger": "Task involves diagnosing performance issues, understanding runtime behavior, or leveraging APM data."
    }
    # We can add more from the list or create our own conceptual ones.
}


# --- API Endpoints ---

@app.route('/task_categories', methods=['GET'])
def get_task_categories():
    if not DEV_TASKS_DB:
        return jsonify({"categories": []})
    categories = sorted(list(set(task.get("category", "Uncategorized") for task in DEV_TASKS_DB)))
    return jsonify({"categories": categories})

@app.route('/dev_tasks', methods=['GET'])
def get_dev_tasks():
    category_filter = request.args.get('category')
    difficulty_filter = request.args.get('difficulty')
    keyword_filter = request.args.get('keyword', '').lower().strip()

    filtered_tasks = DEV_TASKS_DB

    if category_filter:
        filtered_tasks = [
            t for t in filtered_tasks if t.get("category", "").lower() == category_filter.lower()
        ]
    if difficulty_filter:
        filtered_tasks = [
            t for t in filtered_tasks if t.get("difficulty", "").lower() == difficulty_filter.lower()
        ]
    if keyword_filter:
        temp_tasks = []
        for t in filtered_tasks:
            match = (
                keyword_filter in t.get("name", "").lower() or
                keyword_filter in t.get("description", "").lower() or
                keyword_filter in t.get("category", "").lower() or
                keyword_filter in t.get("difficulty", "").lower() or
                any(keyword_filter in kw.lower() for kw in t.get("keywords", []))
            )
            if match:
                temp_tasks.append(t)
        filtered_tasks = temp_tasks
    
    return jsonify({"data": filtered_tasks})


@app.route('/dev_tasks/<task_id>', methods=['GET'])
def get_dev_task_details(task_id):
    task = next((t for t in DEV_TASKS_DB if t.get("id") == task_id), None)
    if task:
        # Optionally, we could also pre-suggest MCPs here
        # task_description_for_mcp = f"{task.get('name', '')} {task.get('description', '')} {' '.join(task.get('keywords', []))}"
        # suggested_mcps = suggest_mcp_for_text(task_description_for_mcp)
        # task_with_suggestions = {**task, "suggested_mcps": suggested_mcps}
        # return jsonify(task_with_suggestions)
        return jsonify(task) # Keeping it simple for now
    else:
        return jsonify({"error": "Development task not found", "message": f"No task with ID {task_id} exists."}), 404


def suggest_mcp_for_text(text_content):
    """Suggests MCPs based on keywords in the text content."""
    suggestions = []
    text_lower = text_content.lower()
    for mcp_name, data in MCP_CAPABILITIES.items():
        for keyword in data["keywords"]:
            # Using regex for whole word matching might be better for some keywords
            # For simplicity, using 'in' for now
            if f" {keyword} " in f" {text_lower} " or text_lower.startswith(keyword) or text_lower.endswith(keyword): # simple check
                if not any(s['name'] == mcp_name for s in suggestions): # Avoid duplicates
                    suggestions.append({
                        "name": mcp_name,
                        "relevance_trigger": data.get("use_case_trigger", "General utility for this task."),
                        "description": data["description"]
                    })
                break # Found a keyword for this MCP, move to next MCP
    
    # Fallback/General MCPs if few specific matches
    if not suggestions or len(suggestions) < 2 :
        if not any(s['name'] == "DuckDuckGo MCP" for s in suggestions):
             suggestions.append({
                "name": "DuckDuckGo MCP",
                "relevance_trigger": "Useful for general research, finding documentation, or resolving errors related to the task.",
                "description": MCP_CAPABILITIES["DuckDuckGo MCP"]["description"]
            })
        if not any(s['name'] == "Memory Bank MCP / Knowledge Graph Memory MCP" for s in suggestions) and len(DEV_TASKS_DB) > 0: # If we have tasks, memory is likely useful
             suggestions.append({
                "name": "Memory Bank MCP / Knowledge Graph Memory MCP",
                "relevance_trigger": "Helps maintain context if the task spans multiple files or requires historical knowledge.",
                "description": MCP_CAPABILITIES["Memory Bank MCP / Knowledge Graph Memory MCP"]["description"]
            })
    
    return suggestions[:5] # Return top 5 suggestions

@app.route('/suggest_mcp_actions', methods=['POST'])
def suggest_mcp_actions_endpoint():
    data = request.get_json()
    if not data or 'task_description' not in data:
        return jsonify({"error": "Missing 'task_description' in request body"}), 400
    
    task_description = data['task_description']
    
    # For a specific task ID, we could be more targeted
    task_id = data.get('task_id')
    if task_id:
        task = next((t for t in DEV_TASKS_DB if t.get("id") == task_id), None)
        if task:
            # Combine general description with task-specific details for better suggestions
            task_full_text = f"{task.get('name','')} {task.get('description','')} {' '.join(task.get('keywords',[]))} {task_description}"
            suggested_mcps = suggest_mcp_for_text(task_full_text)
            return jsonify({"suggested_mcps": suggested_mcps})
        else:
            # Fallback to general description if task_id not found
            suggested_mcps = suggest_mcp_for_text(task_description)
            return jsonify({"suggested_mcps": suggested_mcps})
    else:
        # If no task_id, just use the provided description
        suggested_mcps = suggest_mcp_for_text(task_description)
        return jsonify({"suggested_mcps": suggested_mcps})


if __name__ == '__main__':
    print("MCP-Aware Dev Task Orchestrator Initializing...")
    print(f"Loaded {len(DEV_TASKS_DB)} development tasks from data store.")
    if not DEV_TASKS_DB:
        print("WARNING: No development task data loaded. Check 'backend/data/dev_tasks.json'.")
    print("Server ready and listening on port 5000.")
    app.run(debug=True, port=5000)
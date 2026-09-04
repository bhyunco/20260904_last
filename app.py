import os
from flask import Flask, render_template, request, jsonify
from models import (
    init_db, get_all_todos, get_todo_by_id, create_todo,
    update_todo, toggle_todo, delete_todo, delete_completed_todos, get_todo_stats
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vibe-rpa-flask-todo-secret-key-2026'

# Initialize database on app startup
with app.app_context():
    init_db()

@app.route('/')
def index():
    """Render the main Todo application interface."""
    stats = get_todo_stats()
    categories = ["업무", "개인", "공부", "쇼핑", "아이디어", "기타"]
    priorities = ["높음", "보통", "낮음"]
    return render_template(
        'index.html',
        initial_stats=stats,
        categories=categories,
        priorities=priorities
    )

# ================= REST API Endpoints =================

@app.route('/api/todos', methods=['GET'])
def api_get_todos():
    """Retrieve filtered and sorted list of todos."""
    status = request.args.get('status', 'all')
    category = request.args.get('category', 'all')
    priority = request.args.get('priority', 'all')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'newest')
    
    todos = get_all_todos(
        status=status,
        category=category,
        priority=priority,
        search=search,
        sort_by=sort_by
    )
    return jsonify({"success": True, "todos": todos, "count": len(todos)})

@app.route('/api/todos', methods=['POST'])
def api_create_todo():
    """Create a new todo item."""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"success": False, "error": "할 일 제목을 입력해주세요."}), 400
        
    description = data.get('description', '').strip()
    category = data.get('category', '업무')
    priority = data.get('priority', '보통')
    due_date = data.get('due_date', '')
    
    try:
        new_todo = create_todo(
            title=title,
            description=description,
            category=category,
            priority=priority,
            due_date=due_date
        )
        stats = get_todo_stats()
        return jsonify({
            "success": True,
            "message": "할 일이 추가되었습니다.",
            "todo": new_todo,
            "stats": stats
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
def api_get_todo(todo_id):
    """Get detail of a specific todo item."""
    todo = get_todo_by_id(todo_id)
    if not todo:
        return jsonify({"success": False, "error": "해당 할 일을 찾을 수 없습니다."}), 404
    return jsonify({"success": True, "todo": todo})

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def api_update_todo(todo_id):
    """Update an existing todo item."""
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description')
    category = data.get('category')
    priority = data.get('priority')
    due_date = data.get('due_date')
    completed = data.get('completed')
    
    try:
        updated = update_todo(
            todo_id=todo_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            due_date=due_date,
            completed=completed
        )
        if not updated:
            return jsonify({"success": False, "error": "해당 할 일을 찾을 수 없습니다."}), 404
            
        stats = get_todo_stats()
        return jsonify({
            "success": True,
            "message": "할 일이 수정되었습니다.",
            "todo": updated,
            "stats": stats
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/todos/<int:todo_id>/toggle', methods=['PATCH'])
def api_toggle_todo(todo_id):
    """Toggle completed status of a todo item."""
    updated = toggle_todo(todo_id)
    if not updated:
        return jsonify({"success": False, "error": "해당 할 일을 찾을 수 없습니다."}), 404
        
    stats = get_todo_stats()
    return jsonify({
        "success": True,
        "message": "상태가 변경되었습니다.",
        "todo": updated,
        "stats": stats
    })

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def api_delete_todo(todo_id):
    """Delete a specific todo item."""
    deleted = delete_todo(todo_id)
    if not deleted:
        return jsonify({"success": False, "error": "해당 할 일을 찾을 수 없습니다."}), 404
        
    stats = get_todo_stats()
    return jsonify({
        "success": True,
        "message": "할 일이 삭제되었습니다.",
        "stats": stats
    })

@app.route('/api/todos/completed', methods=['DELETE'])
def api_delete_completed():
    """Delete all completed todos."""
    deleted_count = delete_completed_todos()
    stats = get_todo_stats()
    return jsonify({
        "success": True,
        "message": f"완료된 할 일 {deleted_count}개가 삭제되었습니다.",
        "deleted_count": deleted_count,
        "stats": stats
    })

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Get current statistics."""
    stats = get_todo_stats()
    return jsonify({"success": True, "stats": stats})

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "요청한 리소스를 찾을 수 없습니다."}), 404
    return render_template('index.html', initial_stats=get_todo_stats(), categories=[], priorities=[]), 404

if __name__ == '__main__':
    print("[INFO] Starting Flask To-Do App on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)

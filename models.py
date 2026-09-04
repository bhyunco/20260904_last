import sqlite3
import os
import tempfile
from datetime import datetime

# Vercel serverless environment has a read-only filesystem except /tmp
if os.environ.get('VERCEL'):
    DB_PATH = os.path.join(tempfile.gettempdir(), 'todo.db')
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'todo.db')

def get_db_connection():
    """Create a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed_sample_data=True):
    """Initialize database tables and optionally seed with initial demo tasks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '업무',
            priority TEXT DEFAULT '보통',
            due_date TEXT DEFAULT '',
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    
    # Check if empty, then seed sample tasks if requested
    cursor.execute('SELECT COUNT(*) as count FROM todos')
    count = cursor.fetchone()['count']
    if count == 0 and seed_sample_data:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sample_tasks = [
            ("파이썬 업무자동화 강의 복습하기", "실습 파일 확인 및 Jupyter Notebook 코드 정리", "공부", "높음", datetime.now().strftime('%Y-%m-%d'), 0),
            ("Flask 할 일 관리 웹앱 완성하기", "REST API 및 스타일리시한 다크모드 UI 구현", "업무", "높음", datetime.now().strftime('%Y-%m-%d'), 1),
            ("장보기 목록 작성 및 마트 가기", "원두커피, 우유, 신선한 과일 구매", "쇼핑", "보통", datetime.now().strftime('%Y-%m-%d'), 0),
            ("주말 운동 루틴 계획하기", "유산소 30분 + 스트레칭 20분", "개인", "낮음", "", 0),
        ]
        cursor.executemany('''
            INSERT INTO todos (title, description, category, priority, due_date, completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [(t[0], t[1], t[2], t[3], t[4], t[5], now_str, now_str) for t in sample_tasks])
        conn.commit()
        
    conn.close()

def todo_to_dict(row):
    """Convert a sqlite3.Row object to a dictionary."""
    if row is None:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "category": row["category"] or "업무",
        "priority": row["priority"] or "보통",
        "due_date": row["due_date"] or "",
        "completed": bool(row["completed"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }

def get_all_todos(status='all', category=None, priority=None, search=None, sort_by='newest'):
    """Fetch todos filtered and sorted."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM todos WHERE 1=1"
    params = []
    
    if status == 'active':
        query += " AND completed = 0"
    elif status == 'completed':
        query += " AND completed = 1"
        
    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)
        
    if priority and priority != 'all':
        query += " AND priority = ?"
        params.append(priority)
        
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")
        
    # Sorting
    if sort_by == 'due_date':
        # NULL or empty due_date sorted last
        query += " ORDER BY CASE WHEN due_date = '' OR due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id DESC"
    elif sort_by == 'priority':
        query += """ ORDER BY 
            CASE priority 
                WHEN '높음' THEN 1 
                WHEN '보통' THEN 2 
                WHEN '낮음' THEN 3 
                ELSE 4 
            END ASC, id DESC"""
    elif sort_by == 'oldest':
        query += " ORDER BY id ASC"
    else:  # newest
        query += " ORDER BY id DESC"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    todos = [todo_to_dict(row) for row in rows]
    conn.close()
    return todos

def get_todo_by_id(todo_id):
    """Get a single todo item by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    conn.close()
    return todo_to_dict(row)

def create_todo(title, description="", category="업무", priority="보통", due_date=""):
    """Create a new todo item."""
    if not title or not title.strip():
        raise ValueError("할 일 제목은 필수 입력 항목입니다.")
        
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO todos (title, description, category, priority, due_date, completed, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
    ''', (title.strip(), description.strip() if description else "", category or "업무", priority or "보통", due_date or "", now_str, now_str))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_todo_by_id(new_id)

def update_todo(todo_id, title=None, description=None, category=None, priority=None, due_date=None, completed=None):
    """Update an existing todo item."""
    todo = get_todo_by_id(todo_id)
    if not todo:
        return None
        
    new_title = title.strip() if title is not None else todo["title"]
    if not new_title:
        raise ValueError("할 일 제목은 비어 있을 수 없습니다.")
        
    new_desc = description.strip() if description is not None else todo["description"]
    new_cat = category if category is not None else todo["category"]
    new_priority = priority if priority is not None else todo["priority"]
    new_due = due_date if due_date is not None else todo["due_date"]
    new_completed = int(completed) if completed is not None else int(todo["completed"])
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE todos
        SET title = ?, description = ?, category = ?, priority = ?, due_date = ?, completed = ?, updated_at = ?
        WHERE id = ?
    ''', (new_title, new_desc, new_cat, new_priority, new_due, new_completed, now_str, todo_id))
    conn.commit()
    conn.close()
    return get_todo_by_id(todo_id)

def toggle_todo(todo_id):
    """Toggle completed status of a todo."""
    todo = get_todo_by_id(todo_id)
    if not todo:
        return None
    new_status = not todo["completed"]
    return update_todo(todo_id, completed=new_status)

def delete_todo(todo_id):
    """Delete a todo by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def delete_completed_todos():
    """Delete all completed todos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE completed = 1")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def get_todo_stats():
    """Get summary statistics for dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM todos")
    total = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as completed FROM todos WHERE completed = 1")
    completed = cursor.fetchone()['completed']
    
    pending = total - completed
    rate = round((completed / total * 100), 1) if total > 0 else 0
    
    # Check overdue tasks (due_date < today and completed = 0)
    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) as overdue FROM todos 
        WHERE completed = 0 AND due_date != '' AND due_date < ?
    ''', (today_str,))
    overdue = cursor.fetchone()['overdue']
    
    conn.close()
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": rate,
        "overdue": overdue
    }

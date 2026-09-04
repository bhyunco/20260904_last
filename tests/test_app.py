import os
import sys
import unittest
import tempfile
import json

# Add parent directory to sys.path to import app and models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import models
from app import app

class TodoAppTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.db_fd, self.db_path = tempfile.mkstemp()
        models.DB_PATH = self.db_path
        
        # Initialize the test database without sample data
        models.init_db(seed_sample_data=False)
        
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_index_page(self):
        """Test home page loads with 200 OK and valid HTML."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TaskFlow', response.data)
        self.assertIn(b'id="todo-form"', response.data)

    def test_create_todo_success(self):
        """Test creating a new todo item with full fields."""
        payload = {
            "title": "파이썬 단위 테스트 작성",
            "description": "Flask REST API 및 DB 검증",
            "category": "공부",
            "priority": "높음",
            "due_date": "2026-12-31"
        }
        res = self.client.post('/api/todos', 
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['todo']['title'], "파이썬 단위 테스트 작성")
        self.assertEqual(data['todo']['priority'], "높음")
        self.assertFalse(data['todo']['completed'])
        self.assertEqual(data['stats']['total'], 1)

    def test_create_todo_validation_empty_title(self):
        """Test creating a todo without title should fail with 400 Bad Request."""
        res = self.client.post('/api/todos',
                               data=json.dumps({"title": "   "}),
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])

    def test_toggle_todo(self):
        """Test toggling completed status."""
        todo = models.create_todo("보고서 작성", category="업무")
        todo_id = todo['id']
        self.assertFalse(todo['completed'])

        # Toggle to True
        res = self.client.patch(f'/api/todos/{todo_id}/toggle')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['todo']['completed'])
        self.assertEqual(data['stats']['completed'], 1)

        # Toggle back to False
        res2 = self.client.patch(f'/api/todos/{todo_id}/toggle')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertFalse(data2['todo']['completed'])
        self.assertEqual(data2['stats']['completed'], 0)

    def test_update_todo(self):
        """Test updating fields of an existing todo item."""
        todo = models.create_todo("책 읽기", priority="낮음")
        todo_id = todo['id']

        update_payload = {
            "title": "클린 코드 완독하기",
            "description": "1장부터 5장까지 정리",
            "category": "공부",
            "priority": "높음",
            "due_date": "2026-10-15"
        }
        res = self.client.put(f'/api/todos/{todo_id}',
                              data=json.dumps(update_payload),
                              content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['todo']['title'], "클린 코드 완독하기")
        self.assertEqual(data['todo']['priority'], "높음")
        self.assertEqual(data['todo']['category'], "공부")

    def test_delete_todo(self):
        """Test deleting an existing todo."""
        todo = models.create_todo("삭제할 임시 할 일")
        todo_id = todo['id']

        res = self.client.delete(f'/api/todos/{todo_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

        # Verify it's gone
        get_res = self.client.get(f'/api/todos/{todo_id}')
        self.assertEqual(get_res.status_code, 404)

    def test_delete_completed_todos(self):
        """Test batch deleting completed todos."""
        t1 = models.create_todo("할 일 1")
        t2 = models.create_todo("할 일 2")
        t3 = models.create_todo("할 일 3")

        models.toggle_todo(t1['id'])
        models.toggle_todo(t2['id'])

        res = self.client.delete('/api/todos/completed')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['deleted_count'], 2)

        remaining = models.get_all_todos()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['id'], t3['id'])

    def test_filtering_and_search(self):
        """Test filtering by status, category, and search query."""
        models.create_todo("파이썬 자동화 스크립트", category="업무", priority="높음")
        models.create_todo("우유 및 사과 구매", category="쇼핑", priority="보통")
        t3 = models.create_todo("운동하기", category="개인", priority="낮음")
        models.toggle_todo(t3['id'])

        # Search query '스크립트'
        res = self.client.get('/api/todos?search=스크립트')
        data = res.get_json()
        self.assertEqual(len(data['todos']), 1)
        self.assertEqual(data['todos'][0]['title'], "파이썬 자동화 스크립트")

        # Category filter '쇼핑'
        res_cat = self.client.get('/api/todos?category=쇼핑')
        data_cat = res_cat.get_json()
        self.assertEqual(len(data_cat['todos']), 1)
        self.assertEqual(data_cat['todos'][0]['title'], "우유 및 사과 구매")

        # Status filter 'completed'
        res_comp = self.client.get('/api/todos?status=completed')
        data_comp = res_comp.get_json()
        self.assertEqual(len(data_comp['todos']), 1)
        self.assertEqual(data_comp['todos'][0]['title'], "운동하기")

    def test_stats_calculation(self):
        """Test accuracy of stats calculations."""
        t1 = models.create_todo("Task 1")
        t2 = models.create_todo("Task 2")
        models.toggle_todo(t1['id'])

        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()['stats']
        self.assertEqual(stats['total'], 2)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['completion_rate'], 50.0)

if __name__ == '__main__':
    unittest.main()

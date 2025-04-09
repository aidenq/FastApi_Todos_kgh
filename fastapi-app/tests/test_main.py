import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from main import app, write_todos as save_todos, read_todos as load_todos, TodoItem

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # 테스트 전 초기화
    save_todos([])
    yield
    # 테스트 후 정리
    save_todos([])

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_get_todos_with_items():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False, date="2025-04-06")
    save_todos([todo.dict()])
    response = client.get("/todos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test"

def test_create_todo():
    todo = {
        "id": 1,
        "title": "Test",
        "description": "Test description",
        "completed": False,
        "date": "2025-04-06"
    }
    response = client.post("/todos", json=todo)
    assert response.status_code == 200
    assert response.json()["title"] == "Test"

def test_create_todo_invalid():
    # date 필드 누락 → 422 예상
    todo = {
        "id": 1,
        "title": "Test",
        "description": "Test description",
        "completed": False
    }
    response = client.post("/todos", json=todo)
    assert response.status_code == 422

def test_update_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False, date="2025-04-06")
    save_todos([todo.dict()])
    updated_todo = {"id": 1, "title": "Updated", "description": "Updated description", "completed": True, "date": "2025-04-06"}
    response = client.patch("/todos/1/edit", json=updated_todo)
    assert response.status_code == 200
    assert response.json()["message"] == "Todo updated"

def test_update_todo_status():
    todo = {
        "id": 1,
        "title": "Test",
        "description": "Test description",
        "completed": False,
        "date": "2025-04-06"
    }
    save_todos([todo])
    response = client.patch("/todos/1/complete", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["message"] == "Status updated"

def test_update_todo_not_found():
    updated_todo = {"id": 1, "title": "Updated", "description": "Updated description", "completed": True, "date": "2025-04-06"}
    response = client.patch("/todos/1/edit", json=updated_todo)
    assert response.status_code == 404

def test_edit_todo():
    todo = {
        "id": 1,
        "title": "Old Title",
        "description": "Old description",
        "completed": False,
        "date": "2025-04-06"
    }
    save_todos([todo])
    response = client.patch("/todos/1/edit", json={
        "title": "New Title",
        "description": "New Description",
        "date": "2025-04-07"
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Todo updated"

def test_delete_todo():
    todo = TodoItem(id=1, title="Test", description="Test description", completed=False, date="2025-04-06")
    save_todos([todo.dict()])
    response = client.delete("/todos/1")
    assert response.status_code == 200
    assert response.json()["message"] == "Todo deleted"
    
def test_delete_todo_not_found():
    response = client.delete("/todos/999")
    assert response.status_code == 404

import os
import sys
import importlib.util
from fastapi.testclient import TestClient

# Dynamically load the FastAPI app from main.py
project_root = os.path.dirname(os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location(
    "main_module", os.path.join(project_root, "main.py")
)
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)
app = getattr(main_module, "app")

client = TestClient(app)


def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_and_get_todo():
    new_todo = {
        "id": 101,
        "title": "Integration Test Todo",
        "description": "Testing POST endpoint",
        "completed": False,
        "date": "2025-04-10"
    }
    # Create new todo
    response = client.post("/todos", json=new_todo)
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == new_todo["title"]

    # Verify in list
    response = client.get("/todos")
    todos = response.json()
    assert any(todo.get("id") == new_todo["id"] for todo in todos)

    # Update the todo
    updated_data = {
        "title": "Updated Integration Test Todo",
        "description": "Testing PUT endpoint",
        "completed": True
    }
    response = client.patch(f"/todos/{new_todo['id']}/edit", json=updated_data)
    assert response.status_code == 200
    assert response.json().get("message") == "Todo updated"


def test_complete_todo():
    response = client.patch("/todos/101/complete", json={"completed": True})
    assert response.status_code == 200
    assert response.json().get("message") == "Status updated"


def test_delete_todo():
    response = client.delete("/todos/101")
    assert response.status_code == 200
    assert response.json().get("message") == "Todo deleted"


def test_delete_todo_not_found():
    response = client.delete("/todos/99999")
    assert response.status_code == 404

import requests

BASE_URL = "http://3.34.1.40:8002"

def test_get_todos_empty():
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_and_get_todo():
    # 새 todo 생성
    new_todo = {
        "id": 101,
        "title": "Integration Test Todo",
        "description": "Testing POST endpoint",
        "completed": False,
        "date": "2025-04-10"
    }
    response = requests.post(f"{BASE_URL}/todos", json=new_todo)
    assert response.status_code == 200
    assert response.json()["title"] == new_todo["title"]

    # 생성된 todo 조회
    response = requests.get(f"{BASE_URL}/todos")
    assert response.status_code == 200
    todos = response.json()
    assert any(todo["id"] == new_todo["id"] for todo in todos)

def test_update_todo():
    updated_data = {
        "id": 101,
        "title": "Updated Title",
        "description": "Updated desc",
        "completed": True,
        "date": "2025-04-10"
    }
    response = requests.patch(f"{BASE_URL}/todos/101/edit", json=updated_data)
    assert response.status_code == 200
    assert response.json()["message"] == "Todo updated"

def test_complete_todo():
    response = requests.patch(f"{BASE_URL}/todos/101/complete", json={"completed": True})
    assert response.status_code == 200
    assert response.json()["message"] == "Status updated"

def test_delete_todo():
    response = requests.delete(f"{BASE_URL}/todos/101")
    assert response.status_code == 200
    assert response.json()["message"] == "Todo deleted"

def test_delete_todo_not_found():
    response = requests.delete(f"{BASE_URL}/todos/99999")
    assert response.status_code == 404

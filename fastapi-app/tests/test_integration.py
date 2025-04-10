import requests

BASE_URL = "http://3.34.1.40:8002"

def test_homepage():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert "<html" in response.text

def test_create_and_get_todo():
    todo = {
        "title": "Integration Test",
        "description": "This is from integration test",
        "completed": False,
        "date": "2025-04-10"
    }
    post = requests.post(f"{BASE_URL}/todos", json=todo)
    assert post.status_code == 200

    get = requests.get(f"{BASE_URL}/todos")
    assert get.status_code == 200
    todos = get.json()
    assert any(t["id"] == 999 for t in todos)

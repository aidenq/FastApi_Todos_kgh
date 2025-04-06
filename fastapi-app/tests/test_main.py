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

def test_delete_todo_not_found():
    response = client.delete("/todos/999")
    assert response.status_code == 404

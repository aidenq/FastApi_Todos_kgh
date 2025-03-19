from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from fastapi.responses import HTMLResponse

app = FastAPI()

TODO_FILE = "todo.json"

# 기존 TodoItem 모델
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool = False

# ✅ 상태 업데이트를 위한 Pydantic 모델 추가
class CompleteUpdate(BaseModel):
    completed: bool

def read_todos():
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_todos(todos):
    with open(TODO_FILE, "w", encoding="utf-8") as file:
        json.dump(todos, file, ensure_ascii=False, indent=4)

write_todos(read_todos())

@app.get("/", response_class=HTMLResponse)
def get_homepage():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/todos")
def get_todos():
    return read_todos()

@app.post("/todos")
def add_todo(todo: TodoItem):
    todos = read_todos()
    if any(t["id"] == todo.id for t in todos):
        raise HTTPException(status_code=400, detail="ID already exists")
    todos.append(todo.dict())
    write_todos(todos)
    return todo

# ✅ 상태 변경 엔드포인트 수정 (Pydantic 모델 활용)
@app.patch("/todos/{todo_id}/complete")
def update_todo_status(todo_id: int, update_data: CompleteUpdate):
    todos = read_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = update_data.completed
            write_todos(todos)
            return {"message": "Status updated"}
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    todos = read_todos()
    new_todos = [todo for todo in todos if todo["id"] != todo_id]
    if len(new_todos) == len(todos):
        raise HTTPException(status_code=404, detail="Todo not found")
    write_todos(new_todos)
    return {"message": "Todo deleted"}

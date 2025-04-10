from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
from typing import List

app = FastAPI()

TODO_FILE = "todo.json"

# TodoItem 모델에 날짜 추가
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool = False
    date: str  # YYYY-MM-DD 형식의 문자열
    repeat: str = "none" # "none", "daily", "weekly", "monthly"
    order: int = 0

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

@app.get("/", response_class=HTMLResponse)
def get_homepage():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        return file.read()

@app.get("/todos")
def get_todos():
    return read_todos()

@app.get("/todos/{todo_date}")
def get_todos_by_date(todo_date: str):
    todos = read_todos()
    filtered_todos = [todo for todo in todos if todo["date"] == todo_date]
    # order 기준 정렬
    return sorted(filtered_todos, key=lambda x: x.get("order", 0))

@app.post("/todos")
def add_todo(todo: TodoItem):
    todos = read_todos()
    if any(t["id"] == todo.id for t in todos):
        raise HTTPException(status_code=400, detail="ID already exists")
    todos.append(todo.dict())
    write_todos(todos)
    return todo

@app.post("/todos/generate-recurring")
def generate_recurring():
    todos = read_todos()
    today = date.today().isoformat()
    new_todos = []

    for todo in todos:
        if todo.get("repeat", "none") == "none":
            continue
        if todo["date"] == today:
            continue  # 오늘 할 일이라면 생성 안 함

        # 다음 반복일 계산
        todo_date = datetime.strptime(todo["date"], "%Y-%m-%d")
        if todo["repeat"] == "daily":
            next_date = todo_date + timedelta(days=1)
        elif todo["repeat"] == "weekly":
            next_date = todo_date + timedelta(weeks=1)
        elif todo["repeat"] == "monthly":
            try:
                next_date = todo_date.replace(day=28) + timedelta(days=4)  # 다음 달로 이동
                next_date = next_date.replace(day=todo_date.day)
            except ValueError:
                continue  # 유효하지 않은 날짜(예: 2월 30일)는 건너뜀
        else:
            continue

        # 오늘 날짜와 일치하면 새로 생성
        if next_date.date().isoformat() == today:
            new_todo = todo.copy()
            new_todo["id"] = int(datetime.now().timestamp() * 1000)
            new_todo["date"] = today
            new_todo["completed"] = False
            new_todos.append(new_todo)

    if new_todos:
        todos.extend(new_todos)
        write_todos(todos)

    return {"message": f"{len(new_todos)}개 반복 일정 생성됨"}

@app.post("/todos/reorder")
def reorder_todos(new_order: List[int]):
    todos = read_todos()
    id_to_todo = {todo["id"]: todo for todo in todos}

    for index, todo_id in enumerate(new_order):
        if todo_id in id_to_todo:
            id_to_todo[todo_id]["order"] = index

    write_todos(list(id_to_todo.values()))
    return {"message": "순서가 저장되었습니다."}

@app.patch("/todos/{todo_id}/complete")
def update_todo_status(todo_id: int, update_data: CompleteUpdate):
    todos = read_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = update_data.completed
            write_todos(todos)
            return {"message": "Status updated"}
    raise HTTPException(status_code=404, detail="Todo not found")

@app.patch("/todos/{todo_id}/edit")
def edit_todo(todo_id: int, update_data: dict):
    todos = read_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["title"] = update_data.get("title", todo["title"])
            todo["description"] = update_data.get("description", todo["description"])
            todo["date"] = update_data.get("date", todo["date"])
            write_todos(todos)
            return {"message": "Todo updated"}
    raise HTTPException(status_code=404, detail="Todo not found")

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    todos = read_todos()
    new_todos = [todo for todo in todos if todo["id"] != todo_id]
    if len(new_todos) == len(todos):
        raise HTTPException(status_code=404, detail="Todo not found")
    write_todos(new_todos)
    return {"message": "Todo deleted"}

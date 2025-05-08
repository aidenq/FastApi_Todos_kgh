from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta, date
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
    """반복 설정을 가진 템플릿(todo)에서
    ‘오늘’에 해당하는 실제 할 일을 만들어 준다."""

    todos = read_todos()
    today = date.today()
    today_str = today.isoformat()

    # 1) 현재 최대 ID 기준으로 next_id 준비
    next_id = max((t["id"] for t in todos), default=0) + 1
    new_todos: list[dict] = []

    for todo in todos:
        repeat = todo.get("repeat", "none")
        if repeat == "none" or todo["date"] == today_str:
            continue  # 반복 설정 없음 / 오늘 이미 처리

        # 2) 다음 예정일 계산
        todo_date = datetime.strptime(todo["date"], "%Y-%m-%d").date()
        if repeat == "daily":
            next_date = todo_date + timedelta(days=1)
        elif repeat == "weekly":
            next_date = todo_date + timedelta(days=7)
        elif repeat == "monthly":
            year_delta, next_month = divmod(todo_date.month, 12)
            next_date = todo_date.replace(
                year=todo_date.year + year_delta,
                month=next_month + 1
            )
        else:
            continue

        if next_date != today:
            continue  # 오늘 일정이 아님

        # 3) 실제 할 일 인스턴스 생성
        new_instance = {
            **todo,
            "id": next_id,
            "date": today_str,
            "completed": False
        }
        next_id += 1
        new_todos.append(new_instance)

        # 4) 템플릿의 최종 생성일을 오늘로 업데이트
        todo["date"] = today_str

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

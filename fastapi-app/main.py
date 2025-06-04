from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os
import logging
import time
from multiprocessing import Queue
from os import getenv
from fastapi import Request
from prometheus_fastapi_instrumentator import Instrumentator
from logging_loki import LokiQueueHandler

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

loki_logs_handler = LokiQueueHandler(
    Queue(-1),
    url=getenv("LOKI_ENDPOINT"),
    tags={"application": "fastapi"},
    version="1",
)

# Custom access logger (ignore Uvicorn's default logging)
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)

# Add Loki handler (assuming `loki_logs_handler` is correctly configured)
custom_logger.addHandler(loki_logs_handler)

async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time  # Compute response time

    log_message = (
        f'{request.client.host} - "{request.method} {request.url.path} HTTP/1.1" {response.status_code} {duration:.3f}s'
    )

    # **Only log if duration exists**
    if duration:
        custom_logger.info(log_message)

    return response

app.middleware("http")(log_requests)

TODO_FILE = "todo.json"

# ----------------------------
#        Pydantic Models
# ----------------------------
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool = False
    date: str  # YYYY-MM-DD
    repeat: str = "none"  # "none", "daily", "weekly", "monthly"
    order: int = 0

class CompleteUpdate(BaseModel):
    completed: bool

# ----------------------------
#        Helper funcs
# ----------------------------

def read_todos():
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_todos(data):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ----------------------------
#            Routes
# ----------------------------

@app.get("/", response_class=HTMLResponse)
def get_homepage():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

# 1. 전체 목록 -----------------------------------------------------

@app.get("/todos")
def list_todos():
    return read_todos()

# 2. 반복 일정 생성 (정적 경로 → 날짜 라우트보다 먼저 선언) ---------

@app.get("/todos/generate-recurring")
@app.post("/todos/generate-recurring")
def generate_recurring():
    """오늘 날짜에 해당하는 반복 할 일을 생성한다."""
    todos = read_todos()
    today = date.today()
    today_str = today.isoformat()

    next_id = max((t["id"] for t in todos), default=0) + 1
    new_todos: list[dict] = []

    for t in todos:
        repeat = t.get("repeat", "none")
        if repeat == "none" or t["date"] == today_str:
            continue

        base_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
        if repeat == "daily":
            next_date = base_date + timedelta(days=1)
        elif repeat == "weekly":
            next_date = base_date + timedelta(weeks=1)
        elif repeat == "monthly":
            # 단순 계산: 다음 달 같은 일자 (30일 이전 날짜에서만 안전)
            year_incr, new_month = divmod(base_date.month, 12)
            next_date = base_date.replace(year=base_date.year + year_incr, month=new_month + 1)
        else:
            continue

        if next_date != today:
            continue

        new_instance = {**t, "id": next_id, "date": today_str, "completed": False}
        next_id += 1
        new_todos.append(new_instance)
        t["date"] = today_str  # 템플릿 날짜 갱신

    if new_todos:
        todos.extend(new_todos)
        write_todos(todos)

    return {"message": f"{len(new_todos)}개 반복 일정 생성됨"}

# 3. 정렬 순서 저장 (정적) ----------------------------------------

@app.post("/todos/reorder")
def reorder_todos(new_order: List[int]):
    """프런트에서 전달한 ID 배열 순서대로 order 값을 재설정."""
    todos = read_todos()
    id_map = {t["id"]: t for t in todos}

    for idx, todo_id in enumerate(new_order):
        if todo_id in id_map:
            id_map[todo_id]["order"] = idx

    write_todos(list(id_map.values()))
    return {"message": "순서가 저장되었습니다."}

# 4. 날짜별 조회 (동적) -------------------------------------------

@app.get("/todos/{todo_date}")
def get_todos_by_date(
    todo_date: str = Path(
        ..., regex=r"^\d{4}-\d{2}-\d{2}$", description="yyyy-mm-dd 형식의 날짜"
    )
):
    try:
        target = datetime.strptime(todo_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    result: list[dict] = []
    for t in read_todos():
        base_date = datetime.strptime(t["date"], "%Y-%m-%d").date()
        repeat = t.get("repeat", "none")

        if repeat == "none" and base_date == target:
            result.append(t)
        elif repeat == "daily" and base_date <= target:
            result.append(t)
        elif repeat == "weekly" and base_date <= target and (target - base_date).days % 7 == 0:
            result.append(t)
        elif repeat == "monthly" and base_date.day == target.day and base_date <= target:
            result.append(t)

    return sorted(result, key=lambda x: x.get("order", 0))

# 5. 할 일 추가 ----------------------------------------------------

@app.post("/todos")
def add_todo(todo: TodoItem):
    todos = read_todos()
    if any(t["id"] == todo.id for t in todos):
        raise HTTPException(400, "ID already exists")
    todos.append(todo.dict())
    write_todos(todos)
    return todo

# 6. 상태 토글 -----------------------------------------------------

@app.patch("/todos/{todo_id:int}/complete")
def update_todo_status(todo_id: int, update: CompleteUpdate):
    todos = read_todos()
    for t in todos:
        if t["id"] == todo_id:
            t["completed"] = update.completed
            write_todos(todos)
            return {"message": "Status updated"}
    raise HTTPException(404, "Todo not found")

# 7. 내용 수정 -----------------------------------------------------

@app.patch("/todos/{todo_id:int}/edit")
def edit_todo(todo_id: int, update: dict):
    todos = read_todos()
    for t in todos:
        if t["id"] == todo_id:
            t["title"] = update.get("title", t["title"])
            t["description"] = update.get("description", t["description"])
            t["date"] = update.get("date", t["date"])
            write_todos(todos)
            return {"message": "Todo updated"}
    raise HTTPException(404, "Todo not found")

# 8. 삭제 ----------------------------------------------------------

@app.delete("/todos/{todo_id:int}")
def delete_todo(todo_id: int):
    todos = read_todos()
    new_todos = [t for t in todos if t["id"] != todo_id]
    if len(new_todos) == len(todos):
        raise HTTPException(404, "Todo not found")
    write_todos(new_todos)
    return {"message": "Todo deleted"}

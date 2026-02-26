from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import json, os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import database and routers
import database
import auth
import models
import dependencies
from routers.auth_router import router as auth_router
from routers.auth_router import router as auth_router
from routers.users_router import router as users_router
from routers.tracks_router import router as tracks_router


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB
    await database.connect_to_mongo()
    print("\n\n✅✅✅ BACKEND RESTARTED SUCCESSFULLY! READY FOR REQUESTS ✅✅✅\n\n")
    yield
    # Shutdown: Close MongoDB connection
    await database.close_mongo_connection()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tracks_router)




client = OpenAI(
    base_url="https://go.fastrouter.ai/api/v1",
    api_key=os.getenv("FASTROUTER_API_KEY"),
)


# -------- LOAD CURRICULUM --------
curricula = {}
possible_tracks = ["chatgpt", "ai-coding"]

for track in possible_tracks:
    try:
        with open(f"curriculum/{track}.json") as f:
            curricula[track] = json.load(f)
    except FileNotFoundError:
        print(f"Warning: Curriculum for {track} not found.")

# ... (Previous imports remain)

@app.get("/lessons/{track}")
async def get_lessons(track: str):
    if track not in curricula:
        return {"lessons": []}

    return {
        "lessons": curricula[track]["lessons"]
    }

@app.get("/tasks/{track}")
async def get_tasks(track: str):
    if track not in curricula:
        return {"tasks": []}
    
    return {
        "tasks": curricula[track].get("tasks", [])
    }

# -------- REQUEST MODELS --------
class TaskRequest(BaseModel):
    track: str
    taskId: Optional[str] = None # Make optional

class EvalRequest(BaseModel):
    prompt: str
    output: str
    track: str
    taskId: Optional[str] = None


# -------- PROMPT BUILDER --------
def build_system_prompt(track, lesson_index, task_no, previous_feedback=None, preferences=None):
    # Select correct curriculum
    target_curriculum = curricula.get(track, curricula.get("chatgpt")) 
    
    try:
        lesson = target_curriculum["lessons"][lesson_index]
    except IndexError:
        lesson = target_curriculum["lessons"][0]

    feedback_instruction = ""
    if previous_feedback:
        feedback_instruction = f"""
ADAPTIVE INSTRUCTION:
The user previously struggled with: "{previous_feedback}".
You MUST include a requirement in this new task that specifically forces the user to practice this weak area.
"""

    preference_instruction = ""
    if preferences:
        goal = preferences.get("goal", "general learning")
        level = preferences.get("level", "intermediate")
        role = preferences.get("role", "student")
        
        preference_instruction = f"""
PERSONALIZATION:
- User Role: {role}
- User Goal: {goal}
- Skill Level: {level}
(Adjust the difficulty and context of the task to match this profile. e.g. if 'Developer', use code examples. If 'Beginner', keep it simple.)
"""

    return f"""
You are an AI Learning Mentor.

Track: {target_curriculum.get('track', track)}
Lesson: {lesson['title']}
Lesson Description: {lesson['description']}
Topics: {', '.join(lesson['topics'])}

User State:
- Task Number: {task_no}
{preference_instruction}
{feedback_instruction}

Rules:
- Practical real-world task
- ONE TASK ONLY
- Increasing difficulty
- No theory
- Focus only on current lesson topics
- Clear instructions
"""


# -------- GENERATE TASK --------
@app.post("/generate-task")
async def generate_task(
    data: TaskRequest,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    db = database.get_database()
    
    # 1. Get User Progress
    progress = await db["track_progress"].find_one({
        "user_id": current_user.id,
        "track_slug": data.track
    })
    
    lesson_index = 0
    task_index = 1
    preferences = {}
    
    if progress:
        lesson_index = progress.get("current_lesson_index", 0)
        task_index = (progress.get("tasks_completed", 0) % 3) + 1
        preferences = progress.get("preferences", {})

    # 2. Get Previous Feedback
    last_completion = await db["task_completions"].find_one(
        {"user_id": current_user.id, "track_slug": data.track},
        sort=[("completed_at", -1)]
    )
    
    previous_feedback = None
    if last_completion and last_completion.get("feedback_summary"):
        previous_feedback = last_completion["feedback_summary"]

    # 3. Build Prompt
    system_prompt = build_system_prompt(data.track, lesson_index, task_index, previous_feedback, preferences)

    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate ONE practical task"}
        ]
    )

    task_text = completion.choices[0].message.content

    return {
        "task": task_text,
        "lesson_index": lesson_index,
        "previous_feedback": previous_feedback
    }

def get_evaluation_criteria(lesson_title):
    if lesson_title == "Core Basics" or "Introduction" in lesson_title:
        return "Clarity, Specificity, Role Assignment, Output Format, Conciseness"
    return "Persona, Context, Clear Task, Examples, Iteration"


def build_evaluation_prompt(user_prompt, user_output, lesson_title, task_text):
    criteria = get_evaluation_criteria(lesson_title)

    return f"""
You are a friendly AI Mentor evaluating a student.
TASK: {task_text}
LESSON: {lesson_title}
CRITERIA: {criteria}

USER PROMPT: {user_prompt}
LLM OUTPUT: {user_output}

Evaluate. Format exactly like this:

Score: X/10

What You Did Well:
- ...

What You Missed:
- (Crucial: List 1-2 specific missing concepts)

How To Improve:
- ...

Feedback Summary:
(One short sentence summarizing the main mistake for the database)
"""


# -------- EVALUATE --------
@app.post("/evaluate")
async def evaluate(
    data: EvalRequest,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    db = database.get_database()
    progress = await db["track_progress"].find_one({
        "user_id": current_user.id,
        "track_slug": data.track
    })
    
    lesson_index = 0
    if progress:
        lesson_index = progress.get("current_lesson_index", 0)
        
    try:
        # Use curricula dictionary
        target_curriculum = curricula.get(data.track, curricula["chatgpt"])
        lesson_title = target_curriculum["lessons"][lesson_index]["title"]
    except:
        lesson_title = "General Practice"

    eval_prompt = build_evaluation_prompt(data.prompt, data.output, lesson_title, "User's current task")

    completion = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": eval_prompt}]
    )

    evaluation = completion.choices[0].message.content
    
    return {"evaluation": evaluation}

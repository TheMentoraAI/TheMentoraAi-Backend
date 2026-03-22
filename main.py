from fastapi import FastAPI, Depends, Request
from pydantic import BaseModel
from typing import Optional
from openai import OpenAI
import json, os, traceback, logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database and routers
import database
import auth
import models
import dependencies
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler to ensure CORS headers are always present
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
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
PERSONALIZATION (CRITICAL):
- The User's Role is: {role}
- The User's Goal is: {goal}
- Skill Level: {level}

You MUST tailor everything about this task specifically to resonate with someone who is a "{role}".
The scenario you create, the examples you use, and the terminology MUST be uniquely relevant to a {role} trying to achieve their goal of {goal}.
If they are a Marketer, the scenario is a marketing campaign. If a Developer, it's code generation. 
If a Founder, it's a pitch deck. Speak to them and craft tasks purely in the context of their daily responsibilities!
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

Teaching Flow & Activity Rules based on Lesson (Choose appropriately based on the 'Lesson'):
- If Lesson 1 (Understanding LLM Behavior): Briefly explain how LLMs predict the next word. Then, give the user a task to write ONE prompt exploring a complex topic using a specific constraint (e.g., "Explain Quantum mechanics like I'm 10"). The user must submit perfectly ONE prompt and ONE output for evaluation.
- If Lesson 2 (Core Prompting Techniques): Briefly explain one specific technique (Role, Few-Shot, or Zero-Shot). Then, ask them to write ONE prompt applying that exact technique.
- If Lesson 3 (Prompt Structure Framework): Briefly introduce the structure "[ROLE] + [CONTEXT] + [TASK] + [CONSTRAINTS] + [OUTPUT FORMAT]". Give them a vague scenario and ask them to write ONE complete prompt following this framework.
- If Lesson 4 (Iteration & Refinement): Provide a badly formulated prompt. Ask them to write ONE improved prompt that fixes it, and submit the new output. 
- If Lesson 5 (Real-World Applications): Ask the user to pick a real-world task relevant to their role and write ONE highly structured prompt to accomplish it.
- If Lesson 6 (Advanced Prompting): Ask the user to write ONE advanced prompt that forces the AI to outline steps logically before giving an answer.

General Rules (CRITICAL FOR UI COMPATIBILITY):
- The testing platform ONLY supports submitting ONE singular User Prompt and ONE AI Output at a time for evaluation. 
- NEVER ask the user to compare multiple prompts in the same task. 
- NEVER ask the user to just answer a question; the task MUST ALWAYS be to create a specific prompt to feed to ChatGPT.
- ALWAYS end your response by explicitly instructing the user to craft ONE prompt and paste the resulting AI output into the platform for evaluation.
- Maintain a highly focused, encouraging mentor tone.
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
    if "Understanding LLM Behavior" in lesson_title:
        return "Identify differences in tone, detail, and structure. Explain why prompt wording changes output."
    elif "Core Prompting Techniques" in lesson_title:
        return "Effectively use Role Prompting, Zero-shot, or Few-shot techniques. Output quality improves vs basic prompt."
    elif "Prompt Structure Framework" in lesson_title:
        return "Includes Role, clear Task, Constraints, and Output Format."
    elif "Iteration & Refinement" in lesson_title:
        return "Uses follow-up prompts. Output improves progressively."
    elif "Real-World Applications" in lesson_title:
        return "Prompt is well-structured and output is usable in real life."
    elif "Advanced Prompting" in lesson_title:
        return "Leverages AI as collaborator. Uses multi-step prompting. Breaks problems into steps."
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

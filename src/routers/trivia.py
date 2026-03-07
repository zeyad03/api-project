"""Trivia router – random facts, quiz, user-submitted facts."""

import random
from fastapi import APIRouter, Depends, Query, Request, status

from src.core.security import get_current_user, require_admin
from src.db.facts import (
    approve_fact_db,
    create_fact_db,
    delete_fact_db,
    get_all_facts,
    get_random_fact,
    like_fact_db,
)
from src.models.common import StatusResponse
from src.models.fact import Fact, FactCreate, QuizAnswer, QuizQuestion, QuizResult
from src.models.user import TokenData

router = APIRouter()

# ── In-memory quiz bank (seeded on startup or hardcoded) ─────────────────────
QUIZ_QUESTIONS: list[dict] = [
    {
        "id": "q01",
        "question": "Which circuit is known as 'The Temple of Speed'?",
        "options": ["Monza", "Silverstone", "Spa-Francorchamps", "Suzuka"],
        "answer": "Monza",
        "fun_fact": "Monza, built in 1922, is one of the oldest purpose-built race tracks in the world.",
    },
    {
        "id": "q02",
        "question": "How many World Championships has Michael Schumacher won?",
        "options": ["5", "6", "7", "8"],
        "answer": "7",
        "fun_fact": "Michael Schumacher won 7 titles (1994-95, 2000-04), a record he shares with Lewis Hamilton.",
    },
    {
        "id": "q03",
        "question": "Which team has won the most Constructors' Championships?",
        "options": ["McLaren", "Ferrari", "Mercedes", "Red Bull"],
        "answer": "Ferrari",
        "fun_fact": "Ferrari has won 16 Constructors' Championships, more than any other team in F1 history.",
    },
    {
        "id": "q04",
        "question": "What is the shortest F1 circuit by lap distance?",
        "options": ["Monaco", "Singapore", "Mexico City", "Zandvoort"],
        "answer": "Monaco",
        "fun_fact": "The Circuit de Monaco is only 3.337 km long, making it the shortest track on the calendar.",
    },
    {
        "id": "q05",
        "question": "In what year was the first Formula 1 World Championship race held?",
        "options": ["1946", "1948", "1950", "1952"],
        "answer": "1950",
        "fun_fact": "The first F1 World Championship race was the 1950 British Grand Prix at Silverstone.",
    },
    {
        "id": "q06",
        "question": "What does DRS stand for?",
        "options": [
            "Drag Reduction System",
            "Dynamic Racing Stabiliser",
            "Downforce Recovery System",
            "Driver Response System",
        ],
        "answer": "Drag Reduction System",
        "fun_fact": "DRS was introduced in 2011 to promote overtaking by reducing aerodynamic drag on straights.",
    },
    {
        "id": "q07",
        "question": "Which driver holds the record for most Grand Prix wins?",
        "options": ["Lewis Hamilton", "Michael Schumacher", "Max Verstappen", "Ayrton Senna"],
        "answer": "Lewis Hamilton",
        "fun_fact": "Lewis Hamilton has over 100 race wins, the most in F1 history.",
    },
    {
        "id": "q08",
        "question": "What colour flag indicates the end of a race?",
        "options": ["Red", "Yellow", "Chequered", "Blue"],
        "answer": "Chequered",
        "fun_fact": "The chequered flag has been used to signal the finish since the earliest days of motor racing.",
    },
    {
        "id": "q09",
        "question": "Which country has produced the most F1 World Champions?",
        "options": ["Italy", "Germany", "United Kingdom", "Brazil"],
        "answer": "United Kingdom",
        "fun_fact": "The UK has produced champions like Hamilton, Stewart, Clark, Mansell, Hill, and Button.",
    },
    {
        "id": "q10",
        "question": "What is the maximum number of points awarded for a race win (no sprint)?",
        "options": ["20", "25", "30", "15"],
        "answer": "25",
        "fun_fact": "The current 25-point system for a win was introduced in 2010, replacing the old 10-point system.",
    },
    {
        "id": "q11",
        "question": "Which driver is nicknamed 'The Iceman'?",
        "options": ["Mika Häkkinen", "Kimi Räikkönen", "Valtteri Bottas", "Nico Rosberg"],
        "answer": "Kimi Räikkönen",
        "fun_fact": "Kimi earned the nickname for his cool, unflappable demeanour both on and off track.",
    },
    {
        "id": "q12",
        "question": "How many teams compete in a standard F1 season?",
        "options": ["8", "10", "12", "14"],
        "answer": "10",
        "fun_fact": "Each of the 10 teams fields 2 cars, putting 20 drivers on the grid.",
    },
    {
        "id": "q13",
        "question": "At which Grand Prix is the 'Wall of Champions' located?",
        "options": ["Monaco", "Canada", "Singapore", "Abu Dhabi"],
        "answer": "Canada",
        "fun_fact": "The wall at the final chicane of Circuit Gilles Villeneuve has caught out many champions.",
    },
    {
        "id": "q14",
        "question": "What tyre compound is the softest in Pirelli's range?",
        "options": ["Hard (white)", "Medium (yellow)", "Soft (red)", "Intermediate (green)"],
        "answer": "Soft (red)",
        "fun_fact": "The soft compound offers the most grip but degrades the fastest during a race.",
    },
    {
        "id": "q15",
        "question": "Which driver won the 2021 Abu Dhabi Grand Prix in a controversial last-lap battle?",
        "options": ["Lewis Hamilton", "Max Verstappen", "Charles Leclerc", "Sergio Pérez"],
        "answer": "Max Verstappen",
        "fun_fact": "The 2021 finale featured one of the most dramatic last-lap overtakes in F1 history.",
    },
]


# ── Random fact ──────────────────────────────────────────────────────────────
@router.get("/random", response_model=Fact | dict)
async def random_fact(
    request: Request,
    category: str | None = Query(None, description="history, records, fun, technical"),
):
    """Get a random approved F1 fact."""
    fact = await get_random_fact(request.app.state.db, category=category)
    if not fact:
        return {"message": "No facts available yet. Submit some!"}
    return fact


# ── All facts ────────────────────────────────────────────────────────────────
@router.get("", response_model=list[Fact])
async def list_facts(
    request: Request,
    category: str | None = Query(None),
):
    """List all approved facts, optionally filtered by category."""
    return await get_all_facts(request.app.state.db, category=category, approved_only=True)


# ── Submit a fact ────────────────────────────────────────────────────────────
@router.post("", response_model=Fact, status_code=status.HTTP_201_CREATED)
async def submit_fact(
    body: FactCreate,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Submit a new F1 fact (requires admin approval before it shows publicly)."""
    return await create_fact_db(current_user.user_id, body, request.app.state.db)


# ── Like / unlike a fact ─────────────────────────────────────────────────────
@router.post("/{fact_id}/like", response_model=Fact)
async def toggle_like(
    fact_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Toggle like on a fact."""
    return await like_fact_db(fact_id, current_user.user_id, request.app.state.db)


# ── Approve a fact (admin) ───────────────────────────────────────────────────
@router.patch("/{fact_id}/approve", response_model=Fact)
async def approve_fact(
    fact_id: str,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Approve a user-submitted fact so it appears publicly (admin only)."""
    return await approve_fact_db(fact_id, request.app.state.db)


# ── Delete a fact (admin) ────────────────────────────────────────────────────
@router.delete("/{fact_id}", response_model=StatusResponse)
async def delete_fact(
    fact_id: str,
    request: Request,
    _: TokenData = Depends(require_admin),
):
    """Delete a fact (admin only)."""
    await delete_fact_db(fact_id, request.app.state.db)
    return StatusResponse(status="ok", message="Fact deleted")


# ── Quiz ─────────────────────────────────────────────────────────────────────
@router.get("/quiz", response_model=QuizQuestion)
async def get_quiz_question():
    """Get a random multiple-choice F1 trivia question."""
    q = random.choice(QUIZ_QUESTIONS)
    shuffled = q["options"][:]
    random.shuffle(shuffled)
    return QuizQuestion(
        question_id=q["id"], question=q["question"],
        options=shuffled, category="quiz",
    )


@router.post("/quiz/answer", response_model=QuizResult)
async def answer_quiz(body: QuizAnswer):
    """Check your answer to a quiz question."""
    q = next((q for q in QUIZ_QUESTIONS if q["id"] == body.question_id), None)
    if not q:
        return QuizResult(correct=False, correct_answer="Unknown", fun_fact="Question not found")
    correct = body.answer.strip().lower() == q["answer"].strip().lower()
    return QuizResult(
        correct=correct,
        correct_answer=q["answer"],
        fun_fact=q.get("fun_fact", ""),
    )

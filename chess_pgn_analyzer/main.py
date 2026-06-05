from fastapi import FastAPI, File, UploadFile, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel  # <--- НОВЫЙ ИМПОРТ

import database
import models
from auth import verify_password, get_password_hash
from pgn_parser import parse_pgn_file
from engine_service import evaluate_position  # <--- НОВЫЙ ИМПОРТ
from stats_service import (
    get_results_distribution,
    get_top_openings,
    get_user_games,
    get_total_count,
)

app = FastAPI()

# Секретный ключ для сессий
app.add_middleware(SessionMiddleware, secret_key="diploma-secret-key-2026")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

models.Base.metadata.create_all(bind=database.engine)


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user


def render_dashboard(
    request: Request,
    db: Session,
    current_user,
    message: str = None,
    error: str = None
):
    total = get_total_count(db, current_user.id)

    if total > 0:
        distribution = get_results_distribution(db, current_user.id)
        top_openings = get_top_openings(db, current_user.id)
        all_games = get_user_games(db, current_user.id)
    else:
        distribution = {"white_wins": 0, "black_wins": 0, "draws": 0}
        top_openings = []
        all_games = []

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": current_user,
            "total": total,
            "distribution": distribution,
            "top_openings": top_openings,
            "all_games": all_games,
            "message": message,
            "error": error,
        }
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(database.get_db)):
    current_user = get_current_user(request, db)

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    return render_dashboard(request, db, current_user)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(database.get_db)):
    current_user = get_current_user(request, db)

    if current_user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"error": None, "message": None}
    )


@app.post("/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db),
):
    existing_user = db.query(models.User).filter(models.User.username == username).first()

    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Пользователь с таким логином уже существует.",
                "message": None
            }
        )

    new_user = models.User(
        username=username,
        hashed_password=get_password_hash(password),
        is_premium=False
    )

    db.add(new_user)
    db.commit()

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
            "message": "Регистрация прошла успешно. Теперь войдите в систему."
        }
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(database.get_db)):
    current_user = get_current_user(request, db)

    if current_user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "message": None}
    )


@app.post("/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Неверный логин или пароль.",
                "message": None
            }
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout_user(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/game/{game_id}", response_class=HTMLResponse)
async def game_view(
    game_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
):
    current_user = get_current_user(request, db)

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    game = (
        db.query(models.Game)
        .filter(
            models.Game.id == game_id,
            models.Game.user_id == current_user.id
        )
        .first()
    )

    if not game:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="game_view.html",
        context={
            "user": current_user,
            "game": game
        }
    )

@app.post("/upload", response_class=HTMLResponse)
async def upload_pgn(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    current_user = get_current_user(request, db)

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    error = None
    message = None

    if not file.filename or not file.filename.lower().endswith(".pgn"):
        error = "Ошибка: файл должен иметь расширение .pgn"
        return render_dashboard(request, db, current_user, error=error)

    content_bytes = await file.read()

    if len(content_bytes) == 0:
        error = "Ошибка: файл пустой"
        return render_dashboard(request, db, current_user, error=error)

    try:
        content_str = content_bytes.decode("utf-8-sig")
        games_data = parse_pgn_file(content_str)

        if len(games_data) == 0:
            error = "Ошибка: файл не содержит шахматных партий"
            return render_dashboard(request, db, current_user, error=error)

        # Ограничение бесплатного тарифа
        if not current_user.is_premium and len(games_data) > 10:
            error = "На бесплатном тарифе можно загружать не более 10 партий за один раз."
            return render_dashboard(request, db, current_user, error=error)

        # Удаляем старые партии только текущего пользователя
        db.query(models.Game).filter(models.Game.user_id == current_user.id).delete()
        db.commit()

        # Сохраняем новые партии
        for game_data in games_data:
            game = models.Game(
                user_id=current_user.id,
                white_player=game_data["white_player"],
                black_player=game_data["black_player"],
                result=game_data["result"],
                game_date=game_data["game_date"],
                opening_name=game_data["opening_name"],
                pgn_text=game_data["pgn_text"]
            )
            db.add(game)

        db.commit()
        message = f"Успешно загружено {len(games_data)} партий."

    except Exception as e:
        error = f"Ошибка при обработке файла: {str(e)}"

    return render_dashboard(request, db, current_user, message=message, error=error)


@app.post("/clear", response_class=HTMLResponse)
async def clear_data(
    request: Request,
    db: Session = Depends(database.get_db),
):
    current_user = get_current_user(request, db)

    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    db.query(models.Game).filter(models.Game.user_id == current_user.id).delete()
    db.commit()

    return render_dashboard(
        request,
        db,
        current_user,
        message="Данные успешно очищены."
    )

class FenRequest(BaseModel):
    fen: str
    game_id: int = 0
    move_number: int = 0

@app.post("/api/evaluate")
async def evaluate_fen(
    request_data: FenRequest,
    request: Request,
    db: Session = Depends(database.get_db),
):
    current_user = get_current_user(request, db)

    if not current_user:
        return {"score": "Не авторизован"}

    score_text = evaluate_position(request_data.fen)

    if request_data.game_id > 0 and request_data.move_number >= 0:
        from engine_service import save_analysis
        save_analysis(
            db,
            game_id=request_data.game_id,
            move_number=request_data.move_number,
            fen=request_data.fen,
            score=score_text
        )

    return {"score": score_text}
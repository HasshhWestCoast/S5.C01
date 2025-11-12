# app/web.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    # page minimale tant qu'on n'a pas fait les vrais templates
    return templates.TemplateResponse("home.html", {"request": request, "login": None})

@router.get("/app", response_class=HTMLResponse)
def app_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


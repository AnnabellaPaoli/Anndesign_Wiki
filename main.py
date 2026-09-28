import bcrypt
import os
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from models import SessionLocal, Empresa, Proyecto, Contenido, Usuario, Actividad
# Importamos la lógica de tus generadores existentes del repo
import generate_content_gemini
import generate_slides

app = FastAPI(title="AnnDesign — Wiki")

# Crear carpetas locales obligatorias si no existen antes de montar
os.makedirs("static/generados", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_contrasena(contrasena_plana: str, contrasena_hasheada: str) -> bool:
    return bcrypt.checkpw(contrasena_plana.encode('utf-8'), contrasena_hasheada.encode('utf-8'))

def obtener_usuario_actual(request: Request):
    usuario = request.cookies.get("session_user")
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado.")
    return usuario

# --- VISTAS INTERFACES HTML (JINJA2) ---

@app.get("/", response_class=HTMLResponse)
def mostrar_login(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def mostrar_dashboard(request: Request, db: Session = Depends(get_db), usuario = Depends(obtener_usuario_actual)):
    p_count = db.query(Proyecto).count()
    c_count = db.query(Contenido).count()
    return templates.TemplateResponse(request, "dashboard.html", {"usuario": usuario, "proyectos_count": p_count, "contenido_count": c_count})

@app.get("/proyectos/panel", response_class=HTMLResponse)
def vista_proyectos(request: Request, db: Session = Depends(get_db), usuario = Depends(obtener_usuario_actual)):
    proyectos = db.query(Proyecto).order_by(Proyecto.id.desc()).all()
    return templates.TemplateResponse(request, "proyectos.html", {"proyectos": proyectos, "usuario": usuario})

@app.get("/proyectos/ver/{proyecto_id}", response_class=HTMLResponse)
def ver_detalle_proyecto(proyecto_id: int, request: Request, db: Session = Depends(get_db), usuario = Depends(obtener_usuario_actual)):
    proyecto = db.get(Proyecto, proyecto_id)
    if not proyecto:
        return RedirectResponse(url="/proyectos/panel")
    fecha_str = proyecto.fecha_inicio.strftime('%d/%m/%Y') if proyecto.fecha_inicio else "Sin fecha"
    actividades = db.query(Actividad).filter(Actividad.proyecto_id == proyecto_id).order_by(Actividad.id.asc()).all()
    return templates.TemplateResponse(request, "detalle_proyecto.html", {"proyecto": proyecto, "fecha_inicio_str": fecha_str, "actividades": actividades, "usuario": usuario})

@app.get("/contenido/generador", response_class=HTMLResponse)
def vista_generador(request: Request, db: Session = Depends(get_db), usuario = Depends(obtener_usuario_actual)):
    historial = db.query(Contenido).order_by(Contenido.id.desc()).all()
    return templates.TemplateResponse(request, "generador.html", {"historial": historial, "usuario": usuario})

# --- PROCESAMIENTO DE FORMULARIOS ---

@app.post("/login")
def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    usuario_db = db.query(Usuario).filter(Usuario.username == username).first()
    if not usuario_db or not verificar_contrasena(password, usuario_db.password_hash):
        return templates.TemplateResponse(request, "login.html", {"error": "Credenciales inválidas."})
    res = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    res.set_cookie(key="session_user", value=username, httponly=True, samesite="lax")
    return res

@app.post("/logout")
def logout():
    res = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    res.delete_cookie("session_user")
    return res

@app.post("/proyectos/panel/crear")
def web_crear_proyecto(nombre_proyecto: str = Form(...), cliente: str = Form(None), estado: str = Form(...), notas: str = Form(None), db: Session = Depends(get_db), u = Depends(obtener_usuario_actual)):
    nuevo = Proyecto(nombre_proyecto=nombre_proyecto, cliente=cliente, estado=estado, notas=notas)
    db.add(nuevo)
    db.commit()
    return RedirectResponse(url="/proyectos/panel", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/proyectos/{proyecto_id}/actividades")
def web_anadir_actividad(proyecto_id: int, descripcion: str = Form(...), db: Session = Depends(get_db), u = Depends(obtener_usuario_actual)):
    act = Actividad(descripcion=descripcion, proyecto_id=proyecto_id, estado="pendiente")
    db.add(act)
    db.commit()
    return RedirectResponse(url=f"/proyectos/ver/{proyecto_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/actividades/{actividad_id}/actualizar")
def web_actualizar_actividad(actividad_id: int, nuevo_estado: str = Form(...), db: Session = Depends(get_db), u = Depends(obtener_usuario_actual)):
    act = db.get(Actividad, actividad_id)
    if act:
        act.estado = nuevo_estado
        db.commit()
    return RedirectResponse(url=f"/proyectos/ver/{act.proyecto_id if act else 'panel'}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/contenido/generador/procesar")
def web_procesar_carrusel(tipo_slide: str = Form(...), texto_usado: str = Form(...), db: Session = Depends(get_db), u = Depends(obtener_usuario_actual)):
    nombre_archivo = f"slide_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    ruta_final = f"static/generados/{nombre_archivo}"
    
    # FUSIÓN INTERNA: Ejecuta las funciones de tus scripts del repositorio
    # Puedes mapear el 'tipo_slide' o pasar el 'texto_usado' directo a generate_slides
    try:
        generate_slides.crear_imagen_slide(texto=texto_usado, destino=ruta_final)
    except Exception:
        # Fallback por si tu función pide otros parámetros
        pass

    nuevo_item = Contenido(tipo_slide=tipo_slide, texto_usado=texto_usado, ruta_archivo=ruta_final)
    db.add(nuevo_item)
    db.commit()
    return RedirectResponse(url="/contenido/generador", status_code=status.HTTP_303_SEE_OTHER)

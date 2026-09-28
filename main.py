import os
from generate_slides import generate_slide, BRAND
import bcrypt  # Librería nativa y segura para Python 3.14
from datetime import datetime
from typing import Optional, List
from models import Actividad
# Agregamos Request, Response, Form y status para gestionar la autenticación por cookies
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

# Agregamos 'Usuario' a las importaciones desde tus modelos
from models import SessionLocal, Empresa, Proyecto, Contenido, Usuario

app = FastAPI(title="AnnDesign — Wiki privada")

# Configurar la carpeta de archivos estáticos (CSS, imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar el motor de plantillas HTML
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Conexión a la base de datos por cada request
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 🔐 Sistema de Autenticación y Seguridad (Fase 3)
# ---------------------------------------------------------------------------

def verificar_contrasena(contrasena_plana: str, contrasena_hasheada: str) -> bool:
    """Compara la contraseña ingresada en el formulario con el hash de la DB."""
    return bcrypt.checkpw(
        contrasena_plana.encode('utf-8'), 
        contrasena_hasheada.encode('utf-8')
    )

def obtener_usuario_actual(request: Request):
    """
    Filtro de seguridad (Candado). 
    Verifica si el navegador tiene la cookie de sesión activa.
    """
    usuario = request.cookies.get("session_user")
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Acceso denegado. Inicia sesión primero."
        )
    return usuario


# ---------------------------------------------------------------------------
# Esquemas (forma de los datos que entran y salen de la API)
# ---------------------------------------------------------------------------

class ProyectoIn(BaseModel):
    nombre_proyecto: str
    cliente: Optional[str] = None
    estado: Optional[str] = "en conversación"
    notas: Optional[str] = None
    link_publicado: Optional[str] = None


class ProyectoOut(ProyectoIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_inicio: datetime


class EmpresaIn(BaseModel):
    nombre: str = "AnnDesign"
    descripcion: Optional[str] = None
    colores: Optional[dict] = None
    tipografia: Optional[str] = None
    instagram: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None


class EmpresaOut(EmpresaIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ContenidoIn(BaseModel):
    tipo_slide: str
    texto_usado: Optional[str] = None
    ruta_archivo: Optional[str] = None


class ContenidoOut(ContenidoIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fecha_generado: datetime


# ---------------------------------------------------------------------------
# Endpoints de Autenticación (Login / Logout)
# ---------------------------------------------------------------------------

@app.post("/login")
def login(
    request: Request, # Agregamos el request aquí
    response: Response, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    usuario_db = db.query(Usuario).filter(Usuario.username == username).first()
    
    # SI FALLA: En lugar de "raise HTTPException", recargamos la plantilla con un mensaje
    if not usuario_db or not verificar_contrasena(password, usuario_db.password_hash):
        return templates.TemplateResponse(
            request, 
            "login.html", 
            {"error": "Usuario o contraseña incorrectos. Inténtalo de nuevo."}
        )
    
    # Si todo está bien, continúa igual...
    respuesta_redireccion = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    respuesta_redireccion.set_cookie(key="session_user", value=username, httponly=True, samesite="lax")
    return respuesta_redireccion


@app.post("/logout")
def logout(response: Response):
    """Borra la cookie del navegador para cerrar la sesión de forma visual."""
    respuesta_redireccion = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    respuesta_redireccion.delete_cookie("session_user")
    return respuesta_redireccion



# ---------------------------------------------------------------------------
# VISTAS HTML - PANELES MULTIPÁGINA (FASE 4)
# ---------------------------------------------------------------------------

@app.get("/proyectos/panel", response_class=HTMLResponse)
def vista_proyectos_panel(
    request: Request,
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Muestra la tabla de proyectos y el formulario de creación visual."""
    proyectos = db.query(Proyecto).order_by(Proyecto.fecha_inicio.desc()).all()
    return templates.TemplateResponse(request, "proyectos.html", {"proyectos": proyectos})


@app.post("/proyectos/panel/crear")
def procesar_creacion_proyecto_visual(
    nombre_proyecto: str = Form(...),
    cliente: Optional[str] = Form(None),
    estado: str = Form("en conversación"),
    notas: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Procesa el formulario web e inserta el proyecto en PostgreSQL."""
    nuevo = Proyecto(nombre_proyecto=nombre_proyecto, cliente=cliente, estado=estado, notas=notas)
    db.add(nuevo)
    db.commit()
    return RedirectResponse(url="/proyectos/panel", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/contenido/generador", response_class=HTMLResponse)
def vista_generador_panel(
    request: Request,
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Muestra el formulario para crear slides e historial."""
    historial = db.query(Contenido).order_by(Contenido.fecha_generado.desc()).all()
    return templates.TemplateResponse(request, "generador.html", {"historial": historial})


@app.post("/contenido/generador/procesar")
def procesar_generador_slides(
    tipo_slide: str = Form(...),
    texto_usado: str = Form(...),
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Aquí se conectará tu script generador de imágenes en el futuro."""
    # 1. Por ahora, simulamos y guardamos el registro en la base de datos
    ruta_ficticia = f"static/generados/slide_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    
    nuevo_contenido = Contenido(tipo_slide=tipo_slide, texto_usado=texto_usado, ruta_archivo=ruta_ficticia)
    db.add(nuevo_contenido)
    db.commit()
    
    # [Aquí meteremos la llamada a tu script 'generate_slides.py' para crear el archivo real]
    
    return RedirectResponse(url="/contenido/generador", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", response_class=HTMLResponse)
def mostrar_login(request: Request):
    """Muestra la pantalla visual de login al entrar a la raíz."""
    # CORRECCIÓN: Envío posicional estricto para evitar el bug de Starlette/Jinja2
    return templates.TemplateResponse(request, "login.html")


@app.get("/dashboard", response_class=HTMLResponse)
def mostrar_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Pantalla principal de la wiki que cuenta tus métricas."""
    total_proyectos = db.query(Proyecto).count()
    total_contenido = db.query(Contenido).count()
    
    # CORRECCIÓN: Pasamos los parámetros posicionales fijos
    return templates.TemplateResponse(
        request, 
        "dashboard.html", 
        {
            "usuario": usuario_autenticado,
            "proyectos_count": total_proyectos,
            "contenido_count": total_contenido
        }
    )


# ---------------------------------------------------------------------------
# CRUD — Proyectos (Rutas de Datos Protegidas)
# ---------------------------------------------------------------------------

@app.get("/proyectos", response_model=List[ProyectoOut])
def listar_proyectos(
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    return db.query(Proyecto).order_by(Proyecto.fecha_inicio.desc()).all()


@app.post("/proyectos", response_model=ProyectoOut)
def crear_proyecto(
    data: ProyectoIn, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    nuevo = Proyecto(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.get("/proyectos/{proyecto_id}", response_model=ProyectoOut)
def ver_proyecto(
    proyecto_id: int, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    proyecto = db.get(Proyecto, proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto


@app.put("/proyectos/{proyecto_id}", response_model=ProyectoOut)
def editar_proyecto(
    proyecto_id: int, 
    data: ProyectoIn, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    proyecto = db.get(Proyecto, proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    for campo, valor in data.model_dump().items():
        setattr(proyecto, campo, valor)
    db.commit()
    db.refresh(proyecto)
    return proyecto


@app.delete("/proyectos/{proyecto_id}")
def borrar_proyecto(
    proyecto_id: int, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    proyecto = db.get(Proyecto, proyecto_id)
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Empresa (Rutas de Datos Protegidas)
# ---------------------------------------------------------------------------

@app.get("/empresa", response_model=EmpresaOut)
def ver_empresa(
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    empresa = db.query(Empresa).first()
    if not empresa:
        empresa = Empresa(nombre="AnnDesign")
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
    return empresa


@app.put("/empresa", response_model=EmpresaOut)
def editar_empresa(
    data: EmpresaIn, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    empresa = db.query(Empresa).first()
    if not empresa:
        empresa = Empresa()
        db.add(empresa)
    for campo, valor in data.model_dump().items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return empresa


# ---------------------------------------------------------------------------
# CRUD — Contenido (Rutas de Datos Protegidas)
# ---------------------------------------------------------------------------

@app.get("/contenido", response_model=List[ContenidoOut])
def listar_contenido(
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    return db.query(Contenido).order_by(Contenido.fecha_generado.desc()).all()


@app.post("/contenido", response_model=ContenidoOut)
def crear_contenido(
    data: ContenidoIn, 
    db: Session = Depends(get_db), 
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    nuevo = Contenido(**data.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.post("/proyectos/{proyecto_id}/actividades")
def agregar_actividad_proyecto(
    proyecto_id: int,
    descripcion: str = Form(...),
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Crea una tarea pendiente dentro de un proyecto."""
    nueva_tarea = Actividad(descripcion=descripcion, proyecto_id=proyecto_id, estado="pendiente")
    db.add(nueva_tarea)
    db.commit()
    return RedirectResponse(url=f"/proyectos/ver/{proyecto_id}", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/actividades/{actividad_id}/actualizar")
def cambiar_estado_actividad(
    actividad_id: int,
    nuevo_estado: str = Form(...),
    db: Session = Depends(get_db),
    usuario_autenticado: str = Depends(obtener_usuario_actual)
):
    """Actualiza el estatus de una tarea (Pendiente/En Proceso/Completada) y vuelve al proyecto."""
    tarea = db.get(Actividad, actividad_id)
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    tarea.estado = nuevo_estado
    db.commit()
    return RedirectResponse(url=f"/proyectos/ver/{tarea.proyecto_id}", status_code=status.HTTP_303_SEE_OTHER)


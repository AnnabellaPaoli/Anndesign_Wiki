from sqlalchemy import ForeignKey
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "No encontré DATABASE_URL. Revisa que exista un archivo .env "
        "en esta misma carpeta con esa variable definida."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True)
    descripcion = Column(String(250), nullable=False)
    estado = Column(String(50), default="pendiente") # pendiente | en proceso | completada
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    
    proyecto = relationship("Proyecto", back_populates="actividades")


class Empresa(Base):
    """Una sola fila con la info de marca de AnnDesign."""
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False, default="AnnDesign")
    descripcion = Column(Text)
    colores = Column(JSON)          # ej: {"gold": "#B4903F", "ivory": "#FBF8F3"}
    tipografia = Column(String(120))
    instagram = Column(String(200))
    whatsapp = Column(String(50))
    email = Column(String(120))


class Proyecto(Base):
    """Cada cliente / proyecto que llevas."""
    __tablename__ = "proyectos"

    id = Column(Integer, primary_key=True)
    nombre_proyecto = Column(String(150), nullable=False)
    cliente = Column(String(150))
    estado = Column(String(50), default="en conversación")
    # valores sugeridos para 'estado':
    # "en conversación" | "en diseño" | "en desarrollo" | "entregado"
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    notas = Column(Text)
    link_publicado = Column(String(250))


class Contenido(Base):
    """Historial de piezas de Instagram generadas."""
    __tablename__ = "contenido"

    id = Column(Integer, primary_key=True)
    tipo_slide = Column(String(50))     # portada | servicio | proceso | faq | cierre
    texto_usado = Column(Text)
    fecha_generado = Column(DateTime, default=datetime.utcnow)
    ruta_archivo = Column(String(250))


class Usuario(Base):
    """Tu usuario para iniciar sesión en la wiki."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)


def create_tables():
    """Crea las 4 tablas en PostgreSQL si todavía no existen."""
    Base.metadata.create_all(engine)
    print("Tablas creadas (o ya existían): empresa, proyectos, contenido, usuarios")


if __name__ == "__main__":
    create_tables()
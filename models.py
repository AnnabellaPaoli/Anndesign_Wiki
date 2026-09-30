import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey
# CORRECCIÓN: Aseguramos importar relationship aquí
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("No encontré DATABASE_URL en el archivo .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Empresa(Base):
    __tablename__ = "empresa"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False, default="AnnDesign")
    descripcion = Column(Text)
    colores = Column(JSON)          
    tipografia = Column(String(120))
    instagram = Column(String(200))
    whatsapp = Column(String(50))
    email = Column(String(120))

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True)
    nombre_proyecto = Column(String(150), nullable=False)
    cliente = Column(String(150))
    estado = Column(String(50), default="en conversación")
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    notas = Column(Text)
    link_publicado = Column(String(250))
    
    # Relación para leer actividades fácilmente
    actividades = relationship("Actividad", back_populates="proyecto", cascade="all, delete-orphan")

class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True)
    descripcion = Column(String(250), nullable=False)
    estado = Column(String(50), default="pendiente") # pendiente | en proceso | completada
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    proyecto_id = Column(Integer, ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    
    proyecto = relationship("Proyecto", back_populates="actividades")

class Contenido(Base):
    __tablename__ = "contenido"
    id = Column(Integer, primary_key=True)
    tipo_slide = Column(String(50))     
    texto_usado = Column(Text)
    fecha_generado = Column(DateTime, default=datetime.utcnow)
    ruta_archivo = Column(String(250))

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)

def create_tables():
    Base.metadata.create_all(engine)
    print("Tablas sincronizadas con éxito (incluyendo actividades).")

if __name__ == "__main__":
    create_tables()

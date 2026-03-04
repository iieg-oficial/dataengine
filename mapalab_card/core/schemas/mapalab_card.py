from sqlalchemy import Column, Integer, String, Date, func
from sqlalchemy.orm import declarative_base

MAPALABCardBase = declarative_base()


class MapalabCard(MAPALABCardBase):
    """Modelo SQLAlchemy sincronizado con la migración 377c681a4c1c.

    Contiene las 47 columnas definidas en el upgrade de la migración inicial.
    """
    __tablename__ = 'mapalab_card'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tema = Column(String(1000), nullable=True)
    subtema = Column(String(1000), nullable=True)
    link_final_capa = Column(String(1000), nullable=True)
    capa_descargable = Column(String(1000), nullable=True)
    capa_finalizada_geoserver = Column(String(1000), nullable=True)
    nombre_capa_db = Column(String(1000), nullable=True)
    nombre_capa_usuario = Column(String(1000), nullable=True)
    nombre_capa_geoserver = Column(String(1000), nullable=True)
    descripcion = Column(String(1000), nullable=True)
    frecuencia_actualizacion = Column(String(1000), nullable=True)
    fecha_ultima_actualizacion = Column(Date, nullable=True)

    # Numeralia 01-08: valor, nombre, simbolo
    numeralia_01_valor = Column(String(1000), nullable=True)
    numeralia_01_nombre = Column(String(1000), nullable=True)
    numeralia_01_simbolo = Column(String(1000), nullable=True)
    numeralia_02_valor = Column(String(1000), nullable=True)
    numeralia_02_nombre = Column(String(1000), nullable=True)
    numeralia_02_simbolo = Column(String(1000), nullable=True)
    numeralia_03_valor = Column(String(1000), nullable=True)
    numeralia_03_nombre = Column(String(1000), nullable=True)
    numeralia_03_simbolo = Column(String(1000), nullable=True)
    numeralia_04_valor = Column(String(1000), nullable=True)
    numeralia_04_nombre = Column(String(1000), nullable=True)
    numeralia_04_simbolo = Column(String(1000), nullable=True)
    numeralia_05_valor = Column(String(1000), nullable=True)
    numeralia_05_nombre = Column(String(1000), nullable=True)
    numeralia_05_simbolo = Column(String(1000), nullable=True)
    numeralia_06_valor = Column(String(1000), nullable=True)
    numeralia_06_nombre = Column(String(1000), nullable=True)
    numeralia_06_simbolo = Column(String(1000), nullable=True)
    numeralia_07_valor = Column(String(1000), nullable=True)
    numeralia_07_nombre = Column(String(1000), nullable=True)
    numeralia_07_simbolo = Column(String(1000), nullable=True)
    numeralia_08_valor = Column(String(1000), nullable=True)
    numeralia_08_nombre = Column(String(1000), nullable=True)
    numeralia_08_simbolo = Column(String(1000), nullable=True)

    nombre_pie_numeralia = Column(String(1000), nullable=True)
    metodologia_texto = Column(String(1000), nullable=True)
    metodologia_archivo_enlace = Column(String(1000), nullable=True)
    fuentes_texto_largo = Column(String(1000), nullable=True)
    fuentes_texto_corto = Column(String(1000), nullable=True)
    fuentes_enlace = Column(String(1000), nullable=True)
    tipo_mapa = Column(String(1000), nullable=True)
    texto_leyenda_juridico = Column(String(2000), nullable=True)
    tipo_mapa_enlace = Column(String(1000), nullable=True)
    metadato_txt = Column(String(1000), nullable=True)
    metadato_xlsx = Column(String(1000), nullable=True)
    tarjeta_punto_poligono = Column(String(1000), nullable=True)
    created_at = Column(Date, server_default=func.current_date(), nullable=False)

    def __repr__(self) -> str:
        return f"<MapalabCard(id={self.id}, nombre_capa_db='{self.nombre_capa_db}')>"

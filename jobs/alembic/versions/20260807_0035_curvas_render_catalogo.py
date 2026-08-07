"""el catalogo apunta a la capa de render de curvas de nivel

La migracion `0026_curvas_de_nivel_render` materializa
`mapa_base.curvas_de_nivel_render` y su docstring dice que apunta
`mapalab.layers.geoserver_layer` a esa capa, pero **no ejecuta ningun UPDATE**:
el cambio se venia haciendo a mano en cada entorno. El espejo lo tenia; GCP no,
y ahi se detecto el 2026-08-07.

El costo de no tenerlo no es sutil. Con la capa original, cada tile que no esta
en cache renderiza sobre LineStrings completos —mediana de 133 vertices, pero 47
features pasan de 100 000 y la mayor llega a 910 621—, asi que el indice GiST los
selecciona en casi cualquier envelope. Medido en GCP sobre la misma peticion:

    general:curvas_de_nivel          42.51 s / 2.48 s
    general:curvas_de_nivel_render    0.68 s / 0.21 s

No aparece como error en ningun log: se manifiesta como saturacion de CPU del
nodo cuando alguien navega a una zona sin cachear.

`wfs_layer_name` queda en la tabla original para que las descargas sigan
entregando las curvas completas en 6368, que es el diseño que describe
`mapalab/docs/render-layers.md`.

Los dos UPDATE llevan condicion sobre el valor actual, asi que aplicarla en un
entorno ya corregido no cambia nada.

**Hay que borrar `mapalab.layer_tree_cache` o el cambio no llega al visor.** El
arbol del catalogo se sirve desde esa tabla y `get_cached_state()` **no la
compara contra `mapalab.layers`**: solo mira su `etag` y la reconstruye si la
fila no existe. Mover el `updated_at` de la capa no invalida nada —el
`source_max_updated_at` de la tabla es informativo, no un criterio—, asi que sin
el DELETE el visor sigue pidiendo la capa vieja indefinidamente.

Borrarla es seguro: es una cache materializada y se reconstruye sola en la
siguiente peticion. Cada worker guarda ademas una copia en memoria con TTL de
30 s, asi que el cambio tarda medio minuto en verse. Para que sea inmediato,
`POST /layers/refresh-cache` con el header `X-Internal-Token` la regenera y
avisa a todos los workers de una vez.

Revision ID: 0035_curvas_render_catalogo
Revises: 0034_matviews_spatial_index
Create Date: 2026-08-07
"""
from alembic import op


revision = "0035_curvas_render_catalogo"
down_revision = "0034_matviews_spatial_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE mapalab.layers
           SET geoserver_layer = 'curvas_de_nivel_render',
               updated_at = now()
         WHERE id = 'curvas_de_nivel'
           AND geoserver_layer = 'curvas_de_nivel'
           AND EXISTS (
             SELECT 1 FROM pg_class c
             JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'mapa_base' AND c.relname = 'curvas_de_nivel_render'
           );
        """
    )
    op.execute(
        """
        UPDATE mapalab.layers
           SET wfs_layer_name = 'curvas_de_nivel',
               updated_at = now()
         WHERE id = 'curvas_de_nivel'
           AND coalesce(wfs_layer_name, '') = '';
        """
    )
    op.execute("DELETE FROM mapalab.layer_tree_cache;")


def downgrade() -> None:
    op.execute(
        """
        UPDATE mapalab.layers
           SET geoserver_layer = 'curvas_de_nivel',
               wfs_layer_name = NULL,
               updated_at = now()
         WHERE id = 'curvas_de_nivel'
           AND geoserver_layer = 'curvas_de_nivel_render';
        """
    )
    op.execute("DELETE FROM mapalab.layer_tree_cache;")

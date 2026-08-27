# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El versionado
de `dataengine` es independiente del de MapaLab.

## [1.41.0] - 2026-08-27

### Agregado: el `/ontoy` declara a que nodo pertenece

huachicol 2.9.0 amplio el contrato para que el monitor agrupe por servidor y no solo por servicio.
`ONTOY_NODE` dice donde corre este repo —**S4**— y `ONTOY_NODE_REPORTER` decide quien habla del
host. Es el reportero de su nodo, asi que su `/ontoy` agrega carga, RAM, swap y uptime, leidos de `/proc` sin exporters ni puertos nuevos.

`ONTOY_PEER_CHECKS` queda disponible para las aristas entre nodos; vacia por omision.

**Las dos primeras son obligatorias**: el compose falla si faltan, asi que hay que agregarlas al
`.env` de cada entorno antes de desplegar.

De paso, `ontoy_server.py` se sincroniza con el de huachicol, que es la fuente y llevaba tiempo
divergiendo entre copias. Los checks de maquina quedan marcados como informativos y ya no tumban el
estado del servicio.

## [1.40.0] - 2026-08-24

### Corregido: 195 parcelas de cultivo de la ribera de Chapala sin municipio (migracion 0044)

La `0023` dejo `economia.cultivos` en 99.40 % con **2 068 parcelas en `NULL`**, anotadas entonces
como "borde y costa". Medidas ahora, son **dos cosas distintas** y solo una era un hueco:

| | Parcelas | Hectareas | Que son |
|---|---|---|---|
| Fuera del limite estatal | **1 873** (90.6 %) | 3 317.9 | La capa cubre terreno de estados vecinos. `NULL` es correcto |
| Dentro de Jalisco | **195** (9.4 %) | 615.6 | Hueco real del mosaico municipal |

Las 195 se concentran en cuatro municipios riberenos de Chapala —**183 de Jamay**, mas Jocotepec,
Tizapan el Alto y Tuxcueca—: tierra de cauce recuperado que ningun poligono municipal cubre. Estan
entre 9 m y 1 311 m del municipio mas cercano.

**El criterio es la pertenencia al estado, no una tolerancia en metros.** Un umbral fijo habria
rescatado parcelas de Zacatecas a 50 m de la frontera y dejado fuera las de Jamay a 1.3 km, que son
justo las que si son de Jalisco. Se asignan por vecino mas cercano con `<->`, acotando a las que
`mapa_base.limite_estatal` contiene.

Cobertura: **99.40 % -> 99.46 %**. Las 1 873 de fuera se quedan en `NULL` a proposito.

**Queda un pendiente que no es de esta migracion:** el mosaico de `mapa_base.limite_municipal`
tiene huecos dentro del estado en la ribera de Chapala. Lo correcto a mediano plazo es corregir el
limite, no parchar cada capa que caiga en el hueco.

### Agregado: declarar el campo de municipio en las capas (migracion 0043)

Las migraciones `0023`, `0040`, `0041` y `0042` dejaron el dato en la base, pero **ninguna declaraba
nada en `mapalab.layers`**. Sin `has_municipio`, `municipio_field` y `municipio_field_type` el visor
sigue recortando por `BBOX`, asi que el trabajo de las cuatro no se notaba. Esa configuracion se
edita desde mariachi, pero son mas de 180 capas: a mano no es reproducible entre entornos.

**No trae una lista de ids.** Recorre las capas vivas, resuelve su tabla via `mapalab.workspaces` y
elige el campo comprobando **los valores contra `mapalab.municipios`**, no el nombre de la columna.
Acepta una candidata solo si al menos el 90 % de sus valores distintos empata: por `clave_geo` las
de clave, por nombre normalizado las de nombre. Prefiere siempre la clave.

Esa comprobacion sale de dos casos reales que el nombre de columna habria dado por buenos:
`mapa_base.cabeceras_municipales` tenia un `clave_municipio` **sin prefijo de estado** —`01`, `02`—
que no empata con ninguna clave de cinco digitos, y en trece capas —aeropuertos, cuerpos de agua,
rutas de eventos— `nombre` es el nombre **del propio elemento**.

Validada contra las 203 capas resolubles del catalogo, comparando su eleccion con la que se hizo a
mano tras probar el CQL real por WFS: **203 coincidencias, 0 discrepancias**, incluidos los rechazos.

Idempotente: solo toca las capas que aun no declaran nada. Despues hay que recargar el catalogo de
GeoServer y correr `run_refresh_layer_tree.py`.

### Agregado: `clave_municipio` por coordenada en trece capas de puntos (migracion 0042)

Estaciones y paradas de transporte, estaciones MiBici, aeropuertos y los puntos de eventos no
tenian forma de identificar su municipio: el visor los recortaba con el `BBOX` de la seleccion y el
job del hexbin los contaba con `clave_municipio` nula.

A diferencia de la `0040` y la `0041`, estas tablas **no traen ningun codigo del que derivarla**,
asi que aqui si toca calcularla: spatial join punto-en-poligono contra `mapa_base.limite_municipal`
con `ST_PointOnSurface`, el mismo camino de la `0023` para `economia.cultivos`. Las trece tablas y
el limite estan en EPSG:6368, sin reproyeccion de por medio.

Un punto pertenece a un solo municipio, asi que **no hay nada que decidir**. Eso separa este caso
del de las capas lineales y poligonales, donde un 5-6 % de los features cruza mas de un municipio
—medido: 550 de 9 107 en `caminos_2012`, 962 de 19 756 en una muestra de `itur_iieg`, maximo tres
municipios en ambas— y hay que elegir entre duplicar la fila o quedarse con una. Esa decision sigue
abierta.

Son 699 filas entre las trece, todas resueltas. Aplicada y comprobada por WFS: `estaciones_mibici`
devuelve 368 de 384 al filtrar por Guadalajara y Zapopan.

**Con esto el desglose del hexbin queda completo**: 90 de 91 capas con cobertura total y **un solo
punto sin municipio** en 669 288 —una fila de `robos_negocio_con_violencia` con `municipio` nulo en
el origen—, contra los 6 223 del 2026-08-21.

### Agregado: columna `clave_geo` en `mapa_base.cabeceras_municipales` (migracion 0041)

La tabla ya traia `clave_municipio`, pero **sin el prefijo de estado**: `varchar(3)` con valores
`01`, `02`, `125`. El visor filtra con la clave INEGI de cinco digitos, asi que
`clave_municipio IN ('14039','14120')` no empataba con ninguna fila.

Se detecto al probar el CQL real contra cada tabla antes de declararla en el catalogo: **por
nombre de columna esta habria pasado como buena**, y la capa se habria vaciado al elegir municipio
en vez de mostrar de mas. El nombre `clave_geo` es el que usa el resto del ecosistema
—`mapalab.municipios.clave_geo`— y el que el plan `clave-municipio-en-tablas.md` ya daba por
existente aqui.

Columna generada, como en la `0040`: `'14' || lpad(clave_municipio, 3, '0')`. Verificado sobre las
125 filas, empata al 100 %, de `14001` a `14125`. Aplicada y comprobada por WFS.

**Va antes que la `0045` a proposito.** La `0045` reescribe 39 GB y necesita ventana; esta cuesta
125 filas. Encadenarlas al reves obligaba a esperar a la pesada para tener la barata.


### Agregado: migracion `0045_matviews_fid` — el identificador que faltaba para paginar

**El gate quedo cerrado.** El analisis del 2026-07-31 dejo abierto si GeoTools acepta un indice
unico sobre una vista materializada como clave, o si hacia falta `gt_pk_metadata`. Comprobado el
2026-08-24 publicando una matview de prueba con un unico indice sobre `fid`:
`GetFeature&startIndex=5&count=2` devolvio **200** y los ids `pk_probe.6` y `pk_probe.7`. La
heuristica sobre indices unicos basta; no hace falta `gt_pk_metadata`.

Como ninguna de las 83 matviews trae `fid` —lo que convierte a la `0039` en un no-op— y sus
columnas no forman llave natural, la migracion lo fabrica con `row_number() OVER ()`. Postgres no
permite agregar una columna a una matview, asi que cada una se reconstruye envolviendo su propia
definicion, se cambia por la original y se le devuelven indices y permisos, todo leido del
catalogo porque este repo no declara estas vistas.

**Dos trampas que costaron sendos bugs antes de quedar bien:**

- `information_schema` **no incluye vistas materializadas**. Leer de ahi los grants devuelve vacio
  y la reconstruccion se lleva en silencio el `SELECT` de `mariachi_layers`. Se leen de
  `pg_class.relacl` con `aclexplode`.
- Una matview **no admite `ALTER ... DROP COLUMN`**, asi que el `downgrade` no puede quitar `fid`
  a posteriori: reconstruye con la lista explicita de columnas.

**Sin aplicar. Va en ventana de mantenimiento: son 39 GB en 83 vistas**, no los ~1.25 GB que
estimaba el analisis original. Cada vista queda bloqueada mientras se reconstruye y alembic corre
todo en una transaccion. A favor: **cero dependencias entre matviews**, asi que no hay orden que
respetar. Conviene medirla primero sobre `delitos_fiscalia_robo_bancos`, la mas chica con 56 kB.

## [1.39.0] - 2026-08-21

### Agregado: `clave_municipio` en `espacios_publicos_y_lugares_recreativos` (migracion 0040)

Seis capas del visor salen de esa tabla —plaza, mercado, instalacion deportiva o recreativa,
centro comercial, instalacion gubernamental e instalacion de servicios— y ninguna se podia filtrar
por municipio. En `mapalab.hexbin_counts` se veia como **6 222 puntos con `clave_municipio` nula**:
todo el faltante del precalculado salvo una fila.

**No hizo falta spatial join: la clave ya estaba en el dato.** `cvegeo` es el geocodigo INEGI a
nivel manzana y sus primeros cinco digitos son la clave del municipio. Verificado sobre las 5 780
filas: `left(cvegeo, 5)` empata con `mapalab.municipios.clave_geo` en el **100 %**, sin nulos,
incluidas las seis filas de 13 caracteres.

Por eso la columna es `GENERATED ALWAYS AS (left(cvegeo, 5)) STORED` y no un backfill: se deriva
sola en cada alta y no puede quedar desalineada del `cvegeo` que la origina. Lleva indice btree.
Probado contra la base en una transaccion revertida: 5 780 filas con clave, **125 municipios**,
cero claves fuera del catalogo.

**Faltan dos pasos que no son SQL**: declarar `municipio_field='clave_municipio'` y
`municipio_field_type='clave'` en las seis capas desde mariachi, y correr `make refresh-layer-tree`.

### Cambiado: `run_refresh_hexbin.py` acepta un campo de clave, no solo de nombre

La columna de la `0040` no servia de nada para el precalculado. El job buscaba el municipio entre
`municipio`, `nombre_municipio` y `mun`, y resolvia **por nombre** contra `mapalab.municipios`:
`clave_municipio` no estaba en esa lista, y aunque se agregara, habria buscado `'14120'` en un
diccionario indexado por nombres. La migracion arreglaba el filtro del visor y dejaba los 6 222
NULL del hexbin intactos.

Ahora `_propiedades` detecta tambien un campo de clave —`clave_municipio` o `clave_geo`— y
`_clave_de` lo prefiere sobre el de nombre, validandolo contra las claves de `mapalab.municipios`
antes de aceptarlo. Si la clave falta, viene nula o no esta en el catalogo, cae al nombre como
siempre: las capas que hoy resuelven al 100 % no cambian de comportamiento.

Probado con los ocho casos: clave directa, clave sobre nombre, clave invalida, clave nula, solo
nombre, nombre en mayusculas, nombre nulo y sin campos.

Las otras ocho capas sin desglose municipal son las `auto-eventos-*` del schema `eventos`, que no
traen `cvegeo` ni campo de municipio. Suman ~442 puntos y si las necesitan requieren spatial join.

### Agregado: filtros compuestos y placeholders de contexto en las estadisticas

Una estadistica podia llevar **una** condicion, de igualdad exacta, contra un valor fijo
(`where_field` = `where_value`). Ahora lleva hasta seis, con `eq`, `in`, `gte`, `lte`, `between` e
`is_not_null`, y aplica a todas las primitivas, no solo a `count_where`:

```json
"filters": [
  {"field": "nivel_educativo", "op": "eq",      "value": "Primaria"},
  {"field": "municipio",       "op": "in",      "value": "{{municipio.nombres}}"},
  {"field": "fecha",           "op": "between", "value": ["{{fecha.inicio}}", "{{fecha.fin}}"]}
]
```

Un valor con forma `{{clave}}` no es literal: se resuelve al ejecutar contra una lista blanca de
cuatro claves (`municipio.claves`, `municipio.nombres`, `fecha.inicio`, `fecha.fin`) y **siempre
por bind param**, nunca interpolado. El SQL lo sigue armando el motor.

**La regla que sostiene el diseno:** si un placeholder no trae valor, el filtro **se omite**. El
cron corre sin contexto, asi que persiste el total sin filtrar como hasta ahora; la misma
configuracion sirve despues para la vista filtrada del visor, sin duplicarla por capa.

`where_field`/`where_value` siguen funcionando y se traducen a un filtro `eq` que conserva el
nombre del bind, asi que las configuraciones ya guardadas no cambian de SQL. Verificado contra
`educacion.centros_educativos`: los dos motores generan el mismo SQL y el mismo resultado en los
seis casos probados, y las seis capas con `stats_config` refrescan sin errores.

### Agregado: `scripts/stats_read_grants.sql`

Los GRANT de lectura que `mariachi_layers` necesita sobre los schemas tematicos —los que la
migracion `0031_stats_read_grants` concede— **no sobreviven a un restore**. Restaurar un dump sobre
una base ya migrada devuelve los privilegios al estado del dump sin tocar `alembic_version`, asi que
`alembic current` sigue reportando la revision aplicada mientras los permisos ya no estan.

El sintoma es asimetrico y despista: el cron de estadisticas corre como `gisuser` y calcula bien,
pero el preview y el recalculo del panel de mariachi corren como `mariachi_layers` y responden 502
`permission denied for schema`. Se detecto asi el 2026-08-21, con los grants caidos desde algun
restore anterior.

El script es el cuerpo `DO $$` de la migracion, extraido para reejecutarlo sin tocar
`alembic_version`. Es idempotente y deriva los schemas de `mapalab.workspaces`, de modo que sigue al
catalogo real de cada entorno. Se corre despues de cada restore:

```bash
docker exec dataengine-primary sh -c '
  PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
       -f /scripts/stats_read_grants.sql'
```

Termina imprimiendo una fila por workspace del catalogo: todas deben decir `t`.

### Corregido: `count_where` exigia una columna que no usaba

`_build_query` arma el `count_where` como `SELECT COUNT(*) … WHERE "<where_field>" = :valor` y nunca
toca `field`, pero la validacion lo pedia para toda operacion distinta de `count`. El mismo cambio
va en `mariachi/api/app/services/stats_templates.py`: el motor esta duplicado a proposito entre los
dos repos y una regla que solo cambie de un lado hace que el cron descarte lo que el CMS guarda.

De paso, `field` ahora se valida como identificador **cuando viene presente**, tambien en las
operaciones que no lo requieren. Antes un `field` con contenido arbitrario pasaba sin revisar si la
operacion no lo necesitaba; no era explotable —nunca llegaba al SQL— pero era una diferencia
gratuita con el motor de mariachi, que si lo validaba.

## [1.38.0] - 2026-08-21

### Agregado: `scripts/check-wfs-pagination.sh`

Recorre todas las capas del `GetCapabilities` de WFS y lanza a cada una un
`GetFeature&count=1&startIndex=0`, que es la prueba que separa a las que paginan de las que no.
Reporta capa por capa, agrupa las que fallan por workspace y sale con codigo 1 si hay alguna.
Formaliza una verificacion que se hacia a mano. Requiere `User-Agent` propio: el gateway bloquea
el de `curl` en `/sextante/ows`.

Medido contra el espejo el 2026-08-21: **46 de 121 capas paginan, 75 fallan** —
`seguridad_y_proteccion_ciudadana` 35, `desarrollo_social` 20, `demografia` 8,
`gobierno_y_ciudadania` 5, `economia` 5, `educacion` 1, `mapalab` 1. La ultima auditoria manual
(2026-07-31) contaba 73 en cinco workspaces: `educacion:centros_educativos` y
`mapalab:hexbin_agregado` se sumaron despues.

### Agregado: migracion `0039_matviews_unique_fid`, hoy un no-op

Crea `CREATE UNIQUE INDEX (fid)` en cada vista materializada que tenga columna `fid` y ningun
indice unico, para que GeoServer pueda paginarlas. Como la `0034`, descubre las vistas con un `DO`
block sobre `pg_class` y no con una lista fija, verifica que `fid` sea unico y no nulo antes de
cada indice —un `CREATE UNIQUE INDEX` sobre duplicados abortaria la transaccion entera— y reporta
creados y omitidos.

**No crea ningun indice hoy.** El analisis del 2026-07-31 asumia que las 82 matviews traian
columna `fid`. Verificado contra la base el 2026-08-21: **ninguna de las 83 la tiene**, ni ellas ni
sus tablas base. `fid` existe en 55 tablas normales, que son justo las que ya paginan. La
migracion queda como red por si la columna llega, pero **la paginacion sigue rota** y el arreglo
real es fabricar el identificador: recrear las matviews con `row_number() OVER () AS fid`, o
publicarlas como SQL view en GeoServer declarando el identificador.

Cuando haya columna y la migracion cree indices, dos cosas mas: **va en ventana de mantenimiento**
—Alembic corre en transaccion, asi que no puede usar `CONCURRENTLY` y cada indice toma
`ACCESS EXCLUSIVE` sobre su matview; la `0034` tardo 18 min 41 s sobre las 83— y **hay que
recargar el datastore en GeoServer**, que resuelve la clave al cargar el featuretype y la cachea.

## [1.37.0] - 2026-08-21

### Agregado: `make migrate` deja el catalogo listo, no solo migrado

Restaurar un dump viejo y migrarlo dejaba la caracteristica del hexbin **muerta en silencio**. La
migracion `0036_layer_geometry_type` crea la columna a proposito vacia —clasificar necesita hablar
con GeoServer, que no es trabajo de una migracion— y delega el relleno a
`run_backfill_geometry_type.py`. Si nadie lo corre, las 205 capas del catalogo quedan con
`geometry_type IS NULL`, `run_refresh_hexbin.py` no encuentra ninguna capa de puntos y **termina con
exit 0 diciendo «0 capas precalculadas»**. Para el orquestador eso es exito; para quien abre el
visor, la caracteristica no existe.

`migrate` ahora encadena los dos jobs despues del `alembic upgrade head`:

- **Geometrias** — `run_backfill_geometry_type.py` completo. Su `UPDATE` lleva
  `AND geometry_type IS DISTINCT FROM :tipo`, asi que no escribe si nada cambio. Medido: **2 s**
  para 209 capas.
- **Hexbin pendiente** — `run_refresh_hexbin.py --pendientes`.

### Agregado: `run_refresh_hexbin.py --pendientes`

Procesa solo las capas de puntos **sin filas en `hexbin_counts`**, para que el `migrate` no repita el
recalculo completo. Sin la bandera el comportamiento no cambia: el cron de las 04:15 sigue
reagregando todo.

Medido en el mismo catalogo: **2 min** la corrida completa (91 capas), **0.38 s** la de pendientes
cuando no hay nada nuevo.

El job ademas **avisa de las capas sin `geometry_type`** en vez de ignorarlas, que era la forma en que
el fallo pasaba desapercibido.

**Ojo:** «sin conteos» no es «pendiente». De 101 capas de puntos, 9 no producen ningun conteo (sin
features, o sin campo de fecha o municipio con que agregar) y 1 falla por WFS
(`salud:unidades_salud`, HTTP 400). Esas 10 se reintentan en cada `migrate` — barato, pero por eso el
guardia vive en el job y no en un `if` del Makefile: contarlas desde afuera daria «faltan 10» para
siempre y dispararia el recalculo completo en cada deploy.

## [1.36.0] - 2026-08-18

### Cambiado: el hexbin precalcula tambien las resoluciones 5 y 8

El visor traduce zoom a resolucion H3 con una tabla propia, y las cuatro que guardaba el job —3, 4,
6 y 7— **no cubrian el zoom inicial**: al abrir el mapa se pide la 5, que no existia, asi que la
capa caia al calculo en el navegador y ahi el tope de 20 000 la rechazaba. Los zooms 12 y 13, que
piden la 8, tenian el mismo problema.

Ahora precalcula **3, 4, 5, 6, 7 y 8**. El costo esta medido: los conteos pasan de 203 739 filas y
44 MB a **457 550 filas y 114 MB**, y las celdas compartidas de 6 297 a 16 716 (5 MB). De la 9 en
adelante —zoom 14 y mas cerca— sigue resolviendo el navegador.

## [1.35.0] - 2026-08-18

### Agregado: `mapalab.hexbin_agregado`, la vista que publica el hexbin en GeoServer

La 1.34.0 dejo los conteos H3 en dos tablas, pero GeoServer necesita **una** entidad con geometria
para publicar una capa. La vista hace el join entre `hexbin_counts` y `hexbin_cells` y expone las
columnas planas para filtrar con CQL:

    layer_key = 'violencia_familiar' AND resolution = 7
      AND anio IS NULL AND clave_municipio IS NULL

Es una vista de base y no una SQL view de GeoServer a proposito: asi la definicion vive versionada
en la migracion y GeoServer solo la registra. El `fid` existe porque el WFS necesita un
identificador estable por fila y la unicidad aqui es la tupla completa.

Publicada en el workspace `general` sobre un datastore nuevo `mapalab_hexbin` que apunta al schema
`mapalab`. Comprobado por WFS: devuelve el poligono de la celda, su indice H3 y el total.

## [1.34.0] - 2026-08-18

### Agregado: conteos H3 precalculados para el hexbin del visor

MapaLab agrupa puntos en hexagonos H3 desde su 1.129.0, pero lo hace en el navegador: hay que
traerse los puntos. Medido contra la capa peor, `delitos_fiscalia_violencia_familiar` con 110 215
puntos, eso son **50 MB de GeoJSON y 82 MB de heap**, y se paga en cada F5 porque el visor guarda
en `sessionStorage` el estado, nunca las geometrias. De ahi su tope de 20 000 elementos.

Dos tablas nuevas en `mapalab` y un job que las puebla a las **04:15**:

| Tabla | Contenido | Medido |
|---|---|---|
| `hexbin_cells` | `(resolution, h3_index) -> geom`, compartida por todo el catalogo | 6 297 filas, **1.9 MB** |
| `hexbin_counts` | `(layer_key, resolution, h3_index, anio, clave_municipio, total)` | 203 739 filas, **44 MB** |

Son dos y no una por algo que **solo H3 permite**: la celda `8a2a1072b59ffff` es la misma para
delitos y para escuelas, asi que su poligono se guarda una vez. Con una rejilla arbitraria habria
que repetirlo por capa.

El conteo va por **anio y municipio como columnas**, no resuelto por geometria: una celda de r7 mide
1.5 km de lado y las del borde contienen puntos de dos municipios. Como columna el conteo es exacto.
Cuesta poco: en r7 son 9 171 filas en vez de 2 169, no 2 169 x 10 anios x 125 municipios, porque
cada punto cae en un solo anio y un solo municipio.

Las resoluciones son **3, 4, 6 y 7** —estado y municipio—; de 8 hacia abajo lo sigue cubriendo el
calculo en el navegador, que ademas respeta cualquier filtro dinamico.

El indice lo calcula **Python con el paquete `h3`**, no la base: compilar `h3-pg` en la imagen
`postgis/postgis:18-3.6-alpine` obligaria a mantener una imagen propia de Postgres. Comprobado que
Python y JavaScript devuelven la misma celda para el mismo punto, que es lo que permite que el
precalculado y el calculo en cliente coincidan.

El job lee por **WFS**, no de las tablas: las capas publicadas no siempre son tablas. Las 11 de
delitos son la misma `seguridad_y_proteccion_ciudadana.delitos_fiscalia` con distinto filtro en
GeoServer, asi que leer de la base obligaria a replicar esos filtros. Pide solo la geometria, la
fecha y el municipio, y aplica el `cql_filter` del catalogo.

`layer_key` es el **id del nodo** del catalogo, no el typename: varios nodos comparten tabla con
distinto filtro y usar el typename hacia que se pisaran entre ellos.

`anio` y `clave_municipio` son nullable a proposito: hay capas de puntos sin fecha y sin municipio,
y la fila con los dos en NULL es el total de la celda sin desglosar.

No se toca ninguna tabla tematica y la bajada de la migracion es un `DROP`.

## [1.33.0] - 2026-08-10

### Agregado: `mapalab.layers.geometry_type`, el tipo de geometría del catálogo

El visor y el plugin de QGIS ya sabían dibujar el tipo de geometría de una capa, pero el dato no
existía en ninguna parte: cada cliente lo resolvía en caliente con un `DescribeFeatureType` por
capa —el visor al abrir el panel de capas activas, el plugin al pintar cada fila—. Con 115
`typeName` distintos entre las 209 hojas del catálogo, eso es una ráfaga de peticiones a GeoServer
por sesión, y basta que una falle para que el ícono no aparezca.

La columna guarda el dato una sola vez, con los valores que ya espera el frontend y sin traducción
intermedia: `point`, `line`, `polygon`, `raster`. Queda nullable porque los nodos que no son capa
no tienen geometría y porque hay capas de las que no se puede deducir.

`run_backfill_geometry_type.py` la puebla. El ráster se resuelve sin red —`raster_periodicity` o
workspace en `raster`/`lluvia`/`temperatura`, 4 capas— y el resto sale del `DescribeFeatureType`
del WFS, memorizado por `typeName` para no repetir la consulta de las capas que comparten tabla.
Se lee `localType` además de `type`, porque GeoServer marca como `gml:*` solo la geometría por
defecto y una segunda columna geométrica aparece como `xsd:MultiPolygon`.

Resultado de la primera corrida: 101 punto, 93 polígono, 10 línea, 4 ráster. Queda una sin
clasificar, `curvas_de_nivel`, que se publica solo por WMS —su `wfs_available` es `FALSE` y
GeoServer responde `Could not find type` al describirla—, así que no hay de dónde deducirla; se
ajusta a mano desde el editor de capas de mariachi.

El job queda registrado como `geometry-type` en `make refresh`, fuera de la lista por defecto:
habla con GeoServer y no tiene por qué correr en cada refresco rutinario. Necesita `GEOSERVER_URL`
en el `.env`.

`run_refresh_layer_tree.py` publica el campo como `geometryType` en el árbol. Sin eso, el cron de
las 4:00 reconstruiría la caché sin el dato y el ícono desaparecería del visor cada madrugada.

## [1.32.2] - 2026-08-10

### Corregido: el `/ontoy` del nodo no publicaba el check `containers`

`ontoy_server.py` implementa `_list_containers()`, pero el servicio `jobs` no montaba
`/var/run/docker.sock`, así que salía por `if not DOCKER_SOCKET_PATH.exists(): return [], None`
—sin excepción y sin log— y el check nunca aparecía en la respuesta. El monitor llevaba desde
siempre ciego a los cuatro contenedores del nodo, sin que nada se viera roto: el endpoint
respondía 200 con `disk` y ya.

Se agregan al `compose.yaml` las dos líneas que sextante, acervo y mapalab ya tenían: el bind del
socket en `:ro` y `ONTOY_COMPOSE_PROJECT: dataengine`, que es lo que filtra por proyecto — sin él,
en un monolito el sidecar lista los ~29 contenedores del host.

**Al desplegar:** `docker compose up -d --no-deps jobs`. El `--no-deps` no es opcional: sin él
compose puede recrear `dataengine-primary` y tumbar Postgres unos segundos.

## [1.32.1] - 2026-08-07

### Corregido: el catalogo no apuntaba a la capa de render de curvas (migracion 0035)

La `0026` materializa `mapa_base.curvas_de_nivel_render` y su docstring dice que apunta
`mapalab.layers.geoserver_layer` a esa capa, pero **no ejecuta ningun UPDATE**: el cambio se venia
haciendo a mano en cada entorno. El espejo lo tenia; GCP no, y ahi se detecto.

Quien decide que capa pide el visor es esa columna, no el codigo del frontend. Con la capa
original cada tile no cacheado renderiza sobre LineStrings completos —47 features pasan de 100 000
vertices y la mayor llega a 910 621—, asi que el indice GiST los selecciona en casi cualquier
envelope. Medido en GCP sobre el mismo tile:

| | Render (`MISS`) |
|---|---|
| `general:curvas_de_nivel` | **42.51 s** y 2.48 s |
| `general:curvas_de_nivel_render` | **0.51 s** y 0.19 s |

No aparece como error en ningun log: se manifiesta como saturacion de CPU del nodo cuando alguien
navega a una zona sin cachear.

`wfs_layer_name` queda en la tabla original, para que las descargas sigan entregando las curvas
completas en 6368.

**La migracion borra `mapalab.layer_tree_cache`**, o el cambio no llega al visor: el arbol del
catalogo se sirve desde ahi y **no se invalida solo** —`get_cached_state()` no lo compara contra
`mapalab.layers`, solo mira su `etag`—. Encima hay otra cache en memoria por worker con TTL de
30 s; para verlo al instante, `POST /layers/refresh-cache` con `X-Internal-Token`.

Los UPDATE llevan condicion sobre el valor actual: aplicarla en un entorno ya corregido no cambia
nada.

## [1.32.0] - 2026-08-06

### Corregido: 82 de 83 vistas materializadas sin indice espacial (migracion 0034)

Solo `mapalab.municipios` tenia indice GiST, y es la unica que se crea desde una migracion de
este repo; las tematicas se crean fuera y nadie se los puso. Cada una repite la geometria
completa del municipio en cada periodo, asi que pesan ~1.25 GB con ~17 000 filas, y **cada tile
hacia un Seq Scan de la vista entera**.

Medido sobre `seguridad_y_proteccion_ciudadana.personas_localizadas`, con la consulta real de un
tile de 256 px a z=11 (envelope espacial + `fecha`):

| | Plan | Buffers | Tiempo |
|---|---|---|---|
| Sin indice | Seq Scan | 63 961 | **5 436 ms** |
| Con indice | Bitmap Index Scan | 21 | **1.291 ms** |

End-to-end, una pantalla de 70 tiles en frio pasa de 48.5 s a 0.8 s.

La migracion recorre las matviews con un `DO` block en vez de una lista fija, porque las vistas
no las declara este repo: una tematica nueva queda cubierta con solo volver a aplicarla.
`REFRESH MATERIALIZED VIEW` reconstruye los indices, asi que no hay que recrearlos despues de
cada refresco. En el espejo tardo 18 min 41 s sobre las 83 vistas.

## [1.31.1] - 2026-07-31

### Agregado: `VERBOSE=1` en los targets que usan `run_step`

Sincronización de `make/lib.sh` y `make/common.mk` con gateway-hub 1.42.0. `run_step` esconde la
salida de cada paso y sólo la muestra —las últimas 40 líneas— si falla, así que un `docker build`
real y uno servido entero por caché se ven igual salvo por el cronómetro. Con `VERBOSE=1` la
salida se imprime en directo, indentada bajo el paso y conservando el `ok`/`fail` y el tiempo. El
comportamiento por defecto no cambia.

## [1.31.0] - 2026-07-31

### Cambiado: defaults de render a antialias en texto y tiles activados (migracion 0033)

La 0032 dejo los defaults reproduciendo el comportamiento anterior para que ninguna capa cambiara
de aspecto. Con los ajustes ya medidos, los defaults del sistema pasan a `antialias='text'` y
`tiled=true`: el suavizado solo en etiquetas baja el tile un 59 % conservando la transparencia, y
los tiles habilitan GeoWebCache.

Las capas existentes que estaban en `full` pasan a `text`. **`tiled` no se activa en masa**: una
capa con tiles y un `CQL_FILTER` no declarado en GWC pierde el metatiling y sus poligonos salen
cortados, asi que primero hay que declarar los filtros en `sextante/config/gwc-filters.txt`.

## [1.30.0] - 2026-07-31

### Agregado: `image_format` y `antialias` por capa (migracion 0032)

`mapalab.layers` gana dos columnas para controlar como se le pide cada capa a GeoServer.
Medido sobre un tile de 256x256 de `mapa_base.curvas_de_nivel_render`: PNG 21 465 B,
PNG 8 bits 12 114 B (-44 %), PNG sin antialias 8 698 B (-59 %) y ambos combinados 3 594 B
(-83 %). El ajuste optimo depende de la capa —una rampa continua sufre con paleta de 256
colores, una linea monocroma no— asi que se configura por capa desde la pestana Servicios de
mariachi.

Los defaults (`image/png`, `full`) reproducen el comportamiento anterior: **ninguna capa cambia
de aspecto al migrar**. Dos `CHECK` acotan los valores aceptados.

### Corregido: `run_refresh_layer_tree.py` habria dejado fuera las columnas nuevas

El job duplica el serializador del backend de mapalab (`_layer_to_dict`), asi que se actualizo
en el mismo commit: `_LAYER_COLS` y el bloque `wmsConfig`. Sin eso el cron nocturno habria
reescrito el arbol cacheado sin `format` ni `antialias`, y las capas configuradas habrian vuelto
al default sin aviso. Es el riesgo que documenta `ecosistema/contratos.md`.

## [1.29.0] - 2026-07-30

### Cambiado: Makefile homologado con el resto del ecosistema

La interfaz de comandos es ahora la misma en los nueve repos: `up` levanta desarrollo sin
reconstruir y `deploy` hace produccion completa (`git pull` + `down` + `build` + `up`). Se
retiraron todas las banderas: el entorno se detecta por el nombre de proyecto de Compose y lo que
antes era un argumento ahora es un selector interactivo. Lo transversal vive en `make/common.mk` y
`make/lib.sh`, copiados en cada repo. Convencion completa en `ecosistema/makefiles.md` del repo de
contexto.

Las reglas se partieron en `make/db.mk`, `make/migrate.mk` y `make/jobs.mk`, y el Makefile quedo
como indice.

### Eliminado: el cron que invocaba `make card`

`CRON_JOB` llamaba a `make card`, target borrado el 2026-04-22 junto con el ETL legacy del Google
Sheet. Como `up` y `restart` invocaban `cron-install`, **cada despliegue reinstalaba un cron que
fallaba todas las noches** con `No rule to make target 'card'`. El trabajo real ya lo hace
`jobs/crontab` dentro del contenedor. Se retiraron `CRON_JOB`, `cron-install` y `cron-remove`; hay
que desinstalar a mano el crontab que siga vivo en las VMs (`crontab -l | grep 'make card'`).

### Eliminado: `prod-migration` y el ETL del Google Sheet

El pull del Sheet que alimentaba `public.mapalab_card` dejo de tener sentido: la ingesta masiva
vive ahora en mariachi. Con el se van `scripts/prod-migration.sh`, el tag `legacy-etl-snapshot`,
la credencial de service account de Google y el `pip install` de pandas/gspread en runtime.

El bootstrap sigue disponible como **`make bootstrap`**, que invoca `scripts/bootstrap-v14.sh`:
crea el rol `mariachi_layers`, el schema `mapalab` con sus grants, siembra las capas del baseline
y aplica `alembic upgrade head`. Sigue siendo obligatorio en un entorno nuevo, porque la migracion
`0001_mapalab_init` da por hecho que el schema ya existe.

### Eliminado: `restore-local` y `version-json`

`restore-local` invocaba `restore/do-restore-local.sh`, que no existe en el repo ni existio nunca
en el historial de git. `version-json` y la carpeta `version-api/` se retiraron: el `/ontoy` lee la
version de `VERSION`, ya montado en el contenedor `jobs`.

### Cambiado: los refresh se fusionan en `refresh`

`refresh-all`, `refresh-layer-tree`, `refresh-layer-stats`, `refresh-municipios` y
`refresh-periodicity` pasan a un solo `refresh` con selector, que ademas expone
`cleanup-shares` y `dump-layers-csv`, que corren por cron pero no tenian target. Pedir
`layer-stats` explicitamente ahora usa `--force`: sin el, el TTL hacia que no hiciera nada y
pareciera un fallo. `refresh-municipios` sale del conjunto por defecto por ser un
`REFRESH MATERIALIZED VIEW CONCURRENTLY` mensual y pesado.

### Cambiado: `migrate-status` y `ps` se fusionan en `status`

Consultar el estado no puede tener efectos secundarios, y `migrate` reconstruye y recrea el
contenedor `jobs`. El reporte de alembic vive ahora en `make status`, junto al `ps`. `make shell`
pasa a ser la terminal generica del selector y la consola psql es `make psql`.

### Cambiado: `ingest-metadata` es interactivo

Ya no recibe `DEP=`, `SOURCE=` ni `EXTRA=`. Pregunta la dependencia y la fuente, corre el plan en
dry-run y pide confirmacion escribiendo `aplicar` antes de escribir en la base.

## [1.28.3] - 2026-07-30

### Corregido: `make migrate` dejaba `/ontoy` publicando la version anterior

El `/ontoy` de dataengine lo sirve `dataengine-jobs` leyendo `version-api/html/version.json`, que
es un **bind mount** y por tanto no viaja dentro de la imagen. El target `version-json` lo regenera
desde `VERSION`, y estaba declarado como dependencia de `up` y de `restart` — **pero no de
`migrate`**, que es justamente el que manda usar el procedimiento de despliegue.

Resultado: tras un `make migrate` la imagen quedaba al dia pero `/ontoy` seguia respondiendo la
version anterior **indefinidamente**, y el monitor reportaba dataengine como desactualizado sin que
nada estuviera roto.

Medido el 2026-07-30 en los tres entornos: la imagen `dataengine-jobs` reconstruida con
`/app/VERSION` en `1.28.1`, y `/ontoy` respondiendo `{"version": "1.27.0", ..., "deployed_at":
"2026-07-27T21:43:27Z"}` — el timestamp del despliegue anterior. Fallo **identico en Proxmox, GCP
y produccion**, asi que era del target y no del entorno.

#### Corregido

- `migrate` declara `version-json` como dependencia. Un despliegue con migraciones ya deja el
  `/ontoy` reportando la version correcta, sin paso manual.

---

## [1.28.2] - 2026-07-30

### La ayuda de `bootstrap-v14.sh` ya no menciona staging

Solo documentacion; sin cambios en el stack ni en las migraciones. El entorno staging se retiro
del ecosistema y este repo nunca tuvo uno: no habia archivos, ni targets, ni variables.

#### Cambiado

- El bloque de conectividad `mariachi-api ↔ DataEngine` que imprime `scripts/bootstrap-v14.sh`
  decia `dev / staging (mismo host, compose)`; ahora dice solo `dev`. El caso de produccion
  (servers separados) no cambia.

---

## [1.28.1] - 2026-07-29

### El contexto se movio al repo central

Solo documentacion; sin cambios en el stack ni en las migraciones.

#### Cambiado

- `docs/architecture.md` → `docs/arquitectura.md`, por la convencion de nombres del ecosistema
  (kebab-case y en espanol, igual que en mapalab y sieej).
- El README ya no fija la version en el texto: apunta al archivo `VERSION`. Decia **1.18.0**
  mientras el repo iba en 1.28.0, y fijar el numero garantiza que el drift vuelva en el proximo
  bump.

#### Eliminado

- `docs/context.md`, que vive ahora en `repos/dataengine/contexto.md` del repositorio central de
  contexto (`iieg-oficial/context-ame-esta`).
- `docs/bootstrap-v14.md`: era una migracion one-shot ya ejecutada — el propio documento advertia
  «no usar una vez mariachi reciba ediciones en prod». Quedo como registro en
  `historial/2026-04-dataengine-bootstrap-v14.md`, conservando lo repetible (como recuperar el
  password del rol).

## [1.28.0] - 2026-07-29

### Corregido: el refresco de numeralia borraba estadísticas y se caía en cascada

Tres fallas del job `run_refresh_layer_stats.py`, encontradas en una auditoría del flujo completo de estadísticas dinámicas.

**El job borraba los slots `static` y `formula`.** Solo conocía las 8 operaciones primitivas, así que una configuración guardada por mariachi con valores fijos o fórmulas caía en "config invalida, skip" y el `UPDATE` reescribía `values` completo sin ellos: la numeralia desaparecía del visor tras el cron. Ahora el job replica el motor de mariachi — `static`, `formula`, los seis combinadores (`add`, `sub`, `mul`, `div`, `percent`, `percent_change`), nodos `literal` y el tope de 6 niveles de anidamiento.

**Una query fallida tumbaba el resto del refresco.** Todas las capas corrían en una sola transacción; en Postgres, un error aborta la transacción completa y toda query posterior falla. Bastaba una configuración apuntando a una tabla eliminada para que las capas siguientes se reportaran como `failed` y el `COMMIT` final se convirtiera en un `ROLLBACK` silencioso: el log decía `updated=N` y **ninguna fila se había actualizado**. Ahora cada stat corre en su propio `SAVEPOINT` y cada capa en su propia transacción.

**Protección contra borrado**: si ninguna stat de una capa pudo calcularse, el job revierte y conserva los valores previos en vez de dejar la numeralia vacía.

### Agregado: `ttl_minutes` pasa a ser funcional

La columna existía desde `0003_layer_metadata_stats` pero no la consumía nadie: ni el visor, ni el job (que corría una vez al día para todas las filas por igual). Ahora el job filtra por TTL vencido (con 5 minutos de tolerancia para que un TTL de 24 h no se salte por segundos de deriva) y **el cron pasa de diario 04:30 a cada hora al minuto 30**. Una capa con TTL de 1 h se recalcula cada hora; una de 24 h, una vez al día. `--force` ignora el TTL y recalcula todo.

### Agregado: migración `0031_stats_read_grants`

El motor de estadísticas de mariachi corre como `mariachi_layers`, que solo tenía `SELECT` sobre las 16 tablas de `mapalab`. Los datos de las capas viven en los schemas temáticos, así que **toda estadística sobre datos reales fallaba** con `permission denied for schema demografia` — el preview y el recálculo del panel eran inservibles y solo el cron (que corre como `gisuser`) podía calcular algo.

La migración concede `USAGE` + `SELECT` sobre los schemas temáticos, derivándolos de `mapalab.workspaces` en vez de una lista fija, más `ALTER DEFAULT PRIVILEGES` para las tablas que se creen después. Solo lectura: el motor únicamente agrega (`count`/`sum`/`avg`/`min`/`max`/`latest`) sobre las mismas capas que el visor ya publica. Es idempotente, tolera que el rol no exista y el `downgrade` revoca.

### Cambiado: el formato de las estadísticas se aplica al guardar

El campo `format` se validaba pero ningún productor lo usaba, así que un `avg` llegaba al visor como `340172.1895424836601307`. Ahora se aplica al persistir: `integer`, `decimal_2`, `percentage`, `currency_mxn` y `compact`. Solo ajusta la precisión — el separador de miles lo sigue poniendo el visor y el símbolo va en su propio campo, así que la salida permanece parseable por `formatNumber`.

## [1.27.0] - 2026-07-23

### Agregado: columna `orden` en `mapalab.catalogo_capas` (reordenar capas manualmente)

Migración `0027_catalogo_capas_orden`. Agrega la columna `orden INTEGER NOT NULL DEFAULT 0` a `mapalab.catalogo_capas` para ordenar manualmente (drag & drop desde el admin de mariachi) las capas del catálogo y reflejar ese orden en el admin y en la vista pública `/catalogo`. Inicializa `orden` respetando el orden alfabético actual (por `nombre`) entre las filas vivas y crea el índice parcial `ix_catalogo_capas_orden` (sobre `deleted_at IS NULL`).

Cambio aditivo y reversible (`downgrade` elimina índice y columna; ninguna otra feature las usa). El backend de mariachi (api 1.74.0) ordena por `orden, nombre`, expone `PUT /catalogo/reorder` y asigna `orden = MAX(orden) + 1` a las capas nuevas y de alta masiva.

## [1.26.0] - 2026-07-23

### Agregado: tabla de render `mapa_base.curvas_de_nivel_render`

Migración `0026_curvas_de_nivel_render`. `mapa_base.curvas_de_nivel` guarda cada curva como un LineString completo: la mediana son 133 vértices, pero **47 features superan los 100 000** y la mayor llega a **910 621**. Esas geometrías cruzan medio estado, así que el índice GiST las selecciona en casi cualquier tile y GeoServer procesaba **13.2 millones de vértices por tile de 256 px, sin importar el zoom**.

La tabla nueva materializa las mismas geometrías con `ST_Subdivide(…, 512)` y ya reproyectadas a 3857 (que es lo que pide el visor, de paso elimina la reproyección on-the-fly). Medido:

| zoom | antes | después |
|---|---|---|
| z=11 | 624.8 ms/tile | **20.6 ms** |
| z=13 | 764.4 ms/tile | **7.3 ms** |
| z=15 | 1165.3 ms/tile | **5.0 ms** |

Consulta espacial: 164.7 ms → 0.49 ms. Salida visual idéntica (comparación píxel a píxel: solo difieren bordes de antialiasing sub-píxel, ninguna línea falta ni se parte).

- La tabla original **no se toca**: conserva las curvas completas en 6368 y sigue siendo la fuente para descargas.
- Paso manual posterior en GeoServer (documentado en la migración): publicar `general:curvas_de_nivel_render` con SRS nativo 3857 y el estilo `curvas_de_nivel`, apuntar `mapalab.layers.geoserver_layer` a esa capa y dejar `wfs_layer_name` en la original.
- Si se recargan las curvas hay que regenerar la tabla de render.

Mismo patrón que `0022_cultivos_geom_3857`. Contexto completo en `mapalab/docs/render_layers.md`.

## [1.25.0] - 2026-07-22

### Agregado: tabla `mapalab.catalogo_capas`

Migración `0025_catalogo_capas`: tabla para la sección "Catálogo" de Mapalab (capas por descarga directa, dadas de alta desde mariachi). Columnas: `workspace_alias` + `geoserver_layer`, `enabled` (visibilidad) + `deleted_at` (papelera), `search_tags`, timestamps y `updated_by`. Índice **único parcial** de `slug` (`WHERE deleted_at IS NULL`) e índice de `enabled` para el listado público. Aditiva; sin impacto en capas ni tablas existentes.

## [1.24.2] - 2026-07-16

### Fix (seguridad): publicar Postgres/pgbouncer solo en la interfaz interna

Endurece la exposición de la base de datos y limpia el compose. Sin cambios de esquema.

#### Cambiado

- **`docker-compose.yml`**: `postgres-primary`, `pgbouncer` y `version-api` se publican en `${PG_BIND_ADDRESS}` (obligatorio) en vez del default inline `0.0.0.0`, evitando exponer 5432/6432 en todas las interfaces del host. El `pg_hba.conf` sigue siendo la barrera real; esto reduce la superficie a nivel de bind. Los backups/restores no se ven afectados (usan la red interna de Docker, `host=postgres-primary`).
- **`docker-compose.yml`**: `pgbouncer` fijado a `edoburu/pgbouncer:v1.25.2-p0` (antes `latest`).
- **`docker-compose.yml`**: eliminados todos los defaults inline `${VAR:-valor}`; las variables vienen del `.env` (fail-fast si faltan).
- **`.env.example`**: `PG_BIND_ADDRESS` documentado como IP de interfaz interna (nunca `0.0.0.0`).

---

## [1.24.1] - 2026-07-07

### Tooling: `make migrate-status` con estado visual + guardia de entorno

Mejoras de DX en los targets de migración. Sin cambios de esquema ni de runtime del servicio.

#### Cambiado

- **`make migrate-status`**: salida compacta a color que resalta la revisión actual (`>`), las pendientes (`o`) y las aplicadas (`+`), con resumen "al día / N pendientes" (usa `alembic history --indicate-current`).
- **`make migrate`**: muestra el estado de migraciones antes y después de aplicar `alembic upgrade head`, además de ejecutarlo.
- **Guardia del contenedor `jobs`**: ambos targets verifican acceso vía `docker compose exec`; si el `.env` no está cargado (variables vacías → el compose no parsea) o `jobs` no corre, muestran el motivo real en vez de fallar en silencio.

---

## [1.24.0] - 2026-06-30

### Columna `mapalab.layers.tiled` — capas servidas por tiles, configurables desde mariachi

Permite marcar por capa si el visor la pide como `TileWMS` (cacheable en GeoWebCache) en vez de `ImageWMS`, reemplazando la lista local `TILED_LAYERS` del frontend por config editable desde mariachi.

#### Agregado

- **Migración `0024_layers_tiled`** (`jobs/alembic/versions/20260630_0024_layers_tiled.py`): agrega columna `tiled` (`boolean`, `DEFAULT false`) en `mapalab.layers`.
- **`run_refresh_layer_tree.py`**: incluye `tiled` en `_LAYER_COLS` y lo serializa en `wmsConfig.tiled` dentro de `_layer_to_wms_config`.

---

## [1.23.0] - 2026-06-30

### `economia.cultivos`: columna `clave_municipio` (filtro por municipio en mapalab)

mapalab filtra la "Vista por municipio" con un CQL sobre un campo de la capa, pero `economia.cultivos` no tenía forma de identificar el municipio. Se materializa vía spatial join.

#### Agregado

- **Migración `0023_cultivos_clave_municipio`** (`jobs/alembic/versions/20260630_0023_cultivos_clave_municipio.py`): agrega `clave_municipio varchar(5)` poblada con spatial join punto-en-polígono (`ST_Contains` + `ST_PointOnSurface`) contra `mapa_base.limite_municipal` (ambos en EPSG:6368) — clave INEGI de 5 dígitos. Crea índice btree en `clave_municipio` e índice GiST en `mapa_base.limite_municipal(geom)` (no existía y es necesario para que el join sea rápido). Cobertura 99.4% (las parcelas en borde/costa quedan NULL). Defensiva: se omite si la tabla no existe.

#### Notas

- La config de las 8 capas de cultivo (`has_municipio`, `municipio_field='clave_municipio'`, `municipio_field_type='clave'`) se setea en `mapalab.layers` (vía mariachi); tras cambiarla, correr `make refresh-layer-tree`.

---

## [1.22.1] - 2026-06-29

### `run_refresh_layer_tree.py`: serializar highlight, badge e icon_overrides

El cron de las 04:00 que reconstruye `mapalab.layer_tree_cache` es una reimplementación standalone del serializador del backend mapalab (`_layer_to_dict`) y se había desincronizado: su `SELECT` y su builder no emitían varios campos del nodo que el backend sí. Cada noche sobrescribía el caché con un árbol sin esos campos, así que la configuración hecha en el editor de Mariachi "desaparecía" del visor al día siguiente (detectado con capas marcadas "Sin resaltar" que seguían resaltándose).

#### Corregido

- **`jobs/run_refresh_layer_tree.py`**: se agregan al `_LAYER_COLS` y al nodo serializado `highlight_color`/`highlight_shape` (resaltado al hacer clic), `badge` (gated en `enabled`) e `icon_overrides` (iconos por estado en temas), igualando a `backend/app/services/layer_tree_service.py::_layer_to_dict`. Se replica además el resolver `_resolve_acervo_icon` para normalizar rutas de `iconUrl`/`iconOverrides`.
- Documentado en `docs/jobs.md` que este script duplica el serializador del backend y ambos deben mantenerse en sync.

---

## [1.22.0] - 2026-06-29

### Índice espacial de `economia.cultivos` como migración Alembic

GeoServer necesita lecturas WMS/WFS rápidas sobre `economia.cultivos` (consultas por bounding box). Hasta ahora el índice GiST + `CLUSTER` se reconstruía desde el repo `geoserver` con un script que corría `docker exec` contra `dataengine-primary` en cada arranque — patrón que asumía colocalidad de contenedores y por tanto no funcionaba en producción (PostGIS en servidor dedicado).

La optimización se reubica aquí, que es donde vive la tabla. La tabla casi nunca se actualiza, así que el índice se provisiona una sola vez vía migración versionada.

#### Agregado

- **`jobs/alembic/versions/20260629_0020_cultivos_spatial_index.py`**: crea el índice GiST `sidx_cultivos_geom` sobre `economia.cultivos(geom)` con `fillfactor=100` (tabla read-mostly: índice más compacto, mejor cache hit en lectura), aplica `CLUSTER` (localidad espacial en disco) y `ANALYZE`. La migración es defensiva: si la tabla aún no se cargó (`to_regclass` nula) se omite sin error, ya que `economia.cultivos` se carga por fuera del ETL.
- **`jobs/alembic/versions/20260629_0021_cultivos_drop_dup_index.py`**: elimina `sidx_cultivos_prueba_geom`, un segundo índice GiST sobre `geom` idéntico al anterior, heredado de cuando la tabla era `cultivos_prueba`. Dos índices iguales solo duplican espacio y costo de escritura; el planner usa uno solo.
- **`jobs/alembic/versions/20260629_0022_cultivos_geom_3857.py`**: materializa la columna `geom_3857` (`ST_Transform(geom, 3857)`) con su índice GiST `fillfactor=100`. mapalab renderiza en EPSG:3857 y su `ImageWMS` pide cada GetMap en 3857, mientras la geom nativa está en 6368: GeoServer reproyectaba on-the-fly en cada request. Publicar la capa sobre `geom_3857` elimina esa reproyección. La geom 6368 original se conserva. Requiere un paso manual posterior en GeoServer: re-publicar el featuretype apuntando `geom_3857` como geometría por defecto con SRS nativo 3857.

#### Notas

- `CLUSTER` toma `ACCESS EXCLUSIVE` sobre la tabla; la migración corre una sola vez, no en cada arranque. PostgreSQL no mantiene el orden de cluster tras escrituras: si algún día se recarga masivamente la tabla, re-ejecutar el `CLUSTER`/`ANALYZE` manualmente.

---

## [1.21.1] - 2026-06-19

### `pg-backup`: archivos de respaldo con dueño del host (no `root`)

El contenedor `pg-backup` corre como `root` (lo requieren `crond` y `pg_dump`), por lo que los `.sql.gz` escritos en el bind-mount `/backups` salían como `root:root` en el host. Eso complicaba copiarlos o moverlos a otros servidores sin `sudo`. Ahora el archivo se reasigna al UID/GID del usuario tras generarse.

#### Cambiado

- **`backup/scripts/backup.sh`**: tras el `chmod 600`, si `BACKUP_UID` y `BACKUP_GID` están definidos hace `chown ${BACKUP_UID}:${BACKUP_GID}` al archivo. El contenedor sigue corriendo como `root`, solo cambia el dueño del resultado.
- **`backup/do-backup.sh`**: el backup manual (`make backup`) pasa el UID/GID real de quien ejecuta la orden (`id -u`/`id -g`) al `docker compose exec`.
- **`docker-compose.yml`**: el servicio `pg-backup` recibe `BACKUP_UID` y `BACKUP_GID` desde el `.env` para que los backups del cron también queden con el dueño correcto.
- **`.env.example`**: documenta `BACKUP_UID=1000` y `BACKUP_GID=1000`.

#### Notas

- Para que el cron tome las nuevas variables hay que recrear el contenedor: `docker compose up -d pg-backup`.
- Los backups ya existentes siguen siendo `root`; normalizar con `chown ${BACKUP_UID}:${BACKUP_GID}` una vez si se requiere.

---

## [1.21.0] - 2026-06-08

### Agregado: columna `icon_overrides` para iconos por estado en temas

Permite que el admin de mariachi defina iconos distintos para cada estado visual de un tema del sider (normal / hover). El visor MapaLab usa esta columna para renderizar el icono correspondiente según si el sider está colapsado, expandido o tiene capas activas.

#### Agregado

- **Migración Alembic `0018_layer_icon_overrides`** (`jobs/alembic/versions/20260608_0018_layer_icon_overrides.py`): `ALTER TABLE mapalab.layers ADD COLUMN icon_overrides jsonb NULL`. Sin default — el admin define los overrides por estado.

#### Coordinación con otros repos

- **mariachi/api** (`1.33.0`): `LayerBase` y `LayerUpdate` en `schemas/layer.py` aceptan `icon_overrides` con validación `to_relative` por valor; `models/layer.py` mapea la columna.
- **mariachi/admin** (`1.33.0`): `TemaIconField` reescrito con segmentos normal/hover y preview por estado.
- **mapalab/backend** (`1.72.0`): `layer_tree_service.py` expone `iconOverrides` en el JSON del árbol con resolución a `/acervo/...`.
- **mapalab/frontend** (`1.74.0`): `MenuButton` usa `iconOverrides?.[iconState]` con fallback a `imageUrl` → `Icon`.

## [1.20.0] - 2026-05-26

### Agregado: columna `municipio_field_type` para metadata de filtro por municipio

Habilita el filtrado CQL por capa en el modo "Vista por municipio" del visor (`mapalab` 1.50.0). La metadata `mapalab.layers.has_municipio + municipio_field` ya existía pero faltaba distinguir si el valor del campo es una clave INEGI (5 dígitos, ej. `14039`) o un nombre (ej. `Guadalajara`). Sin este dato el frontend no sabe qué valores meter en la cláusula `IN`.

#### Agregado

- **Migración Alembic `0017_layer_municipio_field_type`** (`jobs/alembic/versions/20260526_0017_layer_municipio_field_type.py`): `ALTER TABLE mapalab.layers ADD COLUMN municipio_field_type varchar(20) NULL`. Valores esperados: `clave` | `nombre` | NULL. Sin default — el admin elige según el contenido real de la columna referenciada por `municipio_field`.

#### Coordinación con otros repos

- **mapalab/backend** (`1.30.0`): `_layer_to_search_meta` ya expone `searchMeta.municipioFieldType` en el JSON del árbol. También agrega `_inherit_municipio_meta` que propaga la metadata desde un `group` hacia sus descendientes (un admin configura una vez en el group y aplica a todas las propiedades hijas).
- **mariachi/api** (`1.19.0`): `LayerBase` y `LayerUpdate` en `schemas/layer.py` aceptan `municipio_field_type`; `models/layer.py` mapea la columna.
- **mariachi/admin** (`1.19.0`): nuevo componente `MunicipioFieldPicker` con dropdown de columnas de la tabla (vía `/geoserver/workspaces/{alias}/layers/{layer}/fields?include_samples=true`) y auto-detección de tipo según muestras.

---

## [1.19.0] - 2026-05-26

### Agregado: job `run_dump_layers_csv.py` (cache de descargas en Acervo)

Para descargar la presión del backend de MapaLab en producción al servir CSVs de capas (saturaba el bucket superior del histograma `http_request_duration_seconds` con valores >10s, mide hasta el cierre del response), se pre-generan los CSVs nocturnamente y se suben a Acervo. El backend redirige (`307`) a la URL pública de Acervo cuando hay un dump fresco; si no, cae a streaming on-the-fly (cambio independiente en `mapalab/backend` con asyncpg).

En GCP staging el job es opcional: si `AO_BUCKET_MAPALAB` no está seteada, hace skip con `return 0` y todas las descargas siguen al vuelo (el almacenamiento en GCP es limitado y los recursos son temporales).

#### Agregado

- **Migración Alembic `0016_layer_downloads`** (`jobs/alembic/versions/20260526_0016_layer_downloads.py`): nueva tabla `mapalab.layer_downloads(layer_key TEXT PK, db_schema, db_table, object_key, size_bytes BIGINT, row_count BIGINT, generated_at TIMESTAMPTZ)` con índice por `generated_at DESC`.
- **Job `jobs/run_dump_layers_csv.py`**: itera capas con `downloadable=true` y `layer_name_db` resuelto en `mapalab.layer_metadata`; para cada una hace `COPY (SELECT * FROM schema.table) TO STDOUT WITH CSV HEADER`, comprime on-the-fly con `gzip` (level 6) a `tempfile.NamedTemporaryFile`, sube a `s3://${MAPALAB_AO_BUCKET}/downloads/{schema}/{table}.csv.gz` con `ContentType=text/csv` y `ContentEncoding=gzip` vía `s3.upload_fileobj` (multipart automático), y upserta el registro en `mapalab.layer_downloads`. Skip si el blob comprimido pesa >2 GB. El uso de tempfile en disco (no `BytesIO` en RAM) permite procesar tablas grandes — verificado en local con tablas que comprimen a >1 GB (e.g. `economia.trabajadores_asegurados` con 17 000 filas pesa ~1 GB en gzip por incluir geometrías cruzadas).
- **`jobs/crontab`**: nueva entry diaria a las 05:00 UTC (`0 5 * * *`). El refresh de municipios se mueve a las 06:00 UTC (sigue siendo mensual el día 1) para no colisionar.
- **`jobs/requirements.txt`**: `boto3==1.35.49`.
- **`jobs/entrypoint.sh`**: el `printenv` que escribe `/etc/environment` para cron ahora incluye también las variables `AO_*` y `MAPALAB_AO_*` (antes solo `DATAENGINE_*`). Sin este cambio cron no vería las credenciales y el job fallaría con "Acervo/mapalab no configurado".
- **`docker-compose.yml`**: el servicio `jobs` ahora recibe `AO_ENDPOINT`, `MAPALAB_AO_BUCKET`, `MAPALAB_AO_ACCESS_KEY`, `MAPALAB_AO_SECRET_KEY` (credenciales del usuario `mapalab-user` de Acervo, separadas de las `AO_*` que usa `pg-backup` para subir backups al bucket `dataengine`). En local agrego `extra_hosts: host.docker.internal:host-gateway` al servicio `jobs` para que pueda alcanzar `acervo-seaweedfs:8333` cuando `AO_ENDPOINT=http://host.docker.internal:8333` (single-VM con todos los compose separados). En producción `AO_ENDPOINT` es URL pública con DNS resoluble, así que no necesita este hack.
- **`.env.example`**: documenta `MAPALAB_AO_BUCKET=mapalab`, `MAPALAB_AO_ACCESS_KEY`, `MAPALAB_AO_SECRET_KEY` como nuevas variables.

#### Por qué minor

Nueva tabla en schema `mapalab`, nuevo job en el cron, nueva dependencia (`boto3`) y nuevas env vars opcionales. Compatible hacia atrás: el endpoint de MapaLab funciona idéntico aunque la tabla esté vacía (cae a streaming on-the-fly).

---

## [1.18.0] - 2026-05-22

### `mapalab.bulk_ingest_plans`: persistencia de planes para ingesta masiva

Para soportar la nueva feature de **ingesta masiva de metadatos** en mariachi (subir CSV/XLSX → previsualizar plan con diff por capa → aplicar), se agrega una tabla que guarda el plan generado entre el `preview` y el `apply`.

#### Agregado

- **Migracion Alembic `0012_bulk_ingest_plans`** (`jobs/alembic/versions/20260521_0012_bulk_ingest_plans.py`): nueva tabla `mapalab.bulk_ingest_plans` con:
  - `id UUID PRIMARY KEY` — generado app-side (mariachi).
  - `created_at TIMESTAMPTZ`, `created_by VARCHAR(255)` — audit del usuario que subio el archivo.
  - `dependencia VARCHAR(100)`, `source_filename VARCHAR(500)`, `source_object_key VARCHAR(500)` — origen del archivo (este ultimo apunta al bucket privado `mariachi` en Acervo).
  - `status VARCHAR(20) CHECK ('pending','applied','cancelled','expired')`.
  - `plan_json JSONB`, `column_mapping JSONB` — plan completo + mapeo de columnas usado (audit).
  - `applied_at`, `applied_by`, `expires_at TIMESTAMPTZ` — TTL de 24h.
  - Indices parciales `ix_bulk_ingest_plans_pending (created_by, created_at DESC) WHERE status='pending'` y `ix_bulk_ingest_plans_expiry (expires_at) WHERE status='pending'`.

La logica de `build_plan` (diff vs DB), `apply_plan` (optimistic locking con `IS NOT DISTINCT FROM`) y el parser CSV/XLSX viven en mariachi (`api/app/services/bulk_ingest_*.py`). Esta tabla es solo el storage del plan.

#### Operacional

- Aplicar en dev/staging/prod: `make migrate` (o `docker compose exec jobs alembic upgrade head`).
- Sin downtime: tabla nueva, sin alterar tablas existentes.

## [1.17.0] - 2026-05-20

### `mapalab.layers`: soft delete con `deleted_at` / `deleted_by`

Para que MapaLab pueda archivar capas de forma reversible (con papelera y restore) en lugar de hard-delete, se agregan dos columnas y se filtran las archivadas del cache materializado del árbol.

#### Agregado

- **Migracion Alembic `0011_layer_deleted_at`**: agrega columnas `deleted_at TIMESTAMPTZ NULL` y `deleted_by VARCHAR(100) NULL` a `mapalab.layers`. Indices parciales `ix_layers_alive WHERE deleted_at IS NULL` (para queries del visor) y `ix_layers_deleted WHERE deleted_at IS NOT NULL` (para listar la papelera). Downgrade incluido.

#### Cambiado

- **`jobs/run_refresh_layer_tree.py`**: `_fetch_layers` y `_max_updated_at` filtran `deleted_at IS NULL`. El cron diario `run_refresh_layer_tree` y el refresh manual via `make refresh-layer-tree` ya no incluyen capas archivadas en `mapalab.layer_tree_cache`. Las capas archivadas desaparecen del visor en cuanto el cache se reconstruye.

### `mapalab.symbols`: columna `bucket_slug` y SVG como archivo

Para que mariachi pueda almacenar simbolos SVG como archivos (subidos al
bucket `iieg` bajo el prefijo `leyendas/`) en lugar de XML inline en la
columna `value`, el schema `mapalab.symbols` necesita declarar en que
bucket de Acervo vive cada simbolo.

#### Agregado

- **Migracion Alembic `0010_symbol_bucket_slug`**
  (`jobs/alembic/versions/20260520_0010_symbol_bucket_slug.py`): agrega
  columna `bucket_slug VARCHAR(50) NOT NULL DEFAULT 'mapalab'` a
  `mapalab.symbols`. Las filas existentes (emojis e imagenes en
  `mapalab/simbologia/`) heredan el default. Los simbolos nuevos
  `kind='svg'` se crean con `bucket_slug='iieg'` y `image_object_key`
  bajo `leyendas/`.

#### Limpieza

- La misma migracion borra entradas legacy con `kind='svg'` y
  `image_object_key IS NULL` (modalidad inline XML que `_apply_sld`
  rechazaba y el SymbolPicker de mariachi deshabilitaba). Idempotente:
  si no hay entradas asi, no toca nada.

## [1.16.0] - 2026-05-20

### Soporte para `notice` (mensaje configurable por capa)

Para que MapaLab v1.29.0 pueda mostrar avisos contextuales sobre cada capa
(anclados a punto del mapa o flotantes en pantalla, con variante banner,
tamaños configurables, etc.), el schema y el builder del árbol incorporan
un nuevo campo JSONB por capa.

#### Agregado

- **Migración Alembic `0009_layer_notice`** (`jobs/alembic/versions/20260519_0009_layer_notice.py`):
  agrega columna `notice JSONB NULL` a `mapalab.layers`. Idempotente,
  reversible (`downgrade` con `drop_column`). Entra automáticamente vía
  `make prod-migration` (que ya corre `alembic upgrade head`).
- **`run_refresh_layer_tree.py`**: el builder del `mapalab.layer_tree_cache`
  ahora incluye `notice` en `_LAYER_COLS` y lo emite en cada nodo del JSON
  cuando `notice.enabled === true`. Si el aviso está apagado se omite
  silenciosamente para no inflar el payload del árbol.

#### Shape del JSONB

```json
{
  "enabled": true,
  "title": "Datos preliminares",
  "description": "...",
  "icon": "/acervo/iieg/iconos/foo.svg",
  "variant": "info|warning|neutral|banner",
  "size": "small|medium|large",
  "position": "top-center|bottom-center",
  "dismissible": true,
  "dismissPersistence": "permanent|reopen",
  "anchorMode": "viewport|coord",
  "anchorCoord": { "lon": ..., "lat": ... },
  "arrowPosition": "top|right|bottom|left",
  "zoomRange": { "min": ..., "max": ... },
  "validFrom": null,
  "validUntil": null,
  "cta": { "label": "...", "url": "..." }
}
```

Validación del shape vive en `mariachi >= 1.2.0` (Pydantic `LayerNotice`);
`dataengine` lo almacena como JSONB sin validar para preservar el principio
de single source of truth en mariachi.

## [1.15.0] - 2026-05-18

### Ingesta masiva de metadatos a `mapalab.layer_metadata` desde CSV

Nuevo flujo `make ingest-metadata` para que los metadatos de capas vengan de
archivos CSV proporcionados por dependencias externas (instituciones que
mandan sus propias capas). Reemplaza la edicion manual via mariachi-admin
para cargas grandes y permite revision granular antes de aplicar.

El flujo es: **plan -> review -> apply**. El planner compara cada fila del
CSV contra `mapalab.layer_metadata` y arma un diff por columna; el applier
ejecuta los upserts aprobados con _optimistic locking_ (`UPDATE ... WHERE
col IS NOT DISTINCT FROM :expected_from`), de modo que ediciones hechas
desde mariachi entre el `plan` y el `apply` se detectan como `conflict` y
se saltean sin pisar.

Semantica de upsert: **merge non-null** (celdas vacias en el CSV no borran
datos existentes). Cada fila tocada queda con `updated_by = 'ingest:<dep>:<archivo>'`.

### Agregado

- **`jobs/ingest/`** (paquete nuevo, aislado de `bootstrap/` y `alembic/`):
  - `reader.py`: lee CSV desde archivo local o URL HTTP (`utf-8-sig`).
  - `columns.py`: header esperado (20 columnas planas, JSONB anidados via
    sufijos: `fuentes_corto/largo/enlace`, `metodologia_texto/archivo_enlace`,
    `metadato_txt/xlsx`), validacion de columnas desconocidas, coerciones
    (`parse_bool`, `clean`, builders de JSONB).
  - `planner.py`: `build_plan(conn, dependencia, source, rows)` calcula
    insertos/updates/duplicados y devuelve plan JSON serializable. Cada
    `update` lleva `diffs` por columna con `from`/`to`/`apply`.
  - `applier.py`: `apply_plan(conn, plan)` ejecuta los cambios aprobados
    con optimistic locking; reporta `inserts_applied`, `inserts_conflict`,
    `updates_applied`, `updates_columns_changed`, `updates_conflict`,
    `changes_skipped`.
  - `run_ingest_metadata.py`: CLI con flags `--dependencia`, `--source`,
    `--plan-out`, `--plan-in`, `--review`, `--apply`. Modos: dry-run,
    plan-editable, review interactivo TTY, apply directo.
- **`make ingest-metadata DEP=<dep> SOURCE=<path|url> [EXTRA=...]`**: target
  wrapper. Si `SOURCE` es path local, hace `docker cp` al container antes
  de invocar el script. Sin `--apply` corre dry-run.

### Cambiado

- **`jobs/bootstrap/v14_schema.sql:129`**: `mapalab.alembic_version_dataengine.version_num`
  se crea como `VARCHAR(255)` (antes `VARCHAR(32)`). Default historico de
  alembic se quedo corto cuando los revision ids descriptivos pasaron 32
  chars (ej. `0008_symbol_catalog_excluir_baneados` = 36).
- **`Makefile` target `migrate`** y **`scripts/prod-migration.sh`**: ahora
  hacen `docker compose build jobs && up -d jobs` antes del `alembic upgrade
  head`, evitando que migraciones nuevas queden silenciosamente ignoradas
  por una imagen del container desactualizada respecto al repo.

### Arreglado

- **Crash de `make prod-migration` en `alembic upgrade head`** con
  `psycopg2.errors.StringDataRightTruncation: value too long for type
  character varying(32)` al intentar stampear `0008_symbol_catalog_excluir_baneados`
  en la tabla de bookkeeping. El UPDATE del version_num al final de la
  migracion crasheaba, revertia la transaccion y dejaba la DB en 0007.
  - Fix en runtime: hook idempotente `_ensure_version_num_capacity` en
    `jobs/alembic/env.py` que ejecuta `ALTER COLUMN ... TYPE VARCHAR(255)`
    si detecta una tabla preexistente con limite menor. Protege ambientes
    bootstrapped con la DDL vieja.
  - Fix en bootstrap fresco: DDL en `v14_schema.sql` actualizada (ver
    seccion Cambiado).

---

## [1.14.3] - 2026-05-14

### `restore.sh`: recrear base destino antes de `pg_restore`

`pg_restore --clean` hacia DROP plano (sin CASCADE) y fallaba cuando la extension postgis o los schemas del dump tenian objetos dependientes de un restore previo (e.g. tras correr `make restore` dos veces seguidas). El script ahora ejecuta `DROP DATABASE IF EXISTS` + `CREATE DATABASE` antes del `pg_restore`, garantizando un punto de partida limpio.

#### Cambiado

- **`scripts/restore.sh`**: bloque previo al `pg_restore` recrea la base destino. Las creds y el host se siguen tomando de `.env` / variables del container.

#### Notas

- El commit (`5d149dc`) ya estaba en `production`; esta entry se agrega retroactivamente para que `make up` deje de emitir el WARN `no se encontro entrada '## [1.14.3]'`.

---

## [1.14.2] - 2026-05-14

### Renombrado del repositorio `mapalab-dataengine` → `dataengine`

El repositorio se renombro a `dataengine`. Se actualizaron las referencias internas (rutas, `README.md`, scripts de bootstrap y docs de jobs) y el remote de git apunta ahora a `git@github.com:iieg-oficial/dataengine.git`.

### Cambiado

- `README.md`, `docs/jobs.md`, `jobs/README.md`, `jobs/bootstrap/v14_schema.sql`, `scripts/bootstrap-v14.sh`: referencias `mapalab-dataengine` → `dataengine`.

## [1.14.1] - 2026-05-13

### Migracion `0008_symbol_catalog_excluir_baneados`: excluir emojis baneados del catalogo

Limpieza del catalogo sembrado en `1.14.0` para excluir tres emojis no deseados (🖕, 💩, 💣). El catalogo se restablece correctamente al borrar volumenes y correr `alembic upgrade head`.

### Cambiado

- `jobs/alembic/versions/20260512_0007_symbol_catalog.py`: removido 🖕 del seed inline de la categoria `gestos`. En despliegues con volumenes recien creados ya no se inserta. 💩 y 💣 nunca estuvieron en el seed.

### Agregado

- `jobs/alembic/versions/20260513_0008_symbol_catalog_excluir_baneados.py`: migracion idempotente que ejecuta `DELETE FROM mapalab.symbols WHERE kind = 'emoji' AND value = ANY(:values)` con la lista `('🖕','💩','💣')`. Sirve para ambientes donde la `0007` ya se aplico con la lista vieja; en ambientes nuevos pasa sin tocar filas. `downgrade` es no-op (la lista de baneados no se restaura).

---

## [1.14.0] - 2026-05-13

### Migracion `0007_symbol_catalog`: catalogo de simbolos para MapaLab

Soporte de schema para el nuevo catalogo de simbolos administrable desde mariachi-admin, consumido por el panel de mediciones de MapaLab y el shape `point` del SLD editor.

### Agregado

- Tabla `mapalab.symbol_categories` — `(id, slug UNIQUE, name, icon, sort_order, created_at, updated_at)`.
- Tabla `mapalab.symbols` — `(id, category_id FK CASCADE, kind CHECK('emoji'|'svg'|'image'), value TEXT, name, sort_order, image_object_key, png_object_key, created_at, updated_at)`. Index compuesto `(category_id, sort_order)`.
- Seed inline en la migracion: 8 categorias (Caras, Gestos, Animales, Comida, Viajes, Objetos, Simbolos, Actividades) y ~980 emojis tomados de `mapalab/frontend/src/pages/maps/helpers/emojiCatalog.js`. Asi el primer despliegue tiene catalogo poblado sin pasos manuales.

### Notas

- La migracion se aplica automaticamente via `make prod-migration` (paso 5: `alembic upgrade head`). No requiere cambios en `prod-migration.sh` ni en `bootstrap-v14.sh`.
- `mapalab/frontend` deja de usar `emojiCatalog.js` y consume el endpoint publico de mariachi `GET /api/mapalab/symbols/catalog`. El admin de mariachi opera contra estas tablas via `dataengine_db`.

---

## [1.13.0] - 2026-05-07

Mientras el primer deploy a produccion no se haya completado, el Sheet de Google sigue siendo la fuente de verdad para `mapalab.layer_metadata`. Por eso `make prod-migration` vuelve a hacer pull del Sheet por default; el `--skip-etl` queda como opt-in para cuando se cierre el ciclo de testing y el Sheet se congele.

### Cambiado

- `scripts/prod-migration.sh`: `SKIP_ETL` default pasa de `1` a `0` (pull del Sheet activo por default). `--with-etl` deja de ser necesario; `--skip-etl` queda como opt-in.
- `Makefile`: ayuda de `prod-migration` actualizada — default `with-etl`, override con `PROD_MIGRATION_FLAGS="--skip-etl"`.
- Comentario de cabecera del script aclarado: revertir el default a `SKIP_ETL=1` tras el primer go-live a produccion.

---

## [1.12.2] - 2026-05-06

Refuerzo del rename agregado en 1.12.1: el migrador ahora también limpia las filas viejas con `layer_key` en formato pre-rename antes de hacer el upsert. Sin esto, al correr `prod-migration` en un ambiente que ya tenía filas con `mundial:*`, las nuevas filas con `eventos:*` se insertaban por separado (PK distinta) y quedaban duplicadas.

### Cambiado

- `run_migrate_mapalab_card.py::main` hace `DELETE` previo en `mapalab.layer_stats` y `mapalab.layer_metadata` para cada `WORKSPACE_RENAMES` y `LAYER_RENAMES` configurado, en orden seguro respecto a la FK `layer_stats_layer_key_fkey`.
- Idempotente: en ambientes limpios (sin filas viejas) los DELETE devuelven 0 rows y no afecta nada.

---

## [1.12.1] - 2026-05-06

`run_migrate_mapalab_card.py` (paso 5 del bootstrap v1.4.0) ahora normaliza el `layer_key` cuando el Sheet de Google usó un nombre de workspace distinto al que GeoServer/`mapalab.workspaces` tienen registrado.

### Cambiado

- **Mapeo de renames in-flight** en `jobs/bootstrap/run_migrate_mapalab_card.py`:
  - Workspace: `mundial` → `eventos` (todas las capas del mundial vivían bajo este alias en el Sheet, pero el workspace real en GeoServer es `eventos`).
  - Layer especifico: `mundial:sitios_interes` → `eventos:sitios_interes_direcciones` (nombre de la capa en GeoServer agrega sufijo `_direcciones`).
- Constantes `WORKSPACE_RENAMES` y `LAYER_RENAMES` + helper `normalize_layer_key`. Idempotente: si el `layer_key` ya viene en formato correcto pasa sin cambios.

### Por qué

Sin esto, `mapalab.layer_metadata` y `mapalab.layer_stats` quedaban con `layer_key = mundial:*`, pero los editores (mariachi, visor) buscan por `${workspaceAlias}:${geoserverLayer}` = `eventos:*`. Resultado: 11 metadatas "huérfanas" y los editores mostraban formularios vacíos para capas que sí tenían datos.

### Notas operativas

- Sin cambios en migración Alembic ni schema.
- `--with-etl` o `--skip-etl` ambos aplican el rename al final (el migrador siempre corre).
- Si el equipo del Sheet alguna vez corrige `mundial:` → `eventos:` en la fuente, los renames quedan no-ops (el `layer_key` ya viene correcto).
- Para renames adicionales en el futuro (otros workspaces mal nombrados desde el Sheet), agregar al diccionario y volver a correr `make prod-migration`.

---

## [1.12.0] - 2026-04-28

`/ontoy` ahora vive dentro del container `jobs` (un mini HTTP server con `http.server` stdlib, sin deps externas) en lugar de un servicio `version-api` con `nginx:alpine` dedicado. Mismo endpoint, mismo formato JSON, lectura del `version.json` en cada request → hot-update sin restart cuando bumpas `VERSION` y corres `make version-json`.

### Cambiado
- **`/ontoy` integrado en `jobs`** (`jobs/ontoy_server.py`): mini server con `http.server.ThreadingHTTPServer` que lee `/app/version.json` (bind-mount read-only) o fallback `/app/VERSION`. Cero deps Python adicionales (stdlib).
- `jobs/entrypoint.sh`: arranca `ontoy_server.py` en background antes del `exec` de cron.
- `docker-compose.yml`: el servicio `jobs` ahora expone `${VERSION_API_PORT:-8088}:8088`, monta `./VERSION` y `./version-api/html/version.json` read-only, y tiene healthcheck con `urllib.request` (sin nuevas deps).

### Eliminado
- Servicio `version-api` (`nginx:alpine`) — reemplazado por el endpoint embebido en `jobs`.
- `version-api/nginx.conf` — ya no se usa (se conserva `version-api/html/` para el `version.json` generado por `make version-json`).

### Notas
- Ahorro real: −1 container, ~−15 MB RAM. Mismo comportamiento desde el cliente (`curl http://localhost:8088/ontoy`).
- Convivencia con cron: el server HTTP corre en background como child del entrypoint; si `cron -f` (PID 1) muere, docker reinicia el container. Si el server HTTP muere, el healthcheck falla y docker reinicia.

---

## [1.11.0] - 2026-04-27

`icon_url` para temas: identidad visual configurable en cada nodo de tipo `tema` del árbol de capas.

### Agregado
- **Migración alembic 0006** (`jobs/alembic/versions/20260426_0006_layer_icon_url.py`): agrega columna `icon_url TEXT` (nullable) a `mapalab.layers`. Por convención solo aplica a `node_type='tema'`.
- `run_refresh_layer_tree.py` incluye `icon_url` en el `SELECT` y emite `iconUrl` en el JSON cacheado únicamente cuando el nodo es tema (no se propaga a leafs ni groups).

### Cambiado
- `prod-migration.sh` aplica esta migración automáticamente via `alembic upgrade head` (sin pasos manuales en producción).

---

## [1.10.0] - 2026-04-26

Herencia automática del `littleCard` (infobox) desde el group ancestro más cercano, para evitar replicación manual del config en cada hijo. Incluye corrección al bug del head fantasma de alembic que bloqueaba el upgrade tras el bootstrap.

### Agregado
- **Herencia automática de `littleCard` desde el ancestro `group`** (`run_refresh_layer_tree.py`): nueva función `_inherit_little_card` que, al construir el árbol del cache, propaga el `infobox_config` del group ancestro más cercano hacia los descendientes (`leaf` o `group`) que no tienen uno propio. Marca con `inheritedFrom: ancestor_id` para debugging. Permite editar el infobox UNA vez en el group y que todos los hijos lo hereden automáticamente sin replicación. Coordina con mariachi v0.26.0 que ofrece UI de herencia (banner verde "Heredando de X" + botón "Personalizar para esta capa"). Cero cambios necesarios en el visor mapalab.

### Corregido
- **Bug del head fantasma de alembic** (`jobs/bootstrap/v14_schema.sql`): el `INSERT ... ON CONFLICT DO NOTHING` insertaba `0003_metadata_stats` en cada corrida del bootstrap, incluso cuando alembic ya estaba en `0005_map_shares`. Esto creaba dos rows simultáneas en `mapalab.alembic_version_dataengine` y alembic interpretaba dos heads activos, fallando con `"Requested revision 0005_map_shares overlaps with other requested revisions 0003_metadata_stats"` en el siguiente `alembic upgrade head`. Fix: usar `INSERT ... SELECT ... WHERE NOT EXISTS` para que el stamp del baseline solo ocurra cuando la tabla está vacía (BD recién creada). En BDs ya migradas, no toca nada. Para BDs ya afectadas: `DELETE FROM mapalab.alembic_version_dataengine WHERE version_num = '0003_metadata_stats';`
- **Orden en `bootstrap-v14.sh`**: el `alembic upgrade head` se ejecuta ANTES del refresh del `layer_tree_cache` (los modelos SQLAlchemy de `jobs/` esperan columnas que agregan las migraciones nuevas, ej. `mapalab.layers.slug` en 0004; sin esto el `SELECT` fallaba con `"column does not exist"`).

---

## [1.9.0] - 2026-04-24

Persistencia de estado de mapa compartido (`map_shares`) con cleanup automático.

### Agregado
- **Migración alembic 0005** (`jobs/alembic/versions/20260424_0005_map_shares.py`): nueva tabla `mapalab.map_shares` para snapshots persistidos del estado del mapa (layers, order, visibility, opacity, filters, periodicity, loop, basemap, view). Indexada para cleanup sliding-window (`last_accessed_at`) y cleanup pinned (`pinned_until`).
- **Job `run_cleanup_shares.py`** agregado al cron diario de `dataengine-jobs` a las 04:45: borra shares no-pinned con `last_accessed_at` mayor a 30 días y los pinned-expired (`pinned_until < now()`).
- Nueva entrada en `jobs/crontab` para el cleanup diario.

---

## [1.8.0] - 2026-04-24

`slug` público y aliases cortos para capas, base para URLs amigables y referencias estables.

### Agregado
- **Migración alembic 0004** (`jobs/alembic/versions/20260424_0004_layer_slugs_and_aliases.py`):
  - Columna `slug` en `mapalab.layers` (unique, kebab-case, max 60 chars) validada por check constraint.
  - Nueva tabla `mapalab.layer_aliases` para identificadores alternos cortos (ej. `esalud` → `establecimientos-salud`), también validados por check constraint.
- `run_refresh_layer_tree.py` incluye `slug` y `aliases` en el JSON materializado del cache, para que el backend de mapalab los sirva en `/layers/tree`.

### Notas de deploy
Backwards compatible: `slug` es nullable. Mariachi admin lo poblará via su bulk slug generator; los IDs existentes siguen resolviendo hasta el cutover.

---

## [1.7.0] - 2026-04-24

Migraciones de `mapalab` ahora viven en este repo. Antes residían en `mariachi/api/alembic/versions/dataengine/` y aplicarlas en producción requería SSH cross-host (mariachi en S1, dataengine en S4). Con este cambio `make prod-migration` es self-contained.

### Agregado
- **Alembic ownership** (`jobs/alembic/`): `env.py`, `alembic.ini`, `script.py.mako` y los 4 baselines (`0001_init_mapalab_schema`, `0002_layer_tree_cache`, `0003_layer_metadata_stats`) movidos desde `mariachi/api/alembic/versions/dataengine/` hacia este repo.
- `alembic` agregado a `jobs/requirements.txt` y al container `dataengine-jobs`.
- Nuevos targets: `make migrate` (corre `alembic upgrade head` dentro de `dataengine-jobs`) y `make migrate-status` (muestra heads/current).
- `bootstrap-v14.sh` ahora corre `alembic upgrade head` automáticamente al final (idempotente).
- `prod-migration.sh` se vuelve re-ejecutable: default `--skip-etl`; `--with-etl` opt-in para el pull legacy del Google Sheet.

### Referencia
Ver `gateway-hub/docs/ecosystem.md §7.3` (revisado 2026-04-24) para el contexto del split mariachi/dataengine en producción.

---

## [1.6.0] - 2026-04-23

`make prod-migration` consolidado como unico orquestador, con un paso nuevo de GRANTs sobre `mapalab.*` que hace el flujo idempotente de punta a punta y desbloquea a mariachi sin runbooks manuales.

### Agregado
- **Paso 3b en `scripts/bootstrap-v14.sh`: GRANTs sobre `mapalab.*` para `mariachi_layers`**. Despues de aplicar `v14_schema.sql` (que crea las tablas como `POSTGRES_USER`), corre `GRANT SELECT/INSERT/UPDATE/DELETE` sobre todas las tablas y sequences del schema + `ALTER DEFAULT PRIVILEGES` para objetos futuros creados por el mismo rol. Sin esto, `mariachi_layers` queda owner del schema pero sin acceso a las tablas, y el editor de capas en mariachi truena con `permission denied for table layers`. Idempotente.
- **Checklist extendido** al final de `bootstrap-v14.sh`:
  - Nuevo "Paso 3: Conectividad mariachi-api ↔ DataEngine" distinguiendo dev/staging (red docker external) vs produccion (`ALLOWED_HOSTS` + reload de `pg_hba.conf` + `sslmode=require`).
  - Nueva seccion "TROUBLESHOOTING: `permission denied for table layers`" con comando de re-aplicacion rapida (`./scripts/bootstrap-v14.sh --skip-role --skip-seed --skip-migrate`) + las 5 queries SQL exactas como fallback standalone.
- `scripts/prod-migration.sh` + `make prod-migration` — orquesta pull final del Google Sheet (restaurando temporalmente el ETL legacy desde git) + bootstrap v1.4.0 + seed + migrate + stamp alembic en una sola llamada.
- `jobs/bootstrap/layers_export.json` versionado — baseline del tree de capas (250 nodos, 9 temas) recuperado del commit pre-refactor.
- `scripts/drop_mapalab_card_validation.sql` — checklist SQL para validar paridad antes de dropear `public.mapalab_card`.

### Cambiado
- `scripts/bootstrap-v14.sh` — al finalizar hace `alembic stamp dataengine@head` automaticamente si detecta container mariachi, e imprime los pasos siguientes de produccion (ahora 8 pasos, antes 7) + bloque de troubleshooting.
- `jobs/bootstrap/v14_schema.sql` marcado como FROZEN (baseline v1.4.0, no se modifica mas). Cambios futuros via alembic.
- `README.md`: version bump a 1.6.0.

### Eliminado
- Targets make `bootstrap-v14`, `bootstrap-v14-dry`, `migrate-mapalab-card` — consolidados en `make prod-migration`. El script `scripts/bootstrap-v14.sh` sigue existiendo como orquestador interno.
- Archivos huerfanos: `postgres/replica/start-replica.sh`, `postgres/primary/init/02-init-replication.sh`.

### Notas de deploy
Esta version desbloquea el editor de capas en mariachi sin pasos manuales post-bootstrap. Si actualizas un DataEngine **ya provisionado** con una version anterior (donde `mariachi_layers` existe pero no tiene GRANTs sobre las tablas), correr una sola vez para que el editor empiece a funcionar:

```bash
./scripts/bootstrap-v14.sh --skip-role --skip-seed --skip-migrate
```

Eso re-aplica solo el Paso 2 (idempotente), Paso 3 (idempotente) y el nuevo Paso 3b.

### Requiere
Compatible con `mariachi >= 0.13.0` (que configura `DATAENGINE_DATABASE_URL` y `MAPALAB_BACKEND_URL` en sus `.env.*`).

---

## [1.5.0] - 2026-04-22

### Agregado
- **Container `jobs`** (rebautizado desde `mapalab-card`, container `dataengine-jobs`) corriendo `cron -f` con 3 tareas diarias sobre el schema `mapalab`
  - 03:00 `run_refresh_periodicity.py` — invoca `SELECT public.refresh_layer_periodicity()` y cuenta filas de `public.layer_periodicity`
  - 04:00 `run_refresh_layer_tree.py` — reconstruye `mapalab.layer_tree_cache` (singleton JSONB con `etag`, `tree`, `initial_order`, `workspaces`)
  - 04:30 `run_refresh_layer_stats.py` — evalua `stats_config` de cada `mapalab.layer_stats` via template catalog
- **Bootstrap idempotente del schema `mapalab`** para MapaLab v1.4.0+: `make bootstrap-v14 LAYERS_JSON=<path>`
  - `scripts/bootstrap-v14.sh` orquesta 5 pasos: rol `mariachi_layers`, schema `mapalab` + ownership, tablas + seed de workspaces, seed de `mapalab.layers` desde JSON, migracion de `public.mapalab_card` → `mapalab.layer_metadata` + `mapalab.layer_stats`
  - `jobs/bootstrap/v14_schema.sql` crea 6 tablas (`workspaces`, `layers`, `initial_layer_order`, `layer_tree_cache`, `layer_metadata`, `layer_stats`) + indices + FKs + checks + marca de version `0003_metadata_stats` en `mapalab.alembic_version_dataengine`
  - `jobs/bootstrap/run_seed_layers.py` aplana el tree exportado, infiere `node_type`, detecta prefijo `*` como `disabled=true`, ordena topologicamente y upsertea (`ON CONFLICT DO UPDATE`)
  - `jobs/bootstrap/run_migrate_mapalab_card.py` migra filas legacy deduplicando por `layer_key` y arma `fuentes`, `metodologia`, `metadato`, numeralia como JSONB
  - Flags: `--dry-run`, `--skip-role`, `--skip-schema`, `--skip-seed`, `--skip-migrate`, `--password <val>`
  - `make bootstrap-v14-dry` para validar sin persistir
- **`make migrate-mapalab-card`** — target 1-shot (idempotente) que re-corre `run_migrate_mapalab_card.py --apply` como herramienta de recuperacion si el Sheet se actualizo. **OJO**: usa `ON CONFLICT DO UPDATE` y sobreescribe ediciones hechas desde mariachi
- **Template catalog** en `run_refresh_layer_stats.py`: 8 operaciones validadas (`count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`) reemplazan SQL libre. Identificadores validados con regex (`[A-Za-z0-9_]{1,100}`), valores bindeados como `:param`
- **Targets make**: `refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`, `logs-jobs`, `bootstrap-v14`, `bootstrap-v14-dry`, `migrate-mapalab-card`, `restore-local`
- **Crontab** del container jobs (`/etc/cron.d/jobs`) y entrypoint que exporta `DATAENGINE_*` a `/etc/environment` para que cron vea las vars
- Documentacion reorganizada: `docs/architecture.md` (componentes + diagrama Mermaid + schema), `docs/jobs.md` (cron container + template catalog + envs), `docs/bootstrap-v14.md` (pasos + flags + idempotencia + secuencia de deploy en produccion), `docs/CHANGELOG.md` (este archivo), `docs/context.md` (feature map + TODOs)
- `.gitignore`: patron `jobs/iieg2025-cloud-*.json` (credencial de service account GCP no versionada) y `jobs/bootstrap/_layers_export.json` (scratch del bootstrap)
- `README.md` muestra la version actual (`1.5.0`) en la cabecera

### Cambiado
- `mapalab_card/` → `jobs/` (git mv preservando historia); servicio docker `mapalab-card` → `jobs` (container `dataengine-mapalab-card` → `dataengine-jobs`). Scripts externos que invoquen el servicio o lean sus logs deben actualizarse
- **Envs del container `jobs` renombradas** `MAPALAB_CARD_DB_{USER,PASSWORD,HOST,PORT,NAME,SSLMODE}` → `DATAENGINE_DB_*`. Aplicado en `docker-compose.yml`, `jobs/run_refresh_*.py`, `jobs/bootstrap/*.py` y `jobs/entrypoint.sh` (que ahora filtra solo `DATAENGINE_*` hacia `/etc/environment`). `make restore-local` tambien usa el prefijo nuevo
- `jobs/Dockerfile` instala `cron`, copia `crontab` a `/etc/cron.d/jobs` (mode 0644), crea `/var/log/cron.log`
- `jobs/core/utils/logger.py` escribe a `jobs.log` (antes `mapalab_card.log`)
- README raiz reescrito: eliminadas referencias al servicio `mapalab-card` ya renombrado. Documentacion profunda movida a `docs/`

### Eliminado
- **ETL legacy del Google Sheet**: `jobs/run_bootstrap.py`, `jobs/core/mapalab_card/` (framework de actions + sources), `jobs/alembic/mapalab_card/` (migraciones), `jobs/core/schemas/mapalab_card.py`, `jobs/data/mapalab_card/`. La fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editable desde mariachi (`/administrador/mapalab/layers`)
- **Target `make card`** y su flag `FORCE_LEGACY_ETL`: ya no hay ETL que correr
- **Envs legacy del compose**: `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH`, `MAPALAB_CARD_GOOGLE_SHEET_URL`, `MAPALAB_CARD_DATA_WORKING_DIR`, `MAPALAB_CARD_DATA_ERROR_DIR`
- **Mount** `${BACKUP_DATA}/mapalab_card` del servicio `jobs` (ya no hay ETL que lo llene)
- `jobs/requirements.txt`: quita `alembic`, `pandas`, `gspread`, `google-auth`
- `jobs/entrypoint.sh`: quita `alembic upgrade head` del legacy

### Seguridad
- Template catalog reemplaza SQL libre en `stats_config` (ver Agregado)

## [1.4.0] - 2026-04-14

### Agregado
- **PgBouncer** (`edoburu/pgbouncer:latest`) como connection pooler expuesto en `${PGBOUNCER_PORT:-6432}`
  - `pgbouncer/pgbouncer.ini`: `pool_mode = transaction`, `default_pool_size = 40`, `max_client_conn = 300`, `min_pool_size = 10`, `reserve_pool_size = 5`, `auth_type = scram-sha-256`
  - `pgbouncer/entrypoint.sh` genera `userlist.txt` dinamicamente desde `${POSTGRES_USER}/${POSTGRES_PASSWORD}` + usuario admin `pgbouncer_admin`
  - healthcheck con `pg_isready -h localhost -p 6432`
- Configuracion de PostgreSQL optimizada para produccion en `postgres/primary/config/postgresql.conf` montada al primary

### Cambiado
- `docker-compose.yml` agrega el servicio `pgbouncer` a `dataengine-network` con dependencia de `postgres-primary` healthy
- Primary arranca con `postgres -c config_file=/etc/postgresql/postgresql.conf`

## [1.3.1] - 2026-03-30

### Cambiado
- Backups y cron jobs ahora respetan `ENV`: solo se ejecutan en `ENV=production` (de lo contrario emiten warning y salen limpiamente). Comprobacion en `Makefile` (`backup`, `cron-install`)
- `backup/scripts/backup.sh` usa `pg_dump --format=custom --compress=5` con SSL verify-ca
- Retencion consistente en dumps SQL y CSV

### Eliminado
- Configuracion no usada de `insert date` en el ETL de `mapalab_card`

## [1.3.0] - 2026-03-27

### Agregado
- **Periodicidad de capas**: funcion SQL `public.refresh_layer_periodicity()` + tabla `public.layer_periodicity` que calcula y cachea la periodicidad por capa
- `scripts/refresh_periodicity.sql` — migracion/rebuild de la funcion
- `scripts/check_periodicity.sql` — diagnostico: muestra si la periodicidad esta al dia
- `make refresh-periodicity` invoca directamente la funcion SQL via `psql` (antes el refresh pasaba por un service Python)
- `make check-periodicity` corre el diagnostico sobre el primary
- `make card` incluye `refresh-periodicity` al final

### Cambiado
- El refresh de periodicidad deja de ser un script Python + SQLAlchemy: invocacion directa `SELECT public.refresh_layer_periodicity()` (menos dependencias, mas rapido)

## [1.2.0] - 2026-03-18

### Eliminado
- **Servicio `postgres-replica`** (streaming replication hot-standby), rol `replication_user` y configuracion `postgres/replica/*`. Puerto `5433` deja de existir. Clientes que apuntaban a la replica deben migrar al primary en `5432` o al pooler en `6432`
- Credenciales `REPLICATION_USER` / `REPLICATION_PASSWORD` del `.env.example`
- Comandos make `logs-replica` y `shell-replica`

### Corregido
- `postgres/primary/init/01-pg-hba.sh` corrige el caso del `replication_user` antes de eliminarlo, para no romper stacks con volumen existente durante el rollout

## [1.1.2] - 2026-03-12

### Agregado
- Entrypoint del servicio `mapalab-card` corre `alembic upgrade head` antes del proceso principal (migraciones automaticas)
- DEBUG flag en backup y restore para output verbose (`DEBUG=1 make backup`, `DEBUG=1 make restore FILE=...`)
- Entrada host adicional en `pg_hba.conf`

### Cambiado
- Ingesta del Google Sheet: `strip()` aplicado a todas las columnas string; representaciones vacias (`""`, `"nan"`, `"none"`, `"null"`) normalizadas a `None`
- `fecha_ultima_actualizacion` cambia de `Date` a `String` para soportar valores de solo ano (`"2023"`) y anos numericos puros

### Eliminado
- Comandos y codigo de firewall (`fw-status`, `fw-setup`, `fw-reset`): reemplazado definitivamente por `pg_hba.conf` + `ALLOWED_HOSTS`

### Corregido
- Whitespace al inicio/fin en columnas durante ingesta causaba duplicados logicos
- Parsing de `fecha_ultima_actualizacion` rompia con valores numericos (ej. `2023` como int)
- Trailing space en llave `Descripción` en diccionario de actions

## [1.1.1] - 2026-03-09

### Agregado
- **`backup/do-backup.sh`** — wrapper en host con spinner animado (frames braille), tiempo transcurrido y stream en tiempo real del log del container. `make backup` delega a este script
- Naming y politicas de retencion estandarizadas para dumps SQL y CSV; cron del backup ahora semanal (domingos 02:00)
- **Firewall management** (`fw-status`, `fw-setup`, `fw-reset`) en el Makefile — removido en 1.1.2
- `scripts/optimize_delitos_views.sql`: SQL views optimizadas para agregacion de datos de delitos
- Variable `BACKUP_DATA` parametriza el volumen de backups (incluyendo `${BACKUP_DATA}/mapalab_card`)

### Cambiado
- `make restart` incluye `fw-setup` + `cron-install`

### Corregido
- Restore mas robusto ante archivos malformados o inexistentes
- Comentarios y docstrings redundantes eliminados para claridad

## [1.1.0] - 2026-03-08

### Agregado
- **Servicio `mapalab-card`** (container `dataengine-mapalab-card`): ETL desde Google Sheet a `public.mapalab_card` usando `gspread` + `pandas` + `sqlalchemy` + `psycopg2`
  - Framework propio en `mapalab_card/core/` (`action.py`, `etl.py`, `source.py`) con acciones `actinsert`, `actbackup`, `actmapdata` y source `srcdatatabular`
  - Config por envs `MAPALAB_CARD_*` (DB + sheets + dirs)
  - `ID` se resetea a `1` antes de cada ingesta
  - Dropping de filas null
- **Alembic migrations** para `mapalab_card`: `377c681a4c1c_crear_tabla_mapalab_card.py` (tabla inicial)
- **`make card`** dispara la ingesta via `docker compose exec`
- **Cron job host** en el `Makefile`: `make cron-install` instala un entry de crontab que ejecuta `make card` a la hora configurada en `CRON_SCHEDULE` (`HH:MM`). `make cron-remove` lo desinstala
- Credenciales de Google Sheets via env (`MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH`, `MAPALAB_CARD_GOOGLE_SHEET_URL`)
- `.gitignore` con entradas especificas para `mapalab_card/**/*.env`, `mapalab_card/**/*.csv` y la credencial JSON de GCP
- README del servicio en `mapalab_card/README.md`

## [1.0.0] - 2026-02-25

Primera version del stack en produccion. Consolida el cluster PostgreSQL con replica, respaldos al Acervo de Objetos, SSL, control de acceso dinamico y restore con deteccion de formato.

### Agregado
- **Cluster PostgreSQL primary + replica** (streaming replication hot-standby) sobre la imagen `postgis/postgis:18-3.6-alpine`. Primary expuesto en `${PG_PRIMARY_PORT:-5432}`, replica en `${PG_REPLICA_PORT:-5433}`
- **Servicio `pg-backup`** (imagen propia en `./backup`): cron con `crond -f -l 8`, dumps diarios a `/backups` con `pg_dump --format=custom`, subida al Acervo de Objetos via MinIO `mc`, cleanup de dumps `+30 dias`
- **SSL obligatorio** (`sslmode=verify-ca`) entre pg-backup y primary; certificados en `postgres/certs/` generados por `make certs` (CA autofirmada + cert de servidor) y montados como bind mount
- **Control de acceso dinamico** con `postgres/primary/init/01-pg-hba.sh`: siempre permite local + red Docker (`172.16.0.0/12`); para cada IP en `${ALLOWED_HOSTS}` agrega linea `hostssl ... scram-sha-256`; al final `reject` catch-all
- **Replica setup** (`postgres/replica/start-replica.sh` + `postgres/primary/init/02-init-replication.sh`): `pg_basebackup` contra primary, chequeo de system identifier para evitar rebase incorrecto, `pg_isready` explicit a base `postgres`
- **Entrypoint custom del primary** (`postgres/primary/entrypoint.sh`): verifica certs, corrige ownership y permisos (`600` a `server.key`), luego delega a `docker-entrypoint.sh`
- **Restore con deteccion de formato** (`restore/do-restore.sh` + `restore/restore.sh`):
  - auto-deteccion: si no se pasa `FILE`, toma el unico archivo en `./restore/` o presenta un menu numerado con tamanos humanizados
  - inspeccion del header: `PGDMP` → `pg_restore --clean --if-exists --no-owner --no-acl`; `.gz` → `gunzip | psql`; fallback `psql -f`
  - crea PostGIS extensions automaticamente antes del restore
  - spinner animado + stream en tiempo real del log del container
  - mode `continue-on-error` para pg_restore (acepta codigo 1 como warning)
- **Docker named volumes** con prefijo `dataengine` (`dataengine-primary-data`, `dataengine-replica-data`, `dataengine-backups-data`) y red `dataengine-network`
- **Variable `PGDATA`** configurable: permite apuntar a path custom dentro del container
- **MinIO `mc` client** copiado al build del backup (curl eliminado al finalizar), alias `acervo` configurado dinamicamente via env vars (`AO_ENDPOINT`, `AO_BUCKET`, `AO_ACCESS_KEY`, `AO_SECRET_KEY`); si no estan configurados, upload se skipea silenciosamente
- **Makefile** inicial con: `up`, `down`, `restart`, `build`, `ps`, `logs`, `logs-primary`, `logs-replica`, `logs-backup`, `shell`, `shell-replica`, `backup`, `restore`, `clean`, `certs`
- **`.env.example`** con lista de variables requeridas (postgres, AO, allowed hosts, ports)

### Cambiado
- Migracion de `postgres:18.2-alpine` → `postgis/postgis:18-3.6-alpine` (PostGIS + pg_restore preparado para GIS)
- Replace de `supercronic` → `crond` nativo en el container de backup
- SSL cert generation movido de init script → custom entrypoint (evita recrear si ya existen)

### Corregido
- `pg_isready` en replica apunta explicitamente a DB `postgres` (fix para race condition al arranque)
- `pg_restore` continua en errores no fatales (codigo 1) para que rebuilds no quiebren por issues cosmeticos

# Evidencia del caso C-07

Fragmento de la consola del servidor, arrancado con `ECHO_SQL=true`, al pedir el detalle de un libro y de una venta sobre el estado inicial que deja `python seed.py`. Los pedidos son los de `casos_venta.http`.

## Resultado

| Lectura | Pedido | Consultas |
|---------|--------|-----------|
| Detalle de un libro con un autor | `GET /libros/1` | 2 |
| Detalle de un libro con dos autores | `GET /libros/5` | 2 |
| Detalle de una venta con un renglón | `GET /ventas/1` | 2 |
| Detalle de una venta con dos renglones | `GET /ventas/2` | 2 |

La cantidad de consultas es la misma con uno o con varios autores, y con uno o con varios renglones: no hay N+1.

Cómo leer el fragmento:

- Cada consulta es una línea `SELECT`. La línea siguiente (`[cached since ...] (1,)`) muestra el valor del parámetro ligado, no es otra consulta.
- La primera consulta trae la fila principal con sus relaciones a uno (`joinedload`).
- La segunda trae la colección con una sola consulta `IN (...)` (`selectinload`), junto con la relación a uno de cada elemento.
- `BEGIN (implicit)` y `ROLLBACK` son el inicio y el cierre de la transacción de lectura.

## Detalle de un libro con un autor

`GET /libros/1`

```
2026-10-13 19:32:30,080 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-10-13 19:32:30,080 INFO sqlalchemy.engine.Engine SELECT libro.id, libro.isbn, libro.titulo, libro.precio, libro.stock, libro.editorial_id, libro.genero_id, editorial_1.id AS id_1, editorial_1.nombre, editorial_1.pais, genero_1.id AS id_2, genero_1.nombre AS nombre_1 
FROM libro LEFT OUTER JOIN editorial AS editorial_1 ON editorial_1.id = libro.editorial_id LEFT OUTER JOIN genero AS genero_1 ON genero_1.id = libro.genero_id 
WHERE libro.id = $1::INTEGER
2026-10-13 19:32:30,081 INFO sqlalchemy.engine.Engine [cached since 46.03s ago] (1,)
2026-10-13 19:32:30,085 INFO sqlalchemy.engine.Engine SELECT libro_autor.libro_id AS libro_autor_libro_id, libro_autor.autor_id AS libro_autor_autor_id, libro_autor.rol AS libro_autor_rol, libro_autor.orden AS libro_autor_orden, autor_1.id AS autor_1_id, autor_1.nombre AS autor_1_nombre, autor_1.nacionalidad AS autor_1_nacionalidad 
FROM libro_autor LEFT OUTER JOIN autor AS autor_1 ON autor_1.id = libro_autor.autor_id 
WHERE libro_autor.libro_id IN ($1::INTEGER)
2026-10-13 19:32:30,085 INFO sqlalchemy.engine.Engine [cached since 46.03s ago] (1,)
INFO:     127.0.0.1:51520 - "GET /libros/1 HTTP/1.1" 200 OK
2026-10-13 19:32:30,089 INFO sqlalchemy.engine.Engine ROLLBACK
```

## Detalle de un libro con dos autores

`GET /libros/5`

```
2026-10-13 19:32:30,792 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-10-13 19:32:30,793 INFO sqlalchemy.engine.Engine SELECT libro.id, libro.isbn, libro.titulo, libro.precio, libro.stock, libro.editorial_id, libro.genero_id, editorial_1.id AS id_1, editorial_1.nombre, editorial_1.pais, genero_1.id AS id_2, genero_1.nombre AS nombre_1 
FROM libro LEFT OUTER JOIN editorial AS editorial_1 ON editorial_1.id = libro.editorial_id LEFT OUTER JOIN genero AS genero_1 ON genero_1.id = libro.genero_id 
WHERE libro.id = $1::INTEGER
2026-10-13 19:32:30,793 INFO sqlalchemy.engine.Engine [cached since 46.75s ago] (5,)
2026-10-13 19:32:30,797 INFO sqlalchemy.engine.Engine SELECT libro_autor.libro_id AS libro_autor_libro_id, libro_autor.autor_id AS libro_autor_autor_id, libro_autor.rol AS libro_autor_rol, libro_autor.orden AS libro_autor_orden, autor_1.id AS autor_1_id, autor_1.nombre AS autor_1_nombre, autor_1.nacionalidad AS autor_1_nacionalidad 
FROM libro_autor LEFT OUTER JOIN autor AS autor_1 ON autor_1.id = libro_autor.autor_id 
WHERE libro_autor.libro_id IN ($1::INTEGER)
2026-10-13 19:32:30,797 INFO sqlalchemy.engine.Engine [cached since 46.74s ago] (5,)
INFO:     127.0.0.1:51520 - "GET /libros/5 HTTP/1.1" 200 OK
2026-10-13 19:32:30,800 INFO sqlalchemy.engine.Engine ROLLBACK
```

## Detalle de una venta con un renglón

`GET /ventas/1`

```
2026-10-13 19:32:31,503 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-10-13 19:32:31,504 INFO sqlalchemy.engine.Engine SELECT venta.id, venta.cliente_id, venta.fecha, venta.total, cliente_1.id AS id_1, cliente_1.nombre, cliente_1.email 
FROM venta LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER
2026-10-13 19:32:31,504 INFO sqlalchemy.engine.Engine [cached since 47.87s ago] (1,)
2026-10-13 19:32:31,507 INFO sqlalchemy.engine.Engine SELECT renglon_venta.venta_id AS renglon_venta_venta_id, renglon_venta.id AS renglon_venta_id, renglon_venta.libro_id AS renglon_venta_libro_id, renglon_venta.cantidad AS renglon_venta_cantidad, renglon_venta.precio_unitario AS renglon_venta_precio_unitario, libro_1.id AS libro_1_id, libro_1.isbn AS libro_1_isbn, libro_1.titulo AS libro_1_titulo, libro_1.precio AS libro_1_precio, libro_1.stock AS libro_1_stock, libro_1.editorial_id AS libro_1_editorial_id, libro_1.genero_id AS libro_1_genero_id 
FROM renglon_venta LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER)
2026-10-13 19:32:31,507 INFO sqlalchemy.engine.Engine [cached since 47.87s ago] (1,)
INFO:     127.0.0.1:51520 - "GET /ventas/1 HTTP/1.1" 200 OK
2026-10-13 19:32:31,510 INFO sqlalchemy.engine.Engine ROLLBACK
```

## Detalle de una venta con dos renglones

`GET /ventas/2`

```
2026-10-13 19:32:32,214 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-10-13 19:32:32,215 INFO sqlalchemy.engine.Engine SELECT venta.id, venta.cliente_id, venta.fecha, venta.total, cliente_1.id AS id_1, cliente_1.nombre, cliente_1.email 
FROM venta LEFT OUTER JOIN cliente AS cliente_1 ON cliente_1.id = venta.cliente_id 
WHERE venta.id = $1::INTEGER
2026-10-13 19:32:32,215 INFO sqlalchemy.engine.Engine [cached since 48.58s ago] (2,)
2026-10-13 19:32:32,218 INFO sqlalchemy.engine.Engine SELECT renglon_venta.venta_id AS renglon_venta_venta_id, renglon_venta.id AS renglon_venta_id, renglon_venta.libro_id AS renglon_venta_libro_id, renglon_venta.cantidad AS renglon_venta_cantidad, renglon_venta.precio_unitario AS renglon_venta_precio_unitario, libro_1.id AS libro_1_id, libro_1.isbn AS libro_1_isbn, libro_1.titulo AS libro_1_titulo, libro_1.precio AS libro_1_precio, libro_1.stock AS libro_1_stock, libro_1.editorial_id AS libro_1_editorial_id, libro_1.genero_id AS libro_1_genero_id 
FROM renglon_venta LEFT OUTER JOIN libro AS libro_1 ON libro_1.id = renglon_venta.libro_id 
WHERE renglon_venta.venta_id IN ($1::INTEGER)
2026-10-13 19:32:32,219 INFO sqlalchemy.engine.Engine [cached since 48.58s ago] (2,)
INFO:     127.0.0.1:51520 - "GET /ventas/2 HTTP/1.1" 200 OK
2026-10-13 19:32:32,222 INFO sqlalchemy.engine.Engine ROLLBACK
```

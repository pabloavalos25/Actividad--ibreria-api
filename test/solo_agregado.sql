-- C-14: ejecutar sólo sobre un destino de desarrollo/pruebas confirmado.
-- psql -X --no-password -h HOST -p PUERTO -U USUARIO -d BASE \
--   -v movimiento_id=ID_EXISTENTE -f test/solo_agregado.sql
-- No modifica datos persistentes: ambos intentos tienen savepoint y el final
-- revierte todo. Falla con código 3 si falta la fila o se acepta un cambio.
\set ON_ERROR_STOP on
\pset pager off
\if :{?movimiento_id}
\else
  \echo 'C14_FALLO: indicar movimiento_id existente'
  DO $$ BEGIN RAISE EXCEPTION 'Verificacion C14 fallida'; END $$;
\endif

BEGIN;
SELECT row_to_json(m)::text AS fila FROM movimiento_stock AS m
WHERE id = :'movimiento_id'::bigint \gset original_
SELECT id, libro_id, venta_id, usuario_id, cantidad, motivo, cuando
FROM movimiento_stock WHERE id = :'movimiento_id'::bigint;

SAVEPOINT antes_update;
\set ON_ERROR_STOP off
UPDATE movimiento_stock SET motivo = motivo WHERE id = :'movimiento_id'::bigint;
\set update_state :SQLSTATE
\set ON_ERROR_STOP on
ROLLBACK TO SAVEPOINT antes_update;
\echo C14_UPDATE_SQLSTATE :update_state
SELECT :'update_state' = '23514' AS rechazado \gset update_
\if :update_rechazado
\else
  \echo 'C14_FALLO: UPDATE fue aceptado o rechazo inesperado'
  DO $$ BEGIN RAISE EXCEPTION 'Verificacion C14 fallida'; END $$;
\endif

SAVEPOINT antes_delete;
\set ON_ERROR_STOP off
DELETE FROM movimiento_stock WHERE id = :'movimiento_id'::bigint;
\set delete_state :SQLSTATE
\set ON_ERROR_STOP on
ROLLBACK TO SAVEPOINT antes_delete;
\echo C14_DELETE_SQLSTATE :delete_state
SELECT :'delete_state' = '23514' AS rechazado \gset delete_
\if :delete_rechazado
\else
  \echo 'C14_FALLO: DELETE fue aceptado o rechazo inesperado'
  DO $$ BEGIN RAISE EXCEPTION 'Verificacion C14 fallida'; END $$;
\endif

SELECT row_to_json(m)::text = :'original_fila' AS intacto
FROM movimiento_stock AS m WHERE id = :'movimiento_id'::bigint \gset final_
\if :final_intacto
  \echo 'C14_OK: movimiento intacto'
\else
  \echo 'C14_FALLO: movimiento alterado'
  DO $$ BEGIN RAISE EXCEPTION 'Verificacion C14 fallida'; END $$;
\endif
ROLLBACK;

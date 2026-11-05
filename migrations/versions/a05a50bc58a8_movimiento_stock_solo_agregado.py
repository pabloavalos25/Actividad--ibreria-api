"""movimiento_stock_solo_agregado

Revision ID: a05a50bc58a8
Revises: 3e5d56535b0e
Create Date: 2026-11-05 12:38:39.293045

"""
from typing import Sequence, Union

from alembic import op

# Escrita a mano y revisada el 2026-11-05 antes de aplicar. Autogenerate no
# detecta funciones ni triggers. BEFORE UPDATE/DELETE rechaza cambios incluso
# por SQL directo; INSERT sigue permitido. Downgrade quita trigger antes de
# función para que la revisión de tablas pueda revertirse después.

# revision identifiers, used by Alembic.
revision: str = 'a05a50bc58a8'
down_revision: Union[str, None] = '3e5d56535b0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION impedir_cambio_movimiento_stock()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'movimiento_stock es de solo agregado: % no permitido', TG_OP
                USING ERRCODE = '23514';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_movimiento_stock_solo_agregado
        BEFORE UPDATE OR DELETE ON movimiento_stock
        FOR EACH ROW EXECUTE FUNCTION impedir_cambio_movimiento_stock()
    """)


def downgrade() -> None:
    op.execute('DROP TRIGGER trg_movimiento_stock_solo_agregado ON movimiento_stock')
    op.execute('DROP FUNCTION impedir_cambio_movimiento_stock()')

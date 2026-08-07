from typing import Optional
from langchain.tools import tool
from langchain.pydantic_v1 import BaseModel, Field

from db.connection import get_conn


# =============================================================================
# ARGS SCHEMAS
# =============================================================================
class ConsultarEstoqueArgs(BaseModel):
    item_nome: Optional[str] = Field(
        default=None,
        description="Nome (ou parte do nome) do item a consultar. Se ausente, lista todos os itens."
    )


class RegistrarMovimentacaoArgs(BaseModel):
    item_nome: str = Field(..., description="Nome do item cadastrado no estoque.")
    quantidade: float = Field(..., description="Quantidade movimentada (sempre positiva).")
    tipo: str = Field(..., description="Tipo de movimentação: ENTRADA | SAIDA | AJUSTE.")
    motivo: Optional[str] = Field(default=None, description="Motivo da movimentação (opcional).")
    registrado_por: Optional[str] = Field(default="estoquista", description="Cargo que registrou.")
    source_text: str = Field(..., description="Texto original do usuário.")


class ListarBaixoEstoqueArgs(BaseModel):
    limite: Optional[int] = Field(default=20, description="Número máximo de itens a retornar.")


# =============================================================================
# HELPERS
# =============================================================================
def _resolve_type_id(cur, tipo: str) -> Optional[int]:
    cur.execute("SELECT id FROM movement_types WHERE UPPER(type)=%s LIMIT 1;", (tipo.strip().upper(),))
    row = cur.fetchone()
    return row[0] if row else None


def _resolve_item_id(cur, item_nome: str) -> Optional[int]:
    cur.execute("SELECT id FROM items WHERE LOWER(name)=LOWER(%s) LIMIT 1;", (item_nome.strip(),))
    row = cur.fetchone()
    return row[0] if row else None


# =============================================================================
# TOOL: consultar_estoque
# =============================================================================
@tool("consultar_estoque", args_schema=ConsultarEstoqueArgs)
def consultar_estoque(item_nome: Optional[str] = None) -> dict:
    """Consulta a quantidade em estoque de um item específico ou de todos os itens cadastrados."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if item_nome:
            cur.execute(
                """
                SELECT name, unit, current_stock, min_stock
                FROM items
                WHERE LOWER(name) LIKE LOWER(%s)
                ORDER BY name;
                """,
                (f"%{item_nome}%",),
            )
        else:
            cur.execute("SELECT name, unit, current_stock, min_stock FROM items ORDER BY name;")

        rows = cur.fetchall()
        itens = [
            {"nome": r[0], "unidade": r[1], "estoque_atual": float(r[2]), "estoque_minimo": float(r[3])}
            for r in rows
        ]
        return {"status": "ok", "itens": itens}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# =============================================================================
# TOOL: registrar_movimentacao
# =============================================================================
@tool("registrar_movimentacao", args_schema=RegistrarMovimentacaoArgs)
def registrar_movimentacao(
    item_nome: str,
    quantidade: float,
    tipo: str,
    source_text: str,
    motivo: Optional[str] = None,
    registrado_por: Optional[str] = "estoquista",
) -> dict:
    """Registra uma entrada, saída ou ajuste de estoque para um item e atualiza o saldo atual."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        item_id = _resolve_item_id(cur, item_nome)
        if not item_id:
            return {"status": "error", "message": f"Item '{item_nome}' não encontrado no cadastro."}

        type_id = _resolve_type_id(cur, tipo)
        if not type_id:
            return {"status": "error", "message": "Tipo inválido (use ENTRADA, SAIDA ou AJUSTE)."}

        delta = quantidade if tipo.upper() != "SAIDA" else -quantidade

        cur.execute(
            """
            INSERT INTO stock_movements (item_id, quantity, type, reason, registered_by, source_text)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, occurred_at;
            """,
            (item_id, quantidade, type_id, motivo, registrado_por, source_text),
        )
        new_id, occurred = cur.fetchone()

        cur.execute(
            "UPDATE items SET current_stock = current_stock + %s WHERE id = %s RETURNING current_stock;",
            (delta, item_id),
        )
        (novo_saldo,) = cur.fetchone()

        conn.commit()
        return {"status": "ok", "movimentacao_id": new_id, "occurred_at": str(occurred), "novo_saldo": float(novo_saldo)}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# =============================================================================
# TOOL: listar_itens_baixo_estoque
# =============================================================================
@tool("listar_itens_baixo_estoque", args_schema=ListarBaixoEstoqueArgs)
def listar_itens_baixo_estoque(limite: Optional[int] = 20) -> dict:
    """Lista os itens cujo estoque atual está igual ou abaixo do estoque mínimo definido."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT name, unit, current_stock, min_stock
            FROM items
            WHERE current_stock <= min_stock
            ORDER BY (min_stock - current_stock) DESC
            LIMIT %s;
            """,
            (limite,),
        )
        rows = cur.fetchall()
        itens = [
            {"nome": r[0], "unidade": r[1], "estoque_atual": float(r[2]), "estoque_minimo": float(r[3])}
            for r in rows
        ]
        return {"status": "ok", "itens_criticos": itens}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


TOOLS = [consultar_estoque, registrar_movimentacao, listar_itens_baixo_estoque]

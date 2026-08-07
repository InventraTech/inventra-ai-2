from typing import Optional
from langchain.tools import tool
from langchain.pydantic_v1 import BaseModel, Field

from db.connection import get_conn


# =============================================================================
# ARGS SCHEMAS
# =============================================================================
class AprovarRequisicaoArgs(BaseModel):
    requisicao_id: int = Field(..., description="ID da requisição a decidir.")
    aprovar: bool = Field(..., description="True para aprovar, False para rejeitar.")
    notas: Optional[str] = Field(default=None, description="Justificativa da decisão.")


class RelatorioGeralArgs(BaseModel):
    pass


# =============================================================================
# TOOL: aprovar_requisicao
# =============================================================================
@tool("aprovar_requisicao", args_schema=AprovarRequisicaoArgs)
def aprovar_requisicao(requisicao_id: int, aprovar: bool, notas: Optional[str] = None) -> dict:
    """Aprova ou rejeita uma requisição de compra pendente. Ação exclusiva do supervisor."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        novo_status = "APROVADA" if aprovar else "REJEITADA"
        cur.execute("SELECT id FROM requisition_status WHERE UPPER(status)=%s LIMIT 1;", (novo_status,))
        status_id = cur.fetchone()
        if not status_id:
            return {"status": "error", "message": "Status de requisição não configurado no banco."}

        cur.execute(
            """
            UPDATE requisitions
            SET status = %s, notes = COALESCE(%s, notes), updated_at = NOW()
            WHERE id = %s AND status = 1
            RETURNING id;
            """,
            (status_id[0], notas, requisicao_id),
        )
        row = cur.fetchone()
        if not row:
            return {"status": "error", "message": f"Requisição {requisicao_id} não encontrada ou já decidida."}
        conn.commit()
        return {"status": "ok", "requisicao_id": requisicao_id, "novo_status": novo_status}
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
# TOOL: relatorio_geral_estoque
# =============================================================================
@tool("relatorio_geral_estoque", args_schema=RelatorioGeralArgs)
def relatorio_geral_estoque() -> dict:
    """Gera um panorama geral: itens em estoque crítico e requisições pendentes de aprovação."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT name, unit, current_stock, min_stock
            FROM items
            WHERE current_stock <= min_stock
            ORDER BY (min_stock - current_stock) DESC
            LIMIT 10;
            """
        )
        criticos = [
            {"nome": r[0], "unidade": r[1], "estoque_atual": float(r[2]), "estoque_minimo": float(r[3])}
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT r.id, COALESCE(i.name, r.item_name_freeform), r.quantity_requested, r.requested_by, r.created_at
            FROM requisitions r
            LEFT JOIN items i ON i.id = r.item_id
            WHERE r.status = 1
            ORDER BY r.created_at ASC
            LIMIT 10;
            """
        )
        pendentes = [
            {"id": r[0], "item": r[1], "quantidade": float(r[2]), "solicitado_por": r[3], "criado_em": str(r[4])}
            for r in cur.fetchall()
        ]

        return {
            "status": "ok",
            "itens_criticos": criticos,
            "requisicoes_pendentes": pendentes,
            "total_itens_criticos": len(criticos),
            "total_requisicoes_pendentes": len(pendentes),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


TOOLS = [aprovar_requisicao, relatorio_geral_estoque]

from typing import Optional
from langchain.tools import tool
from langchain.pydantic_v1 import BaseModel, Field

from db.connection import get_conn


# =============================================================================
# ARGS SCHEMAS
# =============================================================================
class CriarRequisicaoArgs(BaseModel):
    item_nome: str = Field(..., description="Nome do item solicitado (existente ou novo).")
    quantidade: float = Field(..., description="Quantidade solicitada.")
    unidade: Optional[str] = Field(default="un", description="Unidade de medida (kg, l, un, cx...).")
    solicitado_por: str = Field(..., description="Cargo/usuário que está solicitando (ex: estoquista).")
    notas: Optional[str] = Field(default=None, description="Observações adicionais.")
    source_text: str = Field(..., description="Texto original do usuário.")


class ListarRequisicoesArgs(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="Filtro por status: PENDENTE | APROVADA | REJEITADA | COMPRADA | CANCELADA. Se ausente, lista todas."
    )
    limite: Optional[int] = Field(default=20, description="Número máximo de requisições a retornar.")


class AtualizarStatusRequisicaoArgs(BaseModel):
    requisicao_id: int = Field(..., description="ID da requisição a atualizar.")
    novo_status: str = Field(..., description="Novo status: APROVADA | REJEITADA | COMPRADA | CANCELADA.")
    notas: Optional[str] = Field(default=None, description="Observações sobre a atualização.")


class ListarFornecedoresArgs(BaseModel):
    nome: Optional[str] = Field(default=None, description="Filtro por nome do fornecedor.")


# =============================================================================
# HELPERS
# =============================================================================
def _resolve_status_id(cur, status: str) -> Optional[int]:
    cur.execute("SELECT id FROM requisition_status WHERE UPPER(status)=%s LIMIT 1;", (status.strip().upper(),))
    row = cur.fetchone()
    return row[0] if row else None


def _resolve_item_id(cur, item_nome: str) -> Optional[int]:
    cur.execute("SELECT id FROM items WHERE LOWER(name)=LOWER(%s) LIMIT 1;", (item_nome.strip(),))
    row = cur.fetchone()
    return row[0] if row else None


# =============================================================================
# TOOL: criar_requisicao
# =============================================================================
@tool("criar_requisicao", args_schema=CriarRequisicaoArgs)
def criar_requisicao(
    item_nome: str,
    quantidade: float,
    solicitado_por: str,
    source_text: str,
    unidade: Optional[str] = "un",
    notas: Optional[str] = None,
) -> dict:
    """Cria uma requisição de compra de um insumo, vinculando ao cadastro de itens quando existir."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        item_id = _resolve_item_id(cur, item_nome)
        cur.execute(
            """
            INSERT INTO requisitions
                (item_id, item_name_freeform, quantity_requested, unit, requested_by, status, notes, source_text)
            VALUES (%s, %s, %s, %s, %s, 1, %s, %s)
            RETURNING id, created_at;
            """,
            (item_id, None if item_id else item_nome, quantidade, unidade, solicitado_por, notas, source_text),
        )
        new_id, created_at = cur.fetchone()
        conn.commit()
        return {"status": "ok", "requisicao_id": new_id, "created_at": str(created_at), "status_atual": "PENDENTE"}
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
# TOOL: listar_requisicoes
# =============================================================================
@tool("listar_requisicoes", args_schema=ListarRequisicoesArgs)
def listar_requisicoes(status: Optional[str] = None, limite: Optional[int] = 20) -> dict:
    """Lista requisições de compra, opcionalmente filtradas por status."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if status:
            cur.execute(
                """
                SELECT r.id, COALESCE(i.name, r.item_name_freeform), r.quantity_requested, r.unit,
                       r.requested_by, rs.status, r.notes, r.created_at
                FROM requisitions r
                JOIN requisition_status rs ON rs.id = r.status
                LEFT JOIN items i ON i.id = r.item_id
                WHERE UPPER(rs.status) = %s
                ORDER BY r.created_at DESC
                LIMIT %s;
                """,
                (status.strip().upper(), limite),
            )
        else:
            cur.execute(
                """
                SELECT r.id, COALESCE(i.name, r.item_name_freeform), r.quantity_requested, r.unit,
                       r.requested_by, rs.status, r.notes, r.created_at
                FROM requisitions r
                JOIN requisition_status rs ON rs.id = r.status
                LEFT JOIN items i ON i.id = r.item_id
                ORDER BY r.created_at DESC
                LIMIT %s;
                """,
                (limite,),
            )
        rows = cur.fetchall()
        requisicoes = [
            {
                "id": r[0], "item": r[1], "quantidade": float(r[2]), "unidade": r[3],
                "solicitado_por": r[4], "status": r[5], "notas": r[6], "criado_em": str(r[7]),
            }
            for r in rows
        ]
        return {"status": "ok", "requisicoes": requisicoes}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


# =============================================================================
# TOOL: atualizar_status_requisicao
# =============================================================================
@tool("atualizar_status_requisicao", args_schema=AtualizarStatusRequisicaoArgs)
def atualizar_status_requisicao(requisicao_id: int, novo_status: str, notas: Optional[str] = None) -> dict:
    """Atualiza o status de uma requisição (ex: marcar como COMPRADA após efetuar o pedido ao fornecedor)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        status_id = _resolve_status_id(cur, novo_status)
        if not status_id:
            return {"status": "error", "message": "Status inválido (use APROVADA, REJEITADA, COMPRADA ou CANCELADA)."}

        cur.execute(
            """
            UPDATE requisitions
            SET status = %s, notes = COALESCE(%s, notes), updated_at = NOW()
            WHERE id = %s
            RETURNING id;
            """,
            (status_id, notas, requisicao_id),
        )
        row = cur.fetchone()
        if not row:
            return {"status": "error", "message": f"Requisição {requisicao_id} não encontrada."}
        conn.commit()
        return {"status": "ok", "requisicao_id": requisicao_id, "novo_status": novo_status.upper()}
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
# TOOL: listar_fornecedores
# =============================================================================
@tool("listar_fornecedores", args_schema=ListarFornecedoresArgs)
def listar_fornecedores(nome: Optional[str] = None) -> dict:
    """Lista os fornecedores cadastrados, opcionalmente filtrando por nome."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if nome:
            cur.execute(
                "SELECT name, contact_info FROM suppliers WHERE LOWER(name) LIKE LOWER(%s) ORDER BY name;",
                (f"%{nome}%",),
            )
        else:
            cur.execute("SELECT name, contact_info FROM suppliers ORDER BY name;")
        rows = cur.fetchall()
        fornecedores = [{"nome": r[0], "contato": r[1]} for r in rows]
        return {"status": "ok", "fornecedores": fornecedores}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


TOOLS = [criar_requisicao, listar_requisicoes, atualizar_status_requisicao, listar_fornecedores]

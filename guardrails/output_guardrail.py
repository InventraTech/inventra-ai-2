"""
GUARDRAIL DE SAÍDA
Última etapa do pipeline, antes de devolver a resposta ao usuário.
Garante que:
  1) Nenhum trecho de prompt/código interno vazou na resposta do modelo.
  2) Nenhum padrão de dado sensível foi reproduzido na resposta.
  3) A resposta segue minimamente o formato esperado (começa com um marcador "-").
"""
import re

PADROES_VAZAMENTO_CODIGO = [
    re.compile(r"###\s*PERSONA", re.IGNORECASE),
    re.compile(r"###\s*REGRAS", re.IGNORECASE),
    re.compile(r"SYSTEM_PROMPT", re.IGNORECASE),
    re.compile(r"ChatPromptTemplate", re.IGNORECASE),
    re.compile(r"import\s+os"),
]

PADROES_DADOS_SENSIVEIS = [
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
]


def check_output(texto: str) -> str:
    """Sanitiza a resposta final. Retorna o texto original (ou uma versão segura)."""
    for padrao in PADROES_VAZAMENTO_CODIGO:
        if padrao.search(texto):
            return (
                "- Não posso exibir detalhes internos do sistema.\n"
                "- *Recomendação*: \n"
                "Posso ajudar com estoque, requisições, compras ou dúvidas de uso do Inventra.\n"
            )

    for padrao in PADROES_DADOS_SENSIVEIS:
        if padrao.search(texto):
            texto = padrao.sub("[dado removido por segurança]", texto)

    if not texto.strip().startswith("-"):
        texto = f"- {texto.strip()}\n"

    return texto

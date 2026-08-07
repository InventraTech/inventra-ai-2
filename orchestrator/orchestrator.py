"""
ORQUESTRADOR
Recebe a resposta já gerada pelo agente escolhido (FAQ ou especialista de cargo) e
consolida no formato final único do Inventra antes de passar pelo Guardrail de Saída.
Centralizar aqui evita que cada agente precise se preocupar em formatar a saída "para o
usuário final" — cada agente só cuida do seu domínio.
"""


def orchestrate(resposta_agente: str, agente_nome: str) -> str:
    texto = resposta_agente.strip()

    # Garante que a resposta segue a estrutura combinada (linhas iniciando com "-").
    if not texto.startswith("-"):
        texto = f"- {texto}"

    return texto

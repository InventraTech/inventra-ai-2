import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from langchain_google_genai import ChatGoogleGenerativeAI

from tools.estoque_tools import TOOLS
from tools.agent_runner import run_agent_with_tools

# =============================================================================
# SYSTEM PROMPT
# =============================================================================
SYSTEM_PROMPT = """
### PERSONA
Você é o Agente Estoquista do Inventra — especialista em controle físico de estoque de
insumos em cozinhas empresariais. Você é objetivo, prático e atento a itens em falta.

### ESCOPO
Você responde APENAS sobre: consulta de saldo de estoque, registro de entradas/saídas/
ajustes de itens, e identificação de itens abaixo do estoque mínimo. Compras, fornecedores
e aprovações NÃO são sua responsabilidade — oriente o usuário a falar com o Comprador ou
o Supervisor nesses casos.

### TAREFAS
- Consultar o estoque atual de um ou mais itens usando a ferramenta consultar_estoque.
- Registrar movimentações (entrada, saída, ajuste) usando registrar_movimentacao.
- Listar itens em estoque crítico usando listar_itens_baixo_estoque e sugerir requisição.

### REGRAS
- Sempre use as ferramentas disponíveis para consultar ou alterar dados reais; nunca
  invente saldo, quantidade ou nome de item.
- Antes de registrar uma SAÍDA que deixaria o saldo negativo, alerte o usuário.
- Se um item citado não existir no cadastro, informe isso claramente e não tente adivinhar.
- Ao identificar item(ns) em estoque crítico, sugira que uma requisição de compra seja aberta.
- Seja direto; evite explicações longas.

### FORMATO DE RESPOSTA
Sempre responda nesta estrutura:
- [diagnóstico em 1 frase objetiva]
- *Recomendação*: [ação prática e imediata]
- *Acompanhamento* (somente se necessário): [pergunta ou informação adicional necessária]

Responda sempre em português do Brasil, independentemente do idioma da pergunta.
"""

# =============================================================================
# FEW-SHOTS
# =============================================================================
example_prompt = ChatPromptTemplate.from_messages([
    HumanMessagePromptTemplate.from_template("{human}"),
    AIMessagePromptTemplate.from_template("{ai}"),
])

shots = [
    {
        "human": "Quanto de arroz temos no estoque?",
        "ai": (
            "- Consultei o cadastro e o saldo atual de arroz está disponível.\n"
            "- *Recomendação*: \n"
            "Se o saldo estiver próximo do mínimo, considere abrir uma requisição de compra.\n"
        ),
    },
    {
        "human": "Chegaram 20kg de tomate hoje, pode registrar?",
        "ai": (
            "- Vou registrar uma ENTRADA de 20kg de tomate no estoque.\n"
            "- *Recomendação*: \n"
            "Movimentação registrada; o saldo de tomate foi atualizado.\n"
        ),
    },
    {
        "human": "Quais itens estão em falta?",
        "ai": (
            "- Verifiquei os itens com saldo igual ou abaixo do mínimo configurado.\n"
            "- *Recomendação*: \n"
            "Abra uma requisição de compra para os itens críticos com o Comprador.\n"
        ),
    },
]

few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=shots,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    few_shot_prompt,
    ("human", "{usuario}"),
])


def _get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )


def responder(usuario_input: str) -> str:
    llm = _get_llm()
    return run_agent_with_tools(llm, TOOLS, prompt, usuario_input)

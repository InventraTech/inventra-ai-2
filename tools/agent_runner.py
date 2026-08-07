"""
Loop genérico de execução de agente com ferramentas (tool-calling).
Reutilizado pelos três agentes especializados (Estoquista, Comprador, Supervisor)
para não duplicar a lógica de invocar o modelo -> checar tool_calls -> executar
a tool -> devolver o resultado ao modelo -> obter resposta final.
"""
from langchain_core.messages import HumanMessage, ToolMessage


def run_agent_with_tools(llm, tools, prompt, usuario_input: str, max_iters: int = 4) -> str:
    """
    llm: ChatGoogleGenerativeAI (ou compatível) já com .bind_tools(tools) aplicado externamente
         OU passado "cru" — aqui aplicamos o bind para manter o chamador simples.
    tools: lista de @tool do módulo correspondente
    prompt: ChatPromptTemplate (persona + few-shots + entrada real)
    usuario_input: texto atual do usuário
    """
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = prompt.format_messages(usuario=usuario_input)

    for _ in range(max_iters):
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not getattr(ai_msg, "tool_calls", None):
            return ai_msg.content

        for call in ai_msg.tool_calls:
            tool_fn = tools_by_name.get(call["name"])
            if tool_fn is None:
                result = {"status": "error", "message": f"Ferramenta '{call['name']}' desconhecida."}
            else:
                result = tool_fn.invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    # fallback: força uma resposta final sem novas chamadas de ferramenta
    final = llm.invoke(messages)
    return final.content

"""
INVENTRA AI — PONTO DE ENTRADA
Implementa o pipeline completo da arquitetura:

  User
   -> Guardrail entrada (palavrões / acesso ao código / dados sensíveis)
        -> [bloqueado] Parar resposta
        -> [ok] FAQ  OU  Roteador -> Agente do cargo (Estoquista | Comprador | Supervisor)
   -> Orquestrador
   -> Guardrail Saída
   -> User
"""
from guardrails.input_guardrail import check_input
from guardrails.output_guardrail import check_output
from orchestrator.orchestrator import orchestrate
from agents import faq_agent, router_agent


class InventraAI:
    CARGOS_VALIDOS = ("estoquista", "comprador", "supervisor")

    def responder(self, mensagem_usuario: str, cargo_usuario: str) -> str:
        # 1) GUARDRAIL DE ENTRADA
        resultado = check_input(mensagem_usuario)
        if resultado.bloqueado:
            from guardrails.input_guardrail import mensagem_para
            # A resposta de bloqueio também passa pelo guardrail de saída por consistência.
            return check_output(mensagem_para(resultado.motivo))

        # 2) FAQ vs ROTEADOR
        tipo = router_agent.classify_query(mensagem_usuario)

        if tipo == "faq":
            resposta_bruta = faq_agent.responder(mensagem_usuario)
            agente_nome = "faq"
        else:
            agente = router_agent.select_specialist(cargo_usuario)
            resposta_bruta = agente.responder(mensagem_usuario)
            agente_nome = cargo_usuario

        # 3) ORQUESTRADOR
        resposta_orquestrada = orchestrate(resposta_bruta, agente_nome)

        # 4) GUARDRAIL DE SAÍDA
        resposta_final = check_output(resposta_orquestrada)
        return resposta_final


def _cli():
    print("=== Inventra AI (CLI de teste) ===")
    print("Cargos disponíveis: estoquista, comprador, supervisor")
    cargo = input("Informe seu cargo: ").strip().lower()
    while cargo not in InventraAI.CARGOS_VALIDOS:
        cargo = input("Cargo inválido. Tente novamente (estoquista/comprador/supervisor): ").strip().lower()

    app = InventraAI()
    print("Digite sua mensagem (ou 'sair' para encerrar).")
    while True:
        msg = input(f"[{cargo}] > ").strip()
        if msg.lower() in ("sair", "exit", "quit"):
            break
        resposta = app.responder(msg, cargo)
        print(resposta)


if _name_ == "_main_":
    _cli()
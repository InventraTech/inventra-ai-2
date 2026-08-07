# Inventra AI

IA multiagente para o app **Inventra**, seguindo a arquitetura combinada:

```
User
  -> Guardrail entrada (palavrões / acesso ao código / dados sensíveis)
       -> [bloqueado] Parar resposta
       -> [ok] ─┬─> FAQ ──────────────────────────────┐
                └─> Roteador -> Agente do cargo:       │
                                  Estoquista            │
                                  Comprador             ├─> Orquestrador -> Guardrail Saída -> User
                                  Supervisor             │
```

## Estrutura de pastas

```
inventra_ai/
├── main.py                     # ponto de entrada: monta o pipeline completo
├── requirements.txt
├── .env.example
├── db/
│   ├── schema.sql              # tabelas: items, stock_movements, requisitions, suppliers...
│   └── connection.py           # get_conn() (psycopg2), mesmo padrão de pg_tools_pt2.txt
├── guardrails/
│   ├── input_guardrail.py      # bloqueia palavrões, tentativa de acesso ao código, dados sensíveis
│   └── output_guardrail.py     # segunda camada: sanitiza a resposta final
├── knowledge/
│   └── faq_inventra.md         # funcionalidades + tabela de contatos usada pelo agente FAQ
├── tools/
│   ├── estoque_tools.py        # tools do Estoquista (consultar_estoque, registrar_movimentacao...)
│   ├── compras_tools.py        # tools do Comprador (criar_requisicao, listar_fornecedores...)
│   ├── supervisor_tools.py     # tools do Supervisor (aprovar_requisicao, relatorio_geral_estoque)
│   └── agent_runner.py         # loop compartilhado de tool-calling usado pelos 3 agentes
├── agents/
│   ├── faq_agent.py            # agente sem tools, responde com base em knowledge/faq_inventra.md
│   ├── router_agent.py         # decide FAQ x operacional, e escolhe o agente pelo cargo
│   ├── estoquista_agent.py     # agente especializado do Estoquista
│   ├── comprador_agent.py      # agente especializado do Comprador
│   └── supervisor_agent.py     # agente especializado do Supervisor
└── orchestrator/
    └── orchestrator.py         # padroniza a resposta final antes do guardrail de saída
```

Cada cargo tem seu **próprio agente** (persona, escopo, tarefas, regras e few-shots
isolados), exatamente para que o system prompt de cada um não precise crescer com
assuntos de outros cargos — só o Roteador sabe qual agente chamar.

## Como rodar

1. Crie o banco com `db/schema.sql` em um Postgres.
2. Copie `.env.example` para `.env` e preencha `GOOGLE_API_KEY` e `DATABASE_URL`.
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Rode o CLI de teste:
   ```
   python main.py
   ```
   Ele vai pedir o cargo (`estoquista`, `comprador` ou `supervisor`) e depois abrir um
   loop de conversa chamando `InventraAI().responder(mensagem, cargo)`.

## Uso programático

```python
from main import InventraAI

app = InventraAI()
resposta = app.responder("Quanto de arroz temos no estoque?", cargo_usuario="estoquista")
print(resposta)
```

## Notas de design

- O **Guardrail de entrada** é heurístico (palavras-chave/regex) — por isso o diagrama
  original anota "pode ser que não pare". Como segunda camada de proteção, o
  **Guardrail de saída** sanitiza qualquer vazamento de prompt/código ou dado sensível
  que tenha passado pelo modelo.
- O **agente FAQ** não tem acesso a nenhuma tool de banco de dados — ele só orienta sobre
  funcionalidades e contatos, conforme a nota do diagrama ("Contatos" / "Funcionalidades").
- Os três agentes de cargo reutilizam `tools/agent_runner.py` para o loop de tool-calling,
  evitando duplicar a lógica de invocar o modelo, executar a tool e devolver o resultado.
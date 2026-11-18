# Star Imports — MVP de separação de pedidos

Aplicação demonstrativa para consultar pedidos e cancelar itens separados antes da coleta. O projeto transforma o planejamento da Experiência Prática II em um MVP executável.

## Funcionalidades

- Consulta de pedido pelo código.
- Exibição do estado do pedido, itens e saldo.
- Cancelamento idempotente de itens apenas antes da coleta, com reposição de estoque na mesma transação.
- Interface responsiva, operável por teclado e com mensagens textuais de estado.

## Executar localmente

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Abra http://127.0.0.1:5000. O banco SQLite e os dados de demonstração são criados automaticamente na primeira execução. Pedido de demonstração: `DS-1042`.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes usam um banco temporário e cobrem consulta, cancelamento permitido, bloqueio após coleta, pedido inexistente e prevenção de reposição duplicada.

## Limites do MVP

Esta versão é um protótipo funcional local, com dados fictícios. Não integra ERP, autenticação corporativa nem estoque real. O banco de demonstração não deve ser usado em produção. A validação com pessoas da comunidade ainda precisa ser realizada e registrada separadamente.

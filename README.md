# Trader Pro AI Elite v0.4 — pesquisa e auditoria, sem ordens reais

Este projeto evolui o app Streamlit v0.3. É **um motor de regras determinísticas**, não uma IA treinada, não acessa dados ao vivo, não se conecta à B3/corretoras e não garante taxas de acerto.

## Publicação no GitHub e Streamlit (celular)

1. Baixe e **extraia** o ZIP. No seu repositório existente, envie/substitua os arquivos `app.py`, `engine.py`, `backtest.py`, `audit.py`, `requirements.txt`, `test_engine.py`, `test_backtest.py` e `README.md` na **raiz** do repositório. Não envie o ZIP como se fosse código Python.
2. Confirme o commit. A instalação do Streamlit Cloud existente deve apontar para **`app.py`**. Se já estiver conectada ao mesmo repositório, ela geralmente fará o redeploy após o commit.
3. Abra a aplicação e execute a demonstração fictícia para conferir a interface. Para estudar dados históricos, envie um CSV OHLC de WIN legítimo, 5 min, horário de Brasília, com as colunas abaixo. **O CSV de backtest v0.3 contém operações, não candles, e só serve para a aba de auditoria.**

## Formato do CSV de candles

`datetime,open,high,low,close,volume` (volume opcional). Um candle por linha com data/hora de **abertura** no formato `2026-11-20 09:00:00`, em horário de Brasília. Também aceita alguns cabeçalhos em português e timestamps com offset de fuso. Ordenar em ordem crescente.

## Mudanças da v0.4

- Grade de **5 pontos por preço** do contrato WIN, OHLC consistente, candles exatos de 5 minutos e pregão regular: rejeição explícita de dados incoerentes, sem arredondamento silencioso.
- Demonstração fictícia gerada apenas entre 09:00 e 18:20 em dias úteis de pregão, com preços válidos de 5 pontos; não gera candles no feriado de 20/11/2026. **Simulação fictícia não indica desempenho real.**
- Confirmação real de tendência com **candles completos de 15 minutos** — sem uso antecipado de um candle ainda aberto — e rompimento de três candles anteriores.
- Entrada ao abrir o candle seguinte, uma posição por vez, stop prioritário se alta/baixa tocar stop e alvo no mesmo candle, gaps desfavoráveis respeitados.
- Entrada até 17:55; liquidação do que restar até o fechamento do candle das 18:10 (18:15); não atravessa pregões.
- Tick no stop/alvo, slippage adverso na entrada/saída e taxas separadas; horário exato de toque intrabar é explicitamente desconhecido; limite de operações diárias e de perda diária em pontos; drawdown com capital inicial de 0.
- Aba de auditoria para verificar registros da versão antiga sem reescrever seus resultados.

## Observações e limitações

A grade 09:00–18:25 é uma referência de negociação **regular** para nov/2026. Não cobre todos os feriados, eventos, leilões, vencimentos e alterações históricas de horário da B3. O validador **não certifica a autenticidade** do CSV (um arquivo sintético pode obedecer à grade). Faltam ainda fonte independente de dados históricos, calendário oficial de sessões/vencimento, custos da corretora, bid/ask, ajustes de contrato, análise fora da amostra, análise por regime e validação estatística. O slippage configurado é uma hipótese constante, não uma estimativa de liquidez real.

Para estudos comparáveis, registre os parâmetros antes de testar, separe períodos de desenvolvimento e avaliação, e evite ajustes guiados pelo mesmo resultado. Não use estes sinais para operar dinheiro real.

**B3 — dados de referência:**
- https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm
- https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/
- https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm

# Trader Pro AI Elite v0.7 — Pesquisa e auditoria (WIN)

Aplicativo em Streamlit de **simulação retrospectiva de regras**, sem acesso ao mercado ao vivo, sem envio de ordens e sem inteligência artificial treinada. Não há qualquer garantia de lucro ou precisão. **Não usar para operar dinheiro real.**

## Atualizar pelo celular

1. Baixe o ZIP da v0.7 e **extraia** os arquivos.
2. No repositório conectado ao Streamlit, substitua `app.py`, `engine.py`, `backtest.py`, `audit.py`, `test_engine.py`, `test_backtest.py`, `requirements.txt` e `README.md` na **raiz**.
3. Confirme em **Commit changes** e abra o aplicativo no Streamlit. A faixa superior deve exibir **V0.7**. O arquivo de entrada permanece `app.py`.
4. Abra **🛑 Não operar** para ver sinais detectados, candidatos elegíveis no horário, motivos completos por candle e CSV auditável.
5. Na aba **🧪 Backtest**, examine a auditoria de cada candidato ou compare os perfis sob **os mesmos parâmetros**.

## Mudanças da v0.7

- **Gate unificado** do motor e do backtest: distingue `COMPRA/VENDA` detectados de candidatos autorizados pelo **calendário da B3**, horário, candle seguinte disponível e vencimento. Um sinal ainda não significa operação executada; limites de risco e posições abertas são analisados na simulação.
- **Feriados bloqueados obrigatoriamente** na validação dos CSVs, geração de demonstração, elegibilidade de sinais, auditoria e backtest. Bloqueio também de sábados e domingos.
- **Falha fechada:** aceita apenas datas de 2026, para as quais esta implementação possui calendário confirmado. Não supõe automaticamente que um dia de 2027, por exemplo, esteja aberto.
- **Pregão especial 18/02/2026:** início a partir das 13h. No vencimento do contrato não geramos novas posições. Vencimentos e horários especiais adicionais devem ser verificados com a B3 antes de uso com dados reais.
- **Todos os motivos diagnósticos** para candles `AGUARDAR` passam a constar de colunas `all_reason_codes` e `all_reason_details`, além do motivo principal.
- **Comparação de perfis** base v0.5 / seletivo v0.7 na interface, usando os mesmos custos, slippage e limites de risco.
- **Registro de auditoria** com o código do bloqueio de horário/calendário para cada sinal detectado, exportado em CSV.
- A visualização e o relatório JSON indicam calendário e regras de bloqueio. Dados sintéticos continuam explicitamente identificados.

## Arquivos de dados históricos

CSV de candles OHLC de cinco minutos: `datetime,open,high,low,close[,volume]`; timestamps de **abertura**, em Brasília (America/Sao_Paulo). Se o CSV contiver `ticker`, `symbol` ou `contrato`, os valores devem concordar com o vencimento declarado (ex.: `WINZ26`). É necessário identificar a fonte e o contrato; isso não certifica a autenticidade. Contratos contínuos não são aceitos como contratos reais específicos.

Para backtest, as **sessões precisam estar completas**, com preços na grade de cinco pontos do WIN, horário correto, sem duplicações ou gaps intradiários. Dias posteriores ao vencimento são rejeitados. A versão não cobre todos os leilões, eventos extraordinários, modificações futuras ou horários históricos fora das regras codificadas para 2026. Feriados de outros anos exigem calendário publicado e testado antes da liberação.

## Testar localmente

```bash
pip install -r requirements.txt
python -m pytest -q test_engine.py test_backtest.py
streamlit run app.py
```

Os testes unitários verificam somente **integridade do código**, não a estratégia. Os sinais continuam experimentais; com preços sintéticos não é possível estimar acurácia verdadeira. Custos, slippage e preenchimento por OHLC são simplificados, não refletem necessariamente negociações executáveis.

## Fontes oficiais da B3

- https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm
- https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/

`2026-11-20`, `2026-12-24`, `2026-12-25` e `2026-12-31` são datas sem pregão WIN, por exemplo. **Não assuma** que feriado bancário americano implica fechamento do WIN na B3.

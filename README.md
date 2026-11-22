# Trader Pro AI Elite v0.5 — Pesquisa em WIN (sem ordens reais)

Aplicativo responsivo Streamlit, com interface premium de pesquisa histórica. **Não é uma IA treinada**, não tem conexão com corretora, não opera ao vivo e **não prevê a taxa de acerto futura**. O motor permanece determinístico (EMA 9/21, RSI 14, ATR 14, confirmação 15m e rompimento de três candles).

## Instalação no GitHub pelo celular

1. Baixe e **extraia** o ZIP. No repositório GitHub existente, substitua os oito arquivos da raiz: `app.py`, `engine.py`, `backtest.py`, `audit.py`, `test_engine.py`, `test_backtest.py`, `requirements.txt` e `README.md`. **Não publique só o arquivo .zip**.
2. Confirme o *Commit changes*. Se o aplicativo já foi publicado no Streamlit Community Cloud e a implantação usa o mesmo repositório, verifique se o arquivo principal está definido como **`app.py`**; a atualização normalmente acontece após o commit.
3. Abra o aplicativo, selecione *Demonstração fictícia* na barra lateral, e rode um teste apenas para verificar a interface.
4. Para dados históricos, selecione *CSV histórico · origem declarada* e envie **candles reais** de fonte que você possa identificar; informe a fonte, ticker do contrato (ex.: `WINZ26`) e confirme a declaração. **O app não compra, baixa ou autentica os candles.**

## CSV histórico aceito

Colunas: `datetime,open,high,low,close,volume` (volume opcional). Timestamps são da **abertura** de cada candle de cinco minutos no horário de Brasília; sem offset são interpretados como BRT. Exemplo de formato: `2026-11-19 09:00:00`.

Este protótipo restringe a validação a **2026** porque só tem calendário codificado para esse ano; valida 5 pontos por tick, consistência OHLC, sequência temporal, feriados conhecidos, horário regular e prazo de vencimento **nominal** do contrato. O contrato contínuo `WIN` não é aceito para a amostra histórica: é necessário declarar um vencimento específico, por exemplo `WINZ26` (dez/2026). No dia do vencimento, o contrato vincendo encerra a negociação antecipadamente; por precaução a v0.5 **não faz operações nesse dia**.

Para habilitar o *backtest*, cada dia que aparece no CSV deve estar **completo**. Para um dia normal: abertura do primeiro candle às **09:00**, último às **18:20**, sem lacunas (113 candles). O pregão especial de 18/02/2026 e o horário do contrato no vencimento têm regras diferenciadas. A análise no terminal pode aceitar uma amostra parcial válida, mas o backtest irá rejeitá-la. Isso impede o modelo de contabilizar um fechamento fictício quando faltam candles.

**Atenção:** a grade e os horários são referência para 2026 e não incluem todas as exceções históricas, suspensões, leilões, eventos e alterações oficiais. O simples fato de passar na validação **NÃO prova que um arquivo veio da B3**, nem que seus preços são autênticos. Preços inventados podem obedecer à grade. Dados de vencimentos diferentes, séries contínuas ajustadas ou exportações com fuso incorreto podem distorcer resultados. O usuário precisa verificar os dados e a licença de seu provedor.

## Mudanças da v0.5

- Identifica a demonstração sintética de forma inequívoca; ela nunca é apresentada como desempenho de mercado.
- Exige **fonte declarada**, **contrato específico** e confirmação antes da análise de CSV histórico. A fonte é **declarada, não auditada**.
- Salva hash **SHA-256 do arquivo** no relatório de origem e na exportação das operações (ajuda a reproduzir o estudo; **não certifica autenticidade**).
- Verifica o vencimento nominal do contrato informado e impede dados pós-vencimento; exclui operações no dia do vencimento.
- Recusa backtests de dias parciais, evitando fechamento artificial por ausência de dados.
- Exibe *profit factor*, alerta para amostras pequenas e registra condições para sinal `AGUARDAR` / **NÃO OPERAR**.
- Mantém gestão conservadora: posição única, entrada na abertura seguinte, stop prioritário quando stop/alvo são tocados no mesmo candle, slippage adverso dos dois lados, custos separados, máximo de 3 operações/dia por padrão e limite diário de perdas **realizadas**. O limite não é garantido em perdas intratrade ou por gaps.

## Como executar testes

```bash
pip install -r requirements.txt
python -m pytest -q test_engine.py test_backtest.py
streamlit run app.py
```

Os testes usam preços gerados artificialmente: verificam integridade do código, **não** desempenho da estratégia. A amostra fictícia v0.4 tinha 10 operações e saldo líquido negativo; isso não mede o mercado real.

## Limitações para próximos ciclos

Obter dados históricos reais de fonte com permissão, validar sessões e vencimentos com calendário atualizado, verificar múltiplos períodos e regimes, fazer validação fora da amostra, modelar custos e liquidez reais, estimar incerteza e comparar com estratégias ingênuas. Nenhuma otimização deve ser feita olhando repetidamente para o mesmo período de avaliação. O aplicativo não está habilitado para investimentos ou operações reais.

Fontes oficiais B3:
- [Especificação do WIN (tick e vencimentos)](https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm)
- [Horários dos derivativos de índices](https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/)
- [Calendário de negociação de 2026](https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm)

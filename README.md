# ◈ Trader Pro AI Elite v1.3 — Laboratório de Integridade de Contratos

Pesquisa **exploratória** de dados históricos WIN (2019–2020), sem ordens, mercado ao vivo ou backtest desta série. Design premium roxo/escuro para celular. **Não é IA treinada** nem possui taxa de acerto comprovada.

## Atualizar pelo celular (GitHub + Streamlit Cloud)

1. Baixe **Trader_Pro_AI_Elite_v1_3_GitHub.zip** e extraia no celular.
2. No **mesmo repositório GitHub** ligado ao app atual, escolha **Add file → Upload files**. Envie os **20 arquivos extraídos**, na raiz, substituindo os nomes existentes. **Não** envie o arquivo .zip sozinho.
3. Confirme **Commit changes** na branch `main`. O arquivo principal continua `app.py`.
4. Reabra o aplicativo Streamlit. Verifique o cabeçalho **RESEARCH TERMINAL · V1.3**.
5. Selecione **🔬 Explorar 2019–2020 · SEM backtest** e envie novamente o CSV de candles já disponível (`WIN_2019_2020_5min_exploratorio.csv`) ou o `data.csv` original.
6. Abra a aba **🔬 Histórico**, vá a **🧭 Integridade dos contratos · v1.3** e use os cartões/filtros e exportações.
7. Opcionalmente, no campo **Conferir CSV de qualidade por dia da v1.2**, envie `qualidade_por_dia_win_v12.csv` para cotejar datas e quantidades; isso verifica apenas consistência estrutural, não autenticidade dos preços.

**Não inclua dados históricos obtidos de terceiros no seu repositório público** sem verificar as condições de uso. O ZIP inclui apenas código, testes, dependências e documentação. Se o Streamlit Cloud estiver conectado ao repositório, em geral redeployará após o commit. Não precisa pagar Replit nem executar Python no celular.

## O que mudou na v1.3

O módulo novo `integrity_lab.py` produz **cinco saídas exploratórias**:

- **Integridade por dia**: reconcilia os candles com o relatório diário recalculado, relaciona lacunas, abertura divergente, maior variação entre sessões, proximidade e dia nominal de vencimento. Todos os dias permanecem `NAO_CERTIFICADO` e `backtest_liberado=False`.
- **Eventos de continuidade**: separa explicitamente **lacunas temporais**, **variações entre candles consecutivos** e **variações entre sessões**. Jamais atravessa um candle ausente para tratar dois preços como consecutivos.
- **Comparação mensal**: total observado, dias com lacunas, candles ausentes entre extremos, aberturas divergentes e alertas exploratórios por mês.
- **Janelas ±2 dias das datas de vencimento nominais**: pontos para conferência de eventual rolagem; **não detecta o contrato que estava em negociação** nem confirma ajuste, continuidade ou troca efetiva.
- **Resumo JSON e comparação opcional** com `qualidade_por_dia_win_v12.csv`: nomes e totais verificados, sem afirmar autenticidade primária.

**Metodologia de alertas de preço:** `abs(abertura_atual - fechamento_anterior)` é avaliada entre *candles adjacentes de 5 minutos do mesmo pregão*, sem saltos de tempo, e o limiar de destaque é o máximo entre 20 pontos e o percentil 99,9% da amostra arredondado para múltiplos de 5. Entre pregões, o limiar de destaque é o percentil 95 do valor absoluto das diferenças entre o último fechamento observado e a primeira abertura observada seguinte. Os percentis são calculados **sobre a própria amostra** e são **apenas estatísticas descritivas**, não critérios de preço errado, detecção de rolagem ou parâmetros válidos para trading. As variações entre pregões podem ser movimentos normais de mercado.

## Conferência com o CSV fornecido

A conferência por data e contagem do arquivo `qualidade_por_dia_win_v12.csv` enviado pelo usuário bateu **integralmente** com a auditoria regenerada do arquivo de candles desta conversa: **181 dias, zero divergências estruturais**. Isso **não verifica** origem, ticker, contrato, qualidade dos negócios reais ou direitos de redistribuição.

Resumo dos resultados da amostra de pesquisa:

| Medida | Resultado |
|---|---:|
| Candles observados de 5 minutos | 19.257 |
| Pregões com registros | 181 |
| Saltos de tempo intradiários | 72 |
| Candles de 5 minutos faltantes entre os extremos observados | 166 |
| Dias com lacunas | 15 |
| Dias com abertura divergente da referência adotada | 64 |
| Comparações de candles adjacentes no mesmo dia | 19.004 |
| Diferenças de preço adjacente ≥ limiar descritivo (30 pontos nessa amostra) | 24 |
| Diferenças entre sessões no top 5% empírico | 9 |
| Datas nominais de vencimento no recorte | 5 |
| Dias aptos para backtest/negociação | **0** |

Concentração das barras faltantes entre extremos: **março de 2020 (157)** e **abril de 2020 (9)**, segundo a amostra. **Não presumir** que a causa seja circuit breaker, falta de negócios ou problema na origem. Nenhum fechamento diário foi certificado.

Os arquivos de origem de 1 minuto e convertido para 5 minutos produzem os **mesmos totais** nesta análise. O app recalcula internamente quando importa o arquivo, sem precisar enviar relatório diário antigo.

## Controle de risco e limitações

- Dados de 2019–2020: **sem sinais, sem backtest e sem ordens** — não chamar motor `engine.analyze()` ou `backtest()` nesse modo.
- 2026: o modo rigoroso anterior é preservado (calendário e bloqueios mantidos). Não foi alterado para aceitar o histórico antigo.
- A ausência de lacunas detectadas não prova encerramento, origem, fuso, negociação ou continuidade de série.
- O arquivo público não informa o **código de vencimento** do contrato por candle nem se contém emenda/ajuste de rolagem.
- Os horários e o calendário de 2019/2020 são referências com exceções documentadas, mas as sessões finais por data não foram autenticadas.
- O SHA-256 verifica apenas identidade de bytes, **não** procedência dos negócios na B3.
- O aplicativo é um laboratório de pesquisa; **não usar para decisões de investimento com dinheiro real**.

## Fontes oficiais de referência

- [B3 — futuro mini de Ibovespa (WIN): variação mínima e vencimentos](https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm)
- [B3 — calendário de 2019](https://www.b3.com.br/data/files/F8/B3/88/A0/33E97610F157B776AC094EA8/CL%20049-2018_EN_VOP%20Feriados%202019_v7%20R_2.pdf)
- [B3 — calendário de 2020](https://www.b3.com.br/data/files/97/C7/BB/E1/F50BF6109A4874F6AC094EA8/OC%20003-2020-VOP%20Feriados%202020.pdf)
- [B3 — exceções de negociação em 2020](https://www.b3.com.br/pt_br/noticias/funcionamento-da-b3-8AE490C97215B74E0172959F18F11323.htm)

## Testar desenvolvimento (opcional, pelo computador)

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
streamlit run app.py
```

**79 testes automatizados passaram no ambiente de desenvolvimento**, incluindo os testes legados. Isso não substitui o teste da tela após a atualização no Streamlit Cloud. Mantemos os módulos `historical.py`, `quality_lab.py`, `engine.py`, `backtest.py` e seus testes, sem alterar o código de ordem/execução.

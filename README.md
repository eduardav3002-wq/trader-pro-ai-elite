# ◈ Trader Pro AI Elite v0.9 — pesquisa premium, celular primeiro

**Aplicação Streamlit responsiva para pesquisa histórica do mini-índice WIN**. Motor de regras determinísticas para candles de 5 minutos e confirmação de 15 minutos. **Não é uma IA treinada**, não acessa cotações ao vivo, não se conecta a corretoras, não envia ordens reais, não produz probabilidades comprovadas e não oferece qualquer garantia de rentabilidade. Demonstrações usam preços **totalmente fictícios**.

## 📱 Atualização pelo celular: GitHub + Streamlit Cloud

1. Baixe `Trader_Pro_AI_Elite_v0_9_GitHub.zip` e **extraia o ZIP** com o gerenciador de arquivos do Android.
2. Abra o **mesmo repositório** GitHub já conectado ao Streamlit Cloud. Na raiz, use **Add file → Upload files** (ou o menu equivalente no navegador) para enviar os **12 arquivos extraídos**, substituindo os nomes iguais. **Não envie somente o ZIP sem extrair.**
3. A lista é: `app.py`, `engine.py`, `backtest.py`, `audit.py`, `research.py`, `validation.py`, `requirements.txt`, `test_engine.py`, `test_backtest.py`, `test_research.py`, `test_validation.py`, `README.md`.
4. Confirme em **Commit changes**. O arquivo de entrada da implantação permanece **`app.py`**. Em geral, o Streamlit Cloud atualiza automaticamente o aplicativo publicado no mesmo repositório/branch.
5. Abra o seu link Streamlit já existente e verifique no cabeçalho **RESEARCH TERMINAL · V0.9**. Não é preciso instalar Python, pagar Replit nem criar novo repositório para esse fluxo.
6. Abra **🔐 Dados** e execute **🛡️ Executar autoteste de feriados** (10 verificações previstas). Em seguida, abra **🧬 Robustez** e toque em **Calcular diagnóstico de robustez** para testar a demonstração fictícia.

> Os 32 testes unitários de código passaram no ambiente de desenvolvimento, mas o funcionamento da implantação web deve ser conferido no seu dispositivo depois do commit.

## O que muda na v0.9

- **Visual mobile refinado**: margem superior ampliada para reduzir a sobreposição com a barra fixa do Streamlit, melhor espaçamento nos botões e **cartões verticais** de leitura das metades históricas e da reserva cronológica. Algumas tabelas técnicas detalhadas ainda exigem rolagem horizontal.
- **Separação cronológica fixa de 70%/30% dos pregões completos**: estatísticas líquidas para a parte inicial e a reserva final. A divisão preserva cada sessão inteira, não mistura dados de datas e reutiliza somente as operações produzidas pelo mesmo motor com regras fixas.
- **Diagnóstico de evidência**: status explícito `SIMULAÇÃO — SEM EVIDÊNCIA DE MERCADO` para demonstrações e `EVIDÊNCIA INSUFICIENTE — SOMENTE PESQUISA` para CSVs de origem apenas declarada. Alertas se há menos de 30 pregões no total, 10 na reserva ou 100 operações na reserva, se a reserva não teve operações/saldo positivo ou se perde saldo sob custo adicional.
- **Sensibilidade adicional**: reavalia o saldo da **reserva cronológica** subtraindo mais **10 pontos por operação**, sem alterar preços, stops ou condições de entrada. Os custos normais da simulação já estavam incorporados.
- **Auditoria do backtest**: passa a mostrar uma visão textual de quantos sinais foram bloqueados por regras, limites de risco, horário ou posições em aberto. As explicações detalhadas de candle e o CSV de decisões já existiam no motor; foram preservados.
- **Autoteste B3 expandido para 10 cenários**: inclui agora **09/07/2026, pregão normal**, e **31/12/2026, sem pregão**, além dos oito cenários anteriores.
- **Preservação de lógica v0.8**: o motor EMA/RSI/ATR, grade mínima de 5 pontos, entradas na abertura do candle seguinte, precaução com stop/alvo no mesmo candle, slippage adverso, limites de perda, horário e calendário foram mantidos. **Nenhum parâmetro de sinal foi otimizado para maquiar o resultado anterior da demonstração.**

## Advertência importante sobre “fora da amostra”

A v0.9 cria uma **reserva cronológica retrospectiva**, não um teste prospectivo cego. Se os dados já foram vistos, ou as regras foram alteradas após olhar a reserva, aquela janela NÃO é independente. Um teste verdadeiramente prospectivo exige congelar as regras antes de coletar **dados futuros nunca examinados**; mesmo isso não garante performance real. Sem fonte autenticada e execução testada, **não negociar dinheiro real**.

## Formato de importação

CSV: `datetime,open,high,low,close[,volume]`, candles de **5 minutos**, timestamp de **abertura** em horário de Brasília, preços do contrato WIN na **grade de 5 pontos**, horários válidos, sem duplicatas, lacunas ou candles incompletos para o backtest. No app, é necessário declarar fonte, contrato específico (ex.: `WINZ26`) e confirmar a procedência. Não use uma série contínua como se fosse o mesmo contrato até o vencimento.

O SHA-256 do arquivo registra apenas sua identidade digital, **não comprova autenticidade das cotações**. Um CSV de operações não pode ser usado como CSV de candles.

## Feriados e segurança B3 — somente 2026

No validador de candles, no motor de elegibilidade e no backtest, permanecem bloqueados fins de semana e datas de 2026 sem negociação do WIN, como `2026-11-20`, `2026-12-24`, `2026-12-25` e `2026-12-31`. A Quarta-feira de Cinzas (`2026-02-18`) tem início especial às **13h**. O feriado estadual de São Paulo em **09/07/2026 tem pregão normal**, conforme a B3. No vencimento do contrato específico, o modelo proíbe novas entradas. **Outros anos são rejeitados** até que os respectivos calendários oficiais sejam validados e codificados; mudanças extraordinárias são uma limitação operacional e devem ser checadas na fonte oficial.

Fontes oficiais da B3:

- Calendário anual 2026: https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm
- Carnaval e horário especial: https://www.b3.com.br/pt_br/noticias/confira-o-funcionamento-da-b3-no-carnaval.htm
- Feriado 20/11/2026: https://b3.com.br/pt_br/noticias/confira-o-funcionamento-da-b3-no-feriado-do-dia-nacional-de-zumbi-e-da-consciencia-negra.htm
- Horário de derivativos: https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/

## Testar no computador (opcional)

```bash
pip install -r requirements.txt
pip install pytest
python -m pytest -q
streamlit run app.py
```

**32 testes unitários passaram em 22/11/2026.** Eles cobrem regras, processamento de candles, calendário, backtest, custos, auditoria, robustez e avaliação cronológica. Não demonstram taxa de acerto real. `pytest` não precisa constar nas dependências do Streamlit Cloud.

## Limitações

- Não há IA treinada, nem recomendação ou execução de ordens.
- A demonstração é fictícia; é inválido inferir precisão futura de seus resultados.
- Backtest usa OHLC 5m; sequência de toques dentro do candle e liquidez são desconhecidas. Slippage e taxas são aproximações.
- Holdout cronológico é retrospectivo, sem ajuste automático de regras; não prova teste cego.
- CSV de origem declarada não significa fonte verificada.
- O calendário está restrito ao ano de 2026; mudanças especiais posteriores não são checadas em tempo real.

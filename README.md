# ◈ Trader Pro AI Elite v1.0 — laboratório de histórico WIN

**Visual premium, celular primeiro.** Aplicação Streamlit para estudar, de maneira crítica, sinais e backtests exploratórios do mini-índice WIN usando candles de **5 minutos**. Sem compra/venda real, sem conexão com corretoras, sem feed ao vivo, sem IA treinada e sem promessa de acerto. **Demonstração fictícia NÃO é evidência de mercado.**

## 📱 Instalar a atualização no Android (mesmo GitHub + Streamlit Cloud)

1. Baixe `Trader_Pro_AI_Elite_v1_0_GitHub.zip` e **extraia** no gerenciador de arquivos.
2. Abra o **mesmo repositório** do GitHub conectado ao Streamlit Community Cloud.
3. Escolha **Add file → Upload files** e selecione os **14 arquivos extraídos**, não o ZIP. Substitua os mesmos nomes da versão anterior e adicione `provenance.py` e `test_provenance.py`.
4. Confirme **Commit changes** na branch `main`. A execução continua apontando para **`app.py`**; o aplicativo existente normalmente atualiza após o commit.
5. Abra o link já existente no Streamlit. O cabeçalho deve indicar **RESEARCH TERMINAL · V1.0**.
6. Na tela inicial, escolha **Demonstração fictícia** ou **CSV histórico · origem declarada**. Se não tiver um CSV legítimo, permaneça na demonstração identificada.
7. Em **🔐 Dados**, execute o autoteste de calendário. Em **🧬 Robustez**, clique em calcular diagnóstico e confira a **proporção efetiva** de pregões reservados.

**Não precisa instalar Python ou pagar Replit.** Os testes de código foram feitos pelo desenvolvimento; o resultado visual final depende da implantação no seu Streamlit Cloud.

## O que mudou na v1.0

- **Importação histórica visível na tela principal**: formulário com CSV, fonte declarada, contrato específico (como `WINZ26`) e confirmação explícita de que não é arquivo fictício.
- **Triagem mais rigorosa**: tick de **5 pontos**, OHLC, datas duplicadas, candles exatamente de 5 minutos, cada sessão **completa**, nenhuma lacuna dentro da sessão, **nenhum pregão inteiro omitido** entre as datas inicial/final, datas futuras rejeitadas, ticker do arquivo verificado quando houver coluna, feriados bloqueados.
- **Registros de origem**: relatório baixável JSON com identidade SHA-256 dos bytes, período, fornecedor **declarado**, contrato e ressalvas. Hash **não prova cotações autênticas**.
- **Calendário WIN 2026**: bloqueio obrigatório de fins de semana e feriados sem pregão, abertura especial em **18/02/2026 às 13h**, vencimentos em 2026 e último candle do contrato vencendo corrigido conforme as grades vigentes (até outubro `16:55`, a partir de novembro `17:55`). Em vencimento o motor **não abre novas operações**; não valida anos além de 2026.
- **Divisão cronológica mais clara**: mostra a proporção de reserva **efetiva**, e não só o alvo de 30%; por exemplo, 2 de 4 pregões = **50%** por arredondamento. Sem otimização automática nem alegação de teste cego.
- **Leitura mobile premium** e tentativa de ocultar controles flutuantes do Streamlit dentro da página. A barra de gerenciamento do Streamlit Cloud fora do app pode continuar visível. Tabelas técnicas ainda podem exigir arrastar.
- **41 testes automatizados aprovados** em ambiente local; incluem nove testes novos de integração do CSV, lacunas, datas futuras, declarações, vencimentos e arredondamento da reserva.

## ⚠️ Como conseguir dados históricos legítimos

A v1.0 **não fornece** dados intradiários autênticos, porque não recebeu um arquivo ou feed licenciado de mercado. Obtenha um CSV OHLC de **WIN 5 minutos** numa plataforma/fornecedor habilitado a disponibilizar históricos. Verifique termos de uso, custos e qualidade com o fornecedor. A página pública da B3 de *cotações históricas do mercado à vista* refere-se a outro conjunto de dados: ela **não é** um CSV pronto de candles WIN intradiários.

Formato aceito, com cabeçalho e 1 linha por candle de abertura no horário de Brasília:

```csv
datetime,open,high,low,close,volume,symbol
```

`volume` e `symbol` são opcionais; use `symbol` sempre que possível para conferência. Não invente preços, não use **WIN contínuo** como se fosse contrato específico e não misture meses/vencimentos. O conteúdo precisa incluir todas as barras de **cada pregão inteiro**. Para períodos que cruzam contratos, exporte um contrato por vez. O app rejeita CSVs com dias úteis de pregão omitidos entre começo e fim. **Somente 2026** está coberto pelo calendário que foi codificado; outros anos são bloqueados até revisão das grades.

Os dados enviados pelo navegador são processados no ambiente de hospedagem do Streamlit Cloud; evite carregar conteúdo confidencial se não tiver autorização. A confirmação de fonte é declaração do operador, **não autenticação independente da B3**.

## Regras, limitações e auditoria

- As regras de sinal são EMA 9/21, RSI 14, ATR 14 e tendência de 15 min calculada apenas após fechamento. Filtros seletivos são **hipóteses**; o nome comercial **AI** não significa IA treinada.
- Backtest: abertura do candle seguinte, um trade de cada vez, stop prioritário quando stop e alvo caem no mesmo candle, slippage adverso e custos estimados, limites diários e de risco.
- Preços de toque intrabar, fila de execução, spreads reais, delays, slippage real, custos e ajustes continuam desconhecidos com OHLC 5m. Qualquer backtest é aproximado.
- Divisão temporal 70/30 é **retrospectiva**. Se as regras ou dados foram observados antes da separação, não houve verdadeiro teste cego. Uma reserva positiva, mesmo longa, não autoriza operar com dinheiro real.
- A triagem não verifica se uma plataforma reportou todas as suspensões extraordinárias; consulte sempre comunicados oficiais B3. Calendarização automática de outros anos, conexões a corretoras e qualquer emissão de ordens seguem **desativadas**.
- **NUNCA** trate um arquivo fictício rotulado como “histórico declarado” como evidência: o software valida sua estrutura, não sua verdade externa.

### Fontes oficiais consultadas

- Calendário B3 2026 e Quarta-feira de Cinzas: https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm
- Vencimentos WIN: https://b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/vencimentos/calendario-de-vencimentos-de-contratos-financeiros/
- Grade horária a partir de 09/03/2026 — OC 005/2026-PRE: https://www.b3.com.br/data/files/E3/B2/C2/12/BC09C910F37907C9AC094EA8/OC%20005-2026%20PRE%20NOVOS%20HORARIOS%20DE%20NEGOCIACAO_PT.pdf
- Grade horária a partir de 03/11/2026 — OC 050/2026-VNC: https://www.b3.com.br/data/files/99/B7/82/67/8A631A103BBB511AAC094EA8/OC%20050-2026-VNC%20NOVOS%20HORARIOS%20DE%20NEGOCIACAO_PT.pdf
- Características e tick do WIN: https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm

## Rodar testes localmente (opcional)

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
streamlit run app.py
```

Resultado no desenvolvimento da v1.0: **41 testes passaram**. O sistema continua exclusivamente de pesquisa, com ordens desabilitadas.

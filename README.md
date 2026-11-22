# Trader Pro AI Elite v0.6 — Research Terminal (WIN)

Aplicativo Streamlit para **pesquisa e simulação histórica**. Não há ordens, conexão com corretora, preços em tempo real ou inteligência artificial treinada. Não estima probabilidade de acerto e **não deve ser usado para operar dinheiro real**.

## Atualizar o GitHub pelo celular

1. Baixe e **extraia** o ZIP da v0.6 no celular.
2. No repositório GitHub já conectado ao Streamlit, **substitua os oito arquivos na raiz**: `app.py`, `engine.py`, `backtest.py`, `audit.py`, `test_engine.py`, `test_backtest.py`, `requirements.txt`, `README.md`. **Não envie apenas o ZIP**.
3. Confirme as alterações em **Commit changes**. O arquivo principal continua sendo **`app.py`**. O Streamlit Cloud normalmente republica quando recebe um novo commit.
4. Abra o aplicativo publicado; a faixa do topo deve dizer **V0.6**. Na barra lateral, escolha **Demonstração fictícia** e o perfil **Seletivo v0.6 (experimental)**.
5. Abra **🛑 Não operar** e veja os motivos; depois em **🧪 Backtest** execute a demonstração e baixe o CSV/JSON, se quiser compartilhar para auditoria.

## Mudanças na v0.6

- **Dois perfis separados:** `Base v0.5 (comparação)` e `Seletivo v0.6 (experimental)`.
- O seletivo acrescenta dois filtros a EMA 9/21, RSI 14, ATR 14, confirmação 15m e rompimento de três candles. **Os valores abaixo são hipóteses arbitradas para programação**, não calibradas em WIN real:
  - `ATR atual / mediana dos 60 ATR anteriores` entre **0,65 e 1,80**;
  - `amplitude do candle / ATR atual` no máximo **2,20**;
  - período de aquecimento de **75 candles** antes de sinalizar.
- **Motivo de não operar para cada candle:** tendência divergente, RSI fora da faixa, lateralização, volatilidade, rompimento ausente, aquecimento, etc. Disponível em uma nova aba e CSV exportável.
- **Travas opcionais de risco para a simulação:** risco estimado do stop por operação, relação risco/retorno mínima e pausa no restante do dia após N perdas consecutivas realizadas. O limite de perda diária preexistente também usa apenas perdas **realizadas**, nunca garante que uma perda individual será limitada. Gaps, leilões e execução real podem gerar perdas maiores.
- **Auditoria das entradas:** mostra cada sinal candidato e por que entrou ou foi rejeitado no backtest (risco excessivo, entrada tardia, posição aberta, trava diária etc.). Exporta CSV mesmo quando não há operação.
- **Relatórios v0.6:** operações, auditoria de entradas e JSON com perfil, parâmetros e proveniência. Mantida a marcação inequívoca de dados fictícios.
- **Terminal histórico:** evita mostrar uma ordem executável quando o último candle não pode ter uma entrada no próximo candle do pregão (por horário). Não existe fluxo ao vivo.

**Nenhum desses controles demonstra maior acerto.** Na demonstração fictícia padrão, com as travas extras ativadas, o seletivo teve **7 operações e −179 pontos**, enquanto a regra-base nas mesmas travas teve **8 operações e −106 pontos**. Esse exercício serve para verificar o funcionamento dos bloqueios, **não** para medir qualidade da estratégia.

## CSV de dados históricos (se obtidos legalmente)

Colunas: `datetime,open,high,low,close,volume` (volume opcional), um candle por linha de cinco minutos. `datetime` é o **início** do candle no horário de Brasília, por exemplo `2026-11-19 09:00:00`. Se houver coluna `ticker`/`symbol`/`contrato`, seus valores devem bater com o contrato declarado, como `WINZ26`.

Somente **dados de 2026 e de um contrato específico** são aceitos nesta versão. Exige preços na grade de cinco pontos, OHLC coerente, sequência cronológica, sessão regular válida e, para executar backtest, **cada sessão completa**. Contrato contínuo/ajustado não substitui o vencimento específico. No vencimento, esta versão exclui novas operações. Não suporta automaticamente todas as exceções de sessões, leilões ou vencimento; **a validação não autentica preços**. O código não baixa cotação, não contorna serviços pagos nem verifica direitos de uso. Arquivos fictícios podem passar por requisitos estruturais.

## Testes locais

```bash
pip install -r requirements.txt
python -m pytest -q test_engine.py test_backtest.py
streamlit run app.py
```

As bibliotecas de testes e Streamlit são necessárias para executar os comandos; o arquivo `requirements.txt` contém as dependências do aplicativo. Os testes de unidade usam dados sintéticos e avaliam somente a integridade do código. O backtest usa candle seguinte, preenchimento simplificado (tick/slippage constantes), stop prioritário se stop e alvo forem tocados na mesma vela, 1 posição por vez, horário limite, zeragem intradiária e custos aproximados. Ordens reais seguem **desabilitadas**.

## Próximas tarefas

Obter candles reais de fornecedor autorizado e identificar a fonte, validar regras oficiais de sessões/vencimentos, testar múltiplos períodos fora da amostra, considerar custos e execução reais e incluir análise de incerteza. Não otimizar métricas em cima de demonstração inventada.

**Referências B3 para conferir quando usar dados reais:**

- https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm
- https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/
- https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm

# ◈ Trader Pro AI Elite v0.8 — pesquisa premium, celular primeiro

Aplicação **Streamlit** responsiva de pesquisa retrospectiva de sinais de **WIN, intraday, candles de 5 minutos com confirmação de 15 minutos**. O projeto usa **regras determinísticas**, **não é uma IA treinada**, não obtém cotações em tempo real, não se conecta à B3 nem a corretoras, **não envia ordens reais** e **não oferece qualquer garantia de lucro ou de taxa de acerto**.

## 📱 Atualização pelo celular (GitHub + Streamlit Cloud)

1. Faça o download de **`Trader_Pro_AI_Elite_v0_8_GitHub.zip`** e use o gerenciador de arquivos do celular para **extrair o ZIP**.
2. Abra seu repositório atual no GitHub. Use **Add file → Upload files** (ou a interface equivalente de upload pelo navegador) e selecione os **10 arquivos extraídos**. Substitua arquivos de mesmo nome na **raiz** do repositório. **Não envie o ZIP fechado** em vez dos arquivos.
3. Os arquivos são `app.py`, `engine.py`, `backtest.py`, `audit.py`, `research.py`, `requirements.txt`, `test_engine.py`, `test_backtest.py`, `test_research.py`, `README.md`. Não precisa criar novo repositório se o atual já está publicado.
4. Toque em **Commit changes**. Sua publicação existente no Streamlit Cloud deve continuar com **arquivo de entrada `app.py`** e será atualizada quando detectar o commit.
5. Abra o link já existente do aplicativo no navegador do celular. No topo, confirme **`RESEARCH TERMINAL · V0.8`**.
6. No aplicativo, abra **🔐 Dados → 🛡️ Executar autoteste de feriados** e confira se os **8 cenários** foram aprovados. Depois, abra **🧬 Robustez** e execute o diagnóstico da demonstração fictícia.

Caso o deploy não atualize, verifique se o repositório e a branch ainda estão conectados ao Streamlit Cloud e se `research.py` foi enviado. **O teste do deploy web precisa ser feito no Streamlit Cloud**; os testes de código locais não substituem a verificação da interface em um navegador.

## O que muda na v0.8

- **Identidade visual premium**: nova paleta violeta/azul-marinho, cartões compactos, botões acessíveis e melhorias de layout para tela de celular, sem exigir instalação de aplicativo nativo.
- **Nova aba 🧬 Robustez**: resume saldo líquido, taxa histórica, drawdown, compara a *primeira metade* e a *segunda metade* dos pregões, e simula mais 0/5/10/20 pontos de custo **extra** por operação sobre o mesmo histórico de operações. A comparação de metades não é um verdadeiro teste fora da amostra; a análise de custo não refaz entradas, stops ou execução.
- **Autoteste visível ampliado de 4 para 8 cenários**: pregão autorizado, 20/11/2026 feriado, sábado, 2027 sem calendário, Quarta-feira de Cinzas antes/depois de 13h, vencimento do WINM26 e feriado de 24/12.
- **Backtest, auditoria e motor seletivo preservados** da v0.7. Não foram ajustados os filtros com base nos resultados fictícios nem removidas travas para forçar sinais.
- **Avisos de amostra pequena e de falta de evidência**: não confundir taxa histórica em dados artificiais ou em CSV não autenticado com previsão ou vantagem real.

## Fonte de dados aceita

Formato CSV: `datetime,open,high,low,close[,volume]`. Timestamps representam **abertura do candle de cinco minutos em horário de Brasília**. Os preços devem estar no **tick de cinco pontos**, em sequência cronológica, sem lacunas ou valores inconsistentes. Para backtest, são obrigatórios **pregões completos**. Declare fonte e vencimento específico (exemplo: `WINZ26`), nunca uma série contínua em nome de um contrato com vencimento específico.

Se o CSV contiver `ticker`, `symbol`, `ativo`, `contract` ou `contrato`, os símbolos devem concordar com o contrato declarado. A declaração de fonte **não prova a autenticidade** do histórico; o SHA-256 identifica apenas bytes carregados. O CSV de operações de uma versão antiga NÃO é CSV de candles.

## Travas obrigatórias de negociação da B3

- Feriados fechados de 2026, incluindo `2026-11-20`, `2026-12-24`, `2026-12-25`, `2026-12-31`; além de fins de semana.
- Em 18/02/2026, abertura especial às **13h**; entradas anteriores são bloqueadas.
- Entradas bloqueadas no dia de vencimento do contrato específico. Sem entrada depois de 17h55 ou sem próximo candle disponível.
- O código **falha fechado em 2027 e outros anos sem calendário oficial codificado/testado**; não presumir que todo dia útil seja pregão.
- Todos os bloqueios são aplicados na validação de candles, elegibilidade de sinal, auditoria e backtest. O calendário codificado segue a referência 2026 e pode não abranger ocorrências extraordinárias posteriores.

Fontes oficiais: 
- Calendário B3 2026: https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm
- Horários de índices e WIN: https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/horario-de-negociacao/derivativos/indices/
- Vencimentos: https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/vencimentos/calendario-de-vencimentos-de-contratos-financeiros/

## Testes

```
pip install -r requirements.txt
python -m pytest -q test_engine.py test_backtest.py test_research.py
streamlit run app.py
```

**24 testes unitários locais passaram em 22/11/2026**. Estes testes cobrem o motor, backtest, calendário e estatísticas do novo laboratório; não demonstram desempenho real e não substituem a execução no Streamlit Cloud. `pytest` é necessário para rodar os testes localmente, mas não é obrigatório como dependência de produção do aplicativo.

## Limites importantes

As ordens ficam desativadas, inclusive na demonstração. Slippage e taxas são aproximações, os preços da demonstração são **100% sintéticos**, resultados podem ser negativos e nenhum modelo de probabilidade ou inteligência artificial está treinado. Manter em modo de pesquisa até se obter dados verificados, custos realistas, controles independentes e avaliação prospectiva fora da amostra.

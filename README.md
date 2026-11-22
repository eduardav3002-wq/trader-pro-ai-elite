# ◈ Trader Pro AI Elite v1.6 — Comparação matemática de preços

**WIN intraday · Streamlit mobile-first · pesquisa, sem ordens reais · 126 testes de código.**

## O que foi acrescentado

Novo módulo `cross_price_lab.py` e testes em `test_cross_price_lab.py`. Na aba **🧾 Fonte M1**, depois de importar CSV/TSV com ticker, a seção **🔍 Validação cruzada de preços · v1.6** apresenta:

- **Diferença ajustado − original para cada OHLC M1**, incluindo mínimos, máximos e eventos de divergência entre os quatro campos.
- Comparação com coluna opcional `Ajuste`, quando presente; se o ajuste declarado não coincidir com a diferença calculada, gera alerta.
- Classificação do modelo observado: `ADITIVO_CONSTANTE_NA_AMOSTRA`, `ADITIVO_CONSTANTE_POR_CONTRATO_DIA`, `AJUSTE_VARIAVEL_INTRADIA`, `DIVERGENCIAS_NA_TRANSFORMACAO` ou `SEM_SERIE_AJUSTADA`.
- **Mudanças entre minutos consecutivos**, dentro do mesmo ticker e pregão: não compara através de buracos, vencimentos, nem entre dias.
- **Comparação das séries M5 agregadas separadamente**: sinaliza se os valores OHLC já agregados não diferem por uma translação uniforme de preço.
- Exportação de resumo JSON, comparação por dia CSV, eventos CSV, comparação M5 CSV.
- Conferência opcional do SHA-256 contra o JSON de laudo da v1.5. Hash igual **não confirma origem, ticker, corretora, licenças nem autenticidade**.

**IMPORTANTE:** isto compara séries dentro do MESMO ARQUIVO; não constitui verificação cruzada com uma segunda fonte independente e NÃO reconstrói o preço de negociação, nem certifica metodologia de rolagem.

### Exemplo explicado — apenas para interpretar a ferramenta

O laudo compartilhado do exemplo WINZ22 de 31/10/2022 (v1.5) registra 532 minutos M1, 106 M5 completos, dois minutos sem grupo M5, nenhum salto interno e diferença mínima/máxima de +63.385 pontos. Esses valores são registros do **laudo v1.5, não validação independente**. Na v1.6, ao reenviar o CSV de origem, os cálculos serão refeitos candle a candle. Sem esse arquivo, não é possível afirmar que a nova análise foi executada em seus 532 candles.

## Passo a passo pelo Android

1. Faça backup do repositório se desejar. Baixe e **extraia o ZIP** da v1.6.
2. No repositório GitHub existente (branch `main`), envie os **26 arquivos extraídos para a raiz** e substitua os arquivos anteriores. Não suba o arquivo ZIP no lugar do código.
3. Confirme **Commit changes**. No Streamlit Cloud, aguarde a implantação completar (e confira os logs em caso de erro). Não é necessário pagar Replit.
4. Abra o mesmo endereço do aplicativo e confirme **RESEARCH TERMINAL · V1.6**.
5. Selecione **🧾 Conferir CSV com ticker · SEM backtest** e importe novamente o arquivo original `WINZ22_M1_2022-10-31.csv` que você baixou no celular. Declare a fonte e o fuso corretamente — se o fuso não é conhecido, mantenha *Desconhecido*.
6. Abra **🧾 Fonte M1** e role até **🔍 Validação cruzada de preços · v1.6**.
7. Opcional: em **Conferir identidade com laudo anterior v1.5**, envie `laudo_fonte_win_v15.json`. Ele compara apenas o SHA-256 dos bytes do CSV, não os preços contra bolsa ou outra fonte.

## Segurança e limitações

- O módulo é **descritivo**; não cria sinais, retornos de trades, previsões ou backtests.
- **0 dias certificados, backtest não liberado, nenhuma ordem real.** Não alterar esses controles com base apenas em consistência matemática.
- Os preços `Open_Adj/...` são mantidos separados dos campos `Open/...`; jamais são utilizados como preços executáveis.
- Não preenche M1 ausentes e não atravessa pausas, mudanças de ticker ou sessões para comparar retornos M1.
- Verificação de vencimentos, feriados e horários oficiais requer fonte independente. O calendário 2026 do motor permanece preservado.
- A v1.6 não autentica a B3, não valida licença de cotações e não possui integração com corretora.
- Os testes verificam o código de regras, não execução no Streamlit Cloud: **o Streamlit não está instalado no ambiente de teste local**. Confira a nova aba no celular após publicação.

## Testes de código

```bash
python -m pytest -q
```

**126 testes aprovados** no pacote atual. Para inspecionar somente a nova unidade: `python -m pytest test_cross_price_lab.py -q` (10 testes).

---

## Documentação anterior — v1.5 (recursos preservados)

# ◈ Trader Pro AI Elite v1.5 — Laboratório de Fonte M1

**WIN intraday · Streamlit responsivo · sem ordens reais, sem IA treinada e sem previsão garantida.**

## Atualizar pelo Android

1. Extraia `Trader_Pro_AI_Elite_v1_5_GitHub.zip` no telefone.
2. No GitHub do mesmo projeto, envie **os 24 arquivos extraídos**, diretamente para a **raiz** do repositório, substituindo os existentes. Não envie o ZIP como um único arquivo.
3. Confirme o commit na `main`, depois abra seu Streamlit. O arquivo de entrada continua `app.py`.
4. Confira `RESEARCH TERMINAL · V1.5` no topo. Se demorar, aguarde apenas o carregamento normal do site e verifique logs de deploy em caso de erro.
5. Para o novo módulo, selecione **🧾 Conferir CSV com ticker · SEM backtest**, carregue o arquivo M1, declare fonte e fuso, e abra a aba **🧾 Fonte M1**.

## Por que esta versão?

Encontramos uma **amostra pública de um dia**, intitulada `WINZ22_M1_2022-10-31.csv`, com coluna `Contrato=WINZ22`, preços originais `Open/High/Low/Close` e preços ajustados `Open_Adj/...`. Isso é mais rico em metadados do que o CSV contínuo 2019–2020, mas **a identificação continua declarada pelo arquivo, não autenticada independentemente**. Uma única sessão não valida rentabilidade.

Fonte externa consultada (baixe no seu celular pelo botão **Raw**, se desejar):
https://gist.github.com/alcindogandhi/0aa56106c3e374c344569b55facbf9d3

Não redistribuímos esse arquivo público no pacote. O autor não documenta nesta página a origem primária das cotações nem o fuso.

## Novo módulo `source_lab.py`

- Lê CSV/TSV UTF-8 com `Datetime,Contrato,Open,High,Low,Close`, opcionalmente `DataReferencia`, `Volume`, `Open_Adj`, `High_Adj`, `Low_Adj`, `Close_Adj`, `Ajuste`.
- Exige **ticker individual** (ex.: `WINZ22`); rejeita data/hora inválida, duplicação por minuto/contrato, linhas fora de ordem, OHLC inconsistente e preços fora da grade de 5 pontos.
- Conta faltas dentro dos registros e avisa se registros declarados aparecem após vencimento nominal; não valida automaticamente horário oficial ou pregão completo.
- Se houver os quatro campos ajustados, mantém séries **originais e ajustadas distintas** e verifica inconsistências na diferença. Ajuste observado não é evidência de rolagem.
- Constrói candles de 5 minutos **somente com 5 minutos consecutivos completos**, sem preencher janelas parciais. Exportação rotulada EXPLORATÓRIA, nunca certificada.
- Entrega resumo JSON, relatório diário, lacunas M1 e M5 exploratório. Nenhuma dessas saídas alimenta sinais/backtest nesta versão.
- A fonte e o fuso são declarações; o SHA-256 identifica os bytes recebidos, mas **não autentica cotações**.

Amostra externa e saída do módulo **NÃO são suficientes para operações**, e não substituem a investigação do histórico 2019–2020. Mantenha os modos anteriores da v1.4.

## Estado de segurança

**0 pregões certificados na nova fonte; backtest NÃO liberado e ordens NÃO habilitadas.** O bloqueio obrigatório dos feriados da B3 de 2026 continua inalterado no motor existente. Para validar outro ano, seria necessário conferir seu calendário, sessões, tickers e origem de maneira independente.

## Testes

**116 testes automatizados aprovados** no pacote v1.5; isso não comprova desempenho ou funcionamento do site publicado. O Streamlit não estava instalado neste ambiente de construção e precisa ser conferido na implantação real.

---

## Histórico: laboratório de rastreabilidade v1.4

# ◈ Trader Pro AI Elite v1.4 — Rastreabilidade dos dados (funcionalidade preservada)

**Aplicativo experimental para pesquisa de mini-índice WIN, com interface Streamlit responsiva para celular.**

A versão 1.4 amplia os laboratórios de qualidade (v1.2) e integridade (v1.3) com um **dossiê de rastreabilidade** de séries 2019–2020. Não possui IA treinada, acesso a mercado ao vivo, execução de ordens nem resultados de mercado comprovados. **A análise exploratória não produz sinais ou backtests**.

## Atualização pelo Android — GitHub + Streamlit Cloud

1. Baixe o ZIP `Trader_Pro_AI_Elite_v1_4_GitHub.zip` e **extraia** no celular.
2. No mesmo repositório usado pelo Streamlit: **Add file → Upload files** e selecione os **22 arquivos extraídos na raiz**, substituindo arquivos com o mesmo nome. **Não envie o ZIP** como se fosse código.
3. Confirme **Commit changes** na branch `main`. O arquivo principal permanece `app.py`.
4. Abra o mesmo endereço da aplicação Streamlit e confira **RESEARCH TERMINAL · V1.4**.
5. Escolha **🔬 Explorar 2019–2020 · SEM backtest** e carregue o arquivo local `WIN_2019_2020_5min_exploratorio.csv` (ou o original de 1 minuto) na interface; **não publique dados de terceiros no repositório**.
6. Na aba **🔬 Histórico**, veja o novo painel **🧾 Rastreabilidade dos dados · v1.4**, seguido pelas seções de integridade v1.3 e qualidade v1.2.
7. Opcionalmente, baixe o modelo CSV vazio de contratos na própria interface. **Só preencha datas, tickers e referências que você tenha como documentar.** Um contrato presumido a partir de preço, mês ou calendário é apenas palpite e deve permanecer não informado.

## O que faz a v1.4

O módulo `traceability_lab.py` oferece:

- **Dossiê da entrada** com nome, origem *declarada* pelo usuário e hash SHA-256 dos **bytes recebidos**. O hash detecta diferenças de bytes entre arquivos comparados, mas não prova que os dados vieram da B3.
- **Mapa opcional de contratos declarados**, usando `inicio,fim,contrato,documento` com datas `AAAA-MM-DD`, intervalo não sobreposto e códigos `WIN[G/J/M/Q/V/Z][ano com dois dígitos]`. O campo `documento` é texto/URL fornecido pelo usuário, **não uma comprovação automática**. Se o CSV estiver incorreto, ele é rejeitado antes da análise.
- **Análise de vencimentos NOMINAIS**, segundo a quarta-feira mais próxima do dia 15 dos meses pares. Se uma atribuição cruzar essa data, gera um aviso investigativo; NÃO determina o último negócio, a real negociação ou as regras excepcionais daquele período.
- **Fronteiras entre pregões**: separa `TICKER_INDETERMINADO`, `MESMO_TICKER_ALEGADO_SEM_AUTENTICACAO` e `MUDANCA_DECLARADA_NAO_COMPROVADA`. As diferenças de preço são mostradas ao lado, mas **não confirmam rolagem**.
- **Lista de pendências de evidência**: fornecedor primário, ticker por candle, critérios de rolagem, fuso, abertura/encerramento, explicação das lacunas, licença dos dados.
- **Relatórios para download**: rastreabilidade por dia (CSV), fronteiras entre pregões (CSV), pendências (CSV) e dossiê (JSON).
- **Layout mobile** com cartões e filtros limitados a poucos registros na tela, preservando toda a análise nos arquivos CSV/JSON.

### Modelo de contrato (opcional)

O download na aplicação traz **somente o cabeçalho**:

```csv
inicio,fim,contrato,documento
```

Para informar uma hipótese, o campo `documento` deve conter a referência disponível e a fonte ainda precisa ser verificada independentemente. **Não invente datas de rolagem nem reutilize o exemplo de ticker como evidência.** Um mapa preenchido NUNCA muda `backtest_liberado` para verdadeiro.

### Resultado do arquivo público analisado

| Item | Valor |
|---|---:|
| Dias com candles | 181 |
| Fronteiras entre pregões | 180 |
| Dias com ticker comprovado | **0** |
| Dias com ticker alegado sem mapa adicional | 0 |
| Dias sem ticker informado no dossiê atual | 181 |
| Origem primária confirmada | **Não** |
| Dias certificados para backtest | **0** |

O arquivo público **não contém ticker por candle** e não informa os critérios de formação da série. A presença de preços 2019–2020 e de datas nominais de vencimento **não permite identificar automaticamente os contratos negociados**.

## Segurança e limitações

- Esta aplicação não gera ordens, nem habilita automação de execução.
- O modo **2019–2020** nunca chama `analyze` ou `backtest` e não promove informações declaradas a autenticadas.
- O modo histórico rigoroso de **2026** é mantido sem alterações de calendário; exige arquivo e contrato individual conforme validação anterior.
- Os avisos de 2019–2020 não corrigem lacunas, não ajustam preços, não atribuem contratos e não inferem eventos de mercado com base em saltos.
- Mesmo o melhor dia da série permanece **não certificado**, inclusive com mapa preenchido ou referência informada pelo usuário.
- Os parâmetros de preço destacados na v1.3 são percentis descritivos calculados sobre a própria amostra. Não são teste independente, prova de erro ou estratégia lucrativa.
- Os horários de encerramento por data, eventuais suspensões, ticker real, direitos de uso, política de emenda/ajuste e origem primária **não foram auditados externamente**.
- Quando novos dados autenticados forem obtidos, será necessário criar uma **etapa separada de validação**, não simplesmente liberar o bloqueio atual.

## Fontes externas de referência (não autenticam a amostra)

- [B3 — especificações atuais do futuro mini de Ibovespa](https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/futuro-mini-de-ibovespa.htm)
- [B3 — calendário de 2019](https://www.b3.com.br/data/files/F8/B3/88/A0/33E97610F157B776AC094EA8/CL%20049-2018_EN_VOP%20Feriados%202019_v7%20R_2.pdf)
- [B3 — calendário de 2020](https://www.b3.com.br/data/files/97/C7/BB/E1/F50BF6109A4874F6AC094EA8/OC%20003-2020-VOP%20Feriados%202020.pdf)
- [B3 — exceções de funcionamento em 2020](https://www.b3.com.br/pt_br/noticias/funcionamento-da-b3-8AE490C97215B74E0172959F18F11323.htm)
- [GitHub — FGV_Trabalho_WIN, origem secundária do arquivo público](https://github.com/BernardoAflalo/FGV_Trabalho_WIN)

As especificações atualmente publicadas pela B3 são usadas como referência geral e **não comprovam condições contratuais históricas em cada sessão**.

## Testes locais (opcionais; você não precisa executar no celular)

```bash
pip install -r requirements.txt
pip install pytest
pytest -q
streamlit run app.py
```

**101 testes automatizados passaram em 22/11/2026**, incluindo a suíte anterior. O ZIP foi extraído e testado novamente. Isso verifica regras do código e consistência dos arquivos, **não comprova a interface em produção nem desempenho financeiro**.

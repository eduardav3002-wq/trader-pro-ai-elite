# ◈ Trader Pro AI Elite v2.3 — Auditoria de slippage operação a operação

**Atualização:** 23/11/2026 — pesquisa do WINZ26, sem ordens reais, sem IA treinada, sem certificação independente de origem dos preços.

## O que mudou

- Após escolher **Amostra pública B3 · WINZ26**, entre em **Backtest**, toque **Comparar limites de risco · Seletivo** e abra **🔍 Auditoria das diferenças · v2.3**.
- O app guarda o resultado da comparação na sessão, inclusive depois de tocar nos botões de download.
- Agora compara cada operação pelo **candle que originou o sinal**, nos cenários de 1, 2 e 3 ticks de slippage por lado, para 125, 175, 250 e 500 pontos de risco por operação.
- Mostra quantidade de operações comuns, operações removidas ou acrescentadas, o **motivo do bloqueio**, e se o preço, motivo ou candle de saída mudou.
- Decompõe variação do saldo líquido em **mudança do resultado bruto** (efeito das saídas e da seleção) e **mudança do total de custos** (taxa + slippage). Quando operações deixam de existir, a decomposição inclui também os custos e resultados das operações excluídas; portanto, não confundir com custo puro de execução para uma amostra fixa de trades.
- Exporta três novos CSVs: comparações pareadas, detalhes por operação e todas as operações dos cenários.
- **Não modifica** sinal, calendário 2026, filtro de feriados, valores predefinidos, gerenciamento de risco, nem metodologia de validação futura v2.2.

## O que encontramos na amostra de 10–19/11/2026

- **Limite 250**, slippage 1 → 3 ticks/lado: resultado líquido **+682 → +262 pts**; queda de **420 pts**, dos quais **340 pts** na mudança dos resultados brutos/saídas e **80 pts** em custos adicionais. As mesmas **4 operações** foram executadas, mas duas mudaram de tipo de encerramento.
- Em **12/11**, a venda do candle-sinal 314 deixou de atingir o alvo e saiu por tempo: **+298 → +93 pts** (1 → 3 ticks).
- Em **13/11**, a compra do candle-sinal 441 passou de saída no fim do pregão para stop: **−7 → −192 pts** (1 → 3 ticks).
- **Limite 175**, slippage 1 → 3 ticks/lado: resultado **+31 → +188 pts**, porque a operação perdedora de 13/11, candle-sinal 444, deixou de ocorrer por **RISCO_OPERACAO_EXCEDIDO**. Isso não prova robustez a custos.
- **Limite 500**, slippage 3 ticks/lado: **+486 pts** líquidos, mas **1.062 pts** de rebaixamento máximo. O limite de perda diária é somente sobre perdas **já realizadas**, podendo uma operação perder mais que 200 pts.
- Os resultados continuam **exploratórios, não independentes e insuficientes para operar**. Nenhuma configuração foi escolhida como ótima; 250 pts permanece apenas candidato a investigação.

## Instalar no celular pelo GitHub

1. Extraia o arquivo `Trader_Pro_AI_Elite_v2_3_GitHub.zip` no celular.
2. Envie **todos os arquivos extraídos**, não o ZIP fechado, à **raiz** do repositório GitHub usado pelo Streamlit Cloud. Substitua arquivos de mesmo nome, preservando o entrypoint `app.py`.
3. Confirme as alterações (Commit changes) e recarregue o app; o cabeçalho deverá exibir **RESEARCH TERMINAL · V2.3**.
4. Selecione **Amostra pública B3 · WINZ26** → **Backtest** → **Comparar limites de risco · Seletivo** → **🔍 Auditoria das diferenças · v2.3**.
5. Faça download do CSV **Operação a operação** e compare especialmente os cenários de 250 pts.

A avaliação em pregões novos só começará quando dados M5 autênticos, completos e subsequentes à amostra histórica forem importados. A declaração de origem não é certificação. O motor bloqueia feriados e fins de semana de 2026; não alterar esses controles.

---

# Trader Pro AI Elite v2.2 — Avaliação futura auditável e teste de estresse

**Objetivo:** analisar apenas pregões inéditos do WINZ26 sem ajustar parâmetros aos resultados novos. O app é ferramenta de pesquisa e não envia ordens. Não possui IA treinada, integração com corretoras ou garantia de retorno.

## Novidades da v2.2

- Na fonte **Amostra pública B3 · WINZ26**, abra **Backtest → 🔬 Validação futura + estresse · v2.2**.
- A data do primeiro pregão posterior a 19/11/2026 é **23/11/2026**, pois 20/11 foi feriado e 21–22/11 foram fim de semana. O CSV deve conter pregões completos, fechados e consecutivos, sem pular dias negociados.
- O CSV deve ser UTF-8 e conter `datetime,open,high,low,close,contrato` (ou `symbol`, `ticker`, `ativo` ou `contract`), com o mesmo ticker `WINZ26` em todas as linhas. `volume` opcional. Datas são aberturas de candles M5 em Brasília; dados fictícios não são permitidos para validação financeira.
- O aquecimento continua usando os oito pregões de 10 a 19/11. **Nenhuma operação dessa amostra é somada ao resultado dos pregões novos.**
- A comparação **na amostra já conhecida** mostra agora o estresse com 1, 2 e 3 ticks por lado, para identificar sensibilidade antes de receber pregões novos. Não é validação futura.
- Cenários congelados para risco por operação de **125, 175, 250 e 500 pts**, taxa fixa de **2 pts por operação completa**, slippage base de **1 tick (5 pts) por lado** e limites da v2.0.
- Teste de estresse reexecuta a estratégia com **1, 2 ou 3 ticks de slippage por lado**. Como risco e razão ganho/perda mudam, o número de operações também pode mudar. O cenário não é mera subtração de pontos após os trades.
- Tela com resumo, lucro/prejuízo por dia (inclusive dias sem operações), operações detalhadas e cinco downloads: 4 CSVs e um recibo JSON com hash SHA-256 de entrada, datas, fonte **declarada** e parâmetros imutáveis.
- Se forem importados menos de 20 pregões inéditos, o app avisa que a amostra é curta. Mesmo com mais pregões, nenhuma validação independente de origem nem desempenho futuro é presumida.

### Fluxo pelo celular (Android/GitHub)

1. **Extraia** `Trader_Pro_AI_Elite_v2_2_GitHub.zip`.
2. Envie os arquivos extraídos à raiz do repositório GitHub que já hospeda o app. Substitua arquivos de mesmo nome; **não envie apenas o ZIP**.
3. Confirme o commit na branch ligada ao Streamlit Cloud e atualize o aplicativo. A identidade deve exibir `RESEARCH TERMINAL · V2.2`.
4. Em **📁 Escolha como analisar**, toque em **Amostra pública B3 · WINZ26**; depois abra **Backtest** e a seção **🔬 Validação futura + estresse · v2.2**.
5. Se ainda não possuir CSV de pregões posteriores completos, não invente dados; continue testando a amostra interna ou a interface. O app não baixa dados B3 sozinho.
6. Depois de obter CSV com acesso autorizado, exporte os cinco arquivos de auditoria. O recibo permite identificar o arquivo exato e os parâmetros usados, mas **não autentica a fonte**.

### Limitações metodológicas

Os quatro limites já foram analisados nos oito pregões anteriores: portanto, o conjunto não é prova independente de otimização. A comparação futura continua exploratória e deve ser interpretada com cautela contra seleção do melhor resultado, custos, risco intrabar, gaps, mudanças de regime e possível inadequação dos horários. Não operar dinheiro real com base nesta pesquisa. O bloqueio de feriados B3 de 2026, fins de semana e anos fora do calendário validado permanece obrigatório.

---

# Trader Pro AI Elite v2.1

Na amostra pública B3, abra **Backtest → Validar em pregões novos**.
Envie um CSV M5 do WINZ26 com colunas datetime, contrato, open, high, low, close e volume opcional. O horário é o de abertura do candle em Brasília. Envie pregões completos e consecutivos começando pelo próximo pregão após 19/11/2026. Feriados e fins de semana seguem o calendário do motor.

Os oito pregões incluídos são o histórico inicial dos indicadores. Operações, saldo líquido e rebaixamento máximo da validação consideram somente entradas nos pregões novos. Os quatro limites e os demais parâmetros são compartilhados com a comparação fixa da v2.0. O CSV carregado tem fonte declarada e passa pela validação estrutural do motor.

## Histórico da v2.0

# Trader Pro AI Elite v2.0

Extraia o ZIP e envie os arquivos à raiz do repositório do Streamlit.
No app, selecione **Amostra pública B3 · WINZ26** e abra **Backtest → Comparar limites de risco · Seletivo**.

A amostra exploratória contém oito pregões (10, 11, 12, 13, 16, 17, 18 e 19/11/2026) e 904 candles M5 de abertura das 09:00 às 18:20. Os preços e totais da sessão, antes do recorte, foram comparados com o consolidado diário da B3. Nos dias 11 e 12, os negócios registrados de 09:02 a 09:04 formam o candle rotulado 09:00.

A comparação fixa testa 125, 175, 250 e 500 pontos por operação. O padrão do backtest individual segue em 125 pontos. Os resultados desta amostra são exploratórios. Pregões posteriores serão necessários para avaliar os mesmos cenários fora da amostra.

[Boletim Diário da B3](https://arquivos.b3.com.br/bdi/tabelas?lang=pt-br)

## Histórico da versão anterior

# ◈ Trader Pro AI Elite v1.8 — Diagnóstico detalhado de divergências

**WIN intraday · Streamlit mobile-first · sem ordens reais · sem backtest validado neste laboratório**

## Novidade da v1.8

A v1.8 adiciona `discrepancy_lab.py` e `test_discrepancy_lab.py`, preservando os módulos da v1.7. Na aba **🧾 Fonte M1**, depois que duas fontes A e B forem carregadas, a seção **🔎 Diagnóstico de divergências · v1.8** detalha:

- Número de minutos em comum, exclusivos de A ou B, e com diferenças de preços OHLC originais;
- Para cada campo OPEN, HIGH, LOW, CLOSE: quantidade de divergências e maior/mediana diferença absoluta;
- Faixas consecutivas de minutos presentes só em um CSV (não prova que faltou negócio no mercado);
- Eventos categorizados como `OHLC_DIVERGENTE`, `VOLUME_DIVERGENTE`, `AUSENTE_A` e `AUSENTE_B`, com filtro e exportação;
- Alerta **descritivo** de deslocamento constante entre OHLC A e B (não é evidência suficiente de rolagem e nunca corrige os valores);
- Quatro downloads separados: laudo JSON, diagnóstico por OHLC CSV, faixas exclusivas CSV e até 500 eventos CSV; números totais calculados sobre os arquivos completos.

### Autoteste seguro e gratuito, sem segunda fonte

A tela também traz **🧪 Autoteste de divergências · v1.8** com botão `🔬 Executar autoteste sintético (sem upload)` e downloads de dois CSVs artificiais A e B. **Estes arquivos foram inventados para desenvolvimento e NÃO contêm cotações reais da B3**. O teste esperado:

| Verificação no autoteste | Esperado |
|---|---:|
| Minutos em comum A/B | 19 |
| Minutos com preços OHLC diferentes | 2 |
| Minutos exclusivos de A | 1 |
| Minutos exclusivos de B | 1 |
| Minutos com volume diferente | 1 |
| Total de eventos | 5 |
| Pregões certificados | 0 |

A v1.8 reutiliza a validação de ticker individual e preço de 5 pontos. Não mistura séries ajustadas e originais, não supõe fuso, não inventa candles ausentes, não alinha relógios, não corrige divergências e não interpreta deslocamentos de preços como rolagens comprovadas.

### Publicar no Android via GitHub

1. Extraia `Trader_Pro_AI_Elite_v1_8_GitHub.zip`. O arquivo contém **30 arquivos** de código, testes e instruções; envie todos à **raiz** do repositório que já alimenta o Streamlit, substituindo os nomes iguais. Não envie o ZIP inteiro como se fosse código.
2. Confirme **Commit changes** na branch usada pelo Streamlit. O entrypoint continua `app.py`.
3. Abra o aplicativo e confirme `RESEARCH TERMINAL · V1.8`.
4. Selecione **🧾 Conferir CSV com ticker · SEM backtest** e envie a amostra WINZ22 anterior, se estiver disponível.
5. Abra **🧾 Fonte M1** e vá até **🧪 Autoteste de divergências · v1.8**. Toque em **🔬 Executar autoteste sintético (sem upload)**: não é necessário baixar ou enviar outra fonte para conferir a detecção.
6. Quando houver duas fontes externas documentadas, use a seção **🌐 Validação entre duas fontes · v1.7**. A v1.8 detalhará as diferenças logo abaixo da comparação.

### Segurança e limitações

- `0 dias certificados`, `backtest_liberado=False`, `ordens_liberadas=False` **mesmo com todos os preços idênticos**, arquivos renomeados ou deslocamento constante.
- O cálculo de hash SHA-256 identifica arquivos iguais, mas não valida a origem. Mesmo arquivos diferentes e preços coincidentes não comprovam independência.
- Declarar horários iguais com fusos desconhecidos NÃO comprova que as cotações representam o mesmo instante.
- Volume numérico é tratado separadamente e pode representar unidades distintas. Dados falsos de laboratório nunca são classificados como evidências do mercado.
- Calendário B3 e travas de outras versões não foram modificados. O motor histórico rigoroso existente continua limitado a 2026.
- Nenhuma corretora, API de trading, conta real, execução automática ou modelo de IA treinado foi adicionado.

### Verificação do código

`python -m pytest -q` — **157 testes aprovados** (145 anteriores + 12 novos), incluindo extração do ZIP. **A interface Streamlit real ainda precisa ser verificada no telefone**, pois este ambiente não contém o pacote Streamlit.

---

## Documentação preservada da versão anterior

# ◈ Trader Pro AI Elite v1.7 — Laboratório de comparação entre fontes

**WIN intraday · Streamlit responsivo · estudo exploratório, sem execução de ordens**

## Novidade: comparação A × B no celular

A v1.7 adiciona `independent_lab.py` e `test_independent_lab.py`. Depois de importar a **Fonte A** no modo **🧾 Conferir CSV com ticker · SEM backtest**, abra a aba **🧾 Fonte M1** e role até **🌐 Validação entre duas fontes · v1.7**. Você poderá enviar o **Arquivo B**, declarar o fornecedor, a referência documental e o fuso dele e baixar o laudo JSON e os CSVs de diferenças.

O comparador exige que **ambos** sejam CSV/TSV UTF-8 de 1 minuto com colunas `Datetime,Contrato,Open,High,Low,Close`; opcionais `Volume`, `Open_Adj,High_Adj,Low_Adj,Close_Adj,Ajuste`. Os campos ajustados **não são utilizados na comparação entre fontes**: são comparados somente os quatro preços **ORIGINAIS**. Os dois arquivos passam pelas verificações anteriores de ticker WIN individual, grade mínima de cinco pontos, OHLC consistente, timestamps sem segundos, registros ordenados e ausência de duplicatas.

**Comparação rigorosa:** correspondência EXATA em `(Datetime, Contrato)`; não converte fusos, não mistura tickers, não inventa candles, não arredonda preços, não compara séries ajustadas com originais e não assume dados diários como se fossem intradiários. Minutos exclusivos de A ou B são contados separadamente. Se ambos contêm a coluna `Volume`, compara os números como diagnóstico separado, **sem** assumir que volume real e tick volume têm a mesma unidade. A diferença OHLC máxima é exibida. O relatório por dia preserva a classificação `NAO_AUTENTICADO`. O arquivo de eventos é limitado aos **primeiros 500** registros para desempenho no telefone; os totais incluem todos os registros.

**Independência e licenciamento:** dois nomes diferentes ou duas URLs diferentes não comprovam fontes independentes. Mesmo SHA-256 indica o mesmo arquivo. Mesmo preços em todos os minutos não certificam B3, origem, fuso, contratos ou uso autorizado. Se as fontes declararem fusos diferentes, o app sinaliza a incompatibilidade. Se forem desconhecidos, qualquer coincidência é apenas dos horários escritos nos CSVs. A B3 disponibiliza produtos especializados de dados intradiários; arquivos gratuitos podem não ter documentação suficiente. Não baixe material de fontes não autorizadas nem compartilhe históricos com licenças restritas.

## Instruções pelo Android

1. Baixe e **extraia** `Trader_Pro_AI_Elite_v1_7_GitHub.zip`.
2. No repositório GitHub que alimenta o Streamlit existente, envie os **28 arquivos** extraídos para a **raiz**, substituindo os que já têm o mesmo nome, e confirme **Commit changes**. O arquivo de início continua sendo `app.py`.
3. Abra o mesmo site do Streamlit e confira o título `RESEARCH TERMINAL · V1.7`. Se a atualização não aparecer, recarregue a página e confira os logs do Streamlit Cloud.
4. Escolha **🧾 Conferir CSV com ticker · SEM backtest**, envie seu arquivo `WINZ22_M1_2022-10-31` já utilizado na v1.6 e mantenha o fuso **Desconhecido** se ele ainda não foi verificado.
5. Entre em **🧾 Fonte M1** e role até **🌐 Validação entre duas fontes · v1.7**. Carregue outro arquivo M1 do **mesmo contrato**, do **mesmo período**, se existir, e informe seu fornecedor declarado e fuso.
6. **Se você ainda não tem o arquivo B:** não precisa contratar plataforma, nem preencher uma fonte falsa. Pode testar a interface enviando **o mesmo arquivo** também como B; o aplicativo deverá avisar **MESMO ARQUIVO — NÃO INDEPENDENTE**. Esse teste técnico não valida o histórico.
7. Baixe `laudo_comparacao_fontes_win_v17.json` e envie para análise quando uma segunda fonte real estiver disponível.

## Estado de segurança

- O código **não** importa comparação A × B para o motor de sinais ou o backtest. O laboratório mantém **0 pregões certificados, nenhuma ordem habilitada, nenhum backtest validado**.
- Mantém intactos os bloqueios de calendário B3 e demais testes da versão anterior. O calendário do motor continua restrito ao ano **2026**.
- Não contém conta de corretora, chave de API, conexão de negociação, preços ao vivo ou IA treinada.
- A ferramenta não substitui fontes oficiais, documentação da corretora, validação financeira, dados com licença adequada, nem uma auditoria independente.

## Verificação

`python -m pytest -q` — **145 testes aprovados** (126 anteriores + 19 novos).

A suíte exercita a lógica Python; **a tela Streamlit ainda precisa ser testada na publicação real**. O ambiente local de preparação não dispõe do pacote Streamlit.

Fontes úteis para investigação (NÃO usadas automaticamente pelo aplicativo):
- B3 DataWise — https://b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/datawise/dados-disponiveis/
- MetaTrader 5 — https://www.metatrader5.com/en/terminal/help/trading/market_watch

---

## Documentação técnica preservada da v1.6
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

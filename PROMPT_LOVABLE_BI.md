# Prompt para Lovable - Dashboard BI Auditor de Rondas

Crie um dashboard web responsivo, em portugues do Brasil, para o projeto **Auditor de Rondas**. O objetivo do sistema e transformar as auditorias de justificativas de rondas nao realizadas em uma visao executiva e operacional, ajudando a identificar justificativas sem comprovacao, evidencias invalidas, fotos pretas/escuras, casos suspeitos e casos aprovaveis.

## Contexto do projeto

O projeto audita registros em que o colaborador respondeu **"Nao"** para **"INICIAR A RONDA?"** e informou uma justificativa. A auditoria cruza tarefa, colaborador, justificativa e evidencia visual, baixa ou abre a imagem enviada e classifica o caso por risco.

Classificacoes principais:

- `sem_comprovacao`: existe justificativa, mas nao existe foto/link de evidencia.
- `vermelho`: evidencia claramente invalida, como foto preta, escura demais, imagem quebrada, link com erro ou imagem inutil.
- `amarelo`: evidencia suspeita ou duvidosa, exigindo revisao humana ou IA.
- `verde`: imagem passou nos criterios tecnicos basicos e tem baixo risco tecnico.

Regra operacional sugerida:

- `verde`: aceitar automaticamente ou tratar como baixo risco.
- `amarelo`: revisar.
- `vermelho`: recusar ou priorizar auditoria.
- `sem_comprovacao`: recusar por falta de evidencia.

## Fonte de dados

A fonte preferencial do dashboard e a view Postgres:

```sql
dbo.vw_bi_auditoria_rondas
```

Se a conexao com Postgres ainda nao estiver disponivel, crie tambem um fluxo alternativo de importacao de CSV/XLSX com os mesmos campos.

Campos principais da view:

- `ronda_id`
- `execucao_id`
- `auditoria_iniciada_em`
- `auditoria_finalizada_em`
- `auditoria_origem`
- `auditoria_data_inicio`
- `auditoria_data_fim`
- `auditoria_campo_periodo`
- `auditoria_usar_ia`
- `auditoria_arquivo_excel`
- `atividade_id`
- `tarefa_id`
- `colaborador`
- `data`
- `data_execucao_inicio`
- `execucao_disponibilizacao`
- `tarefa_disponibilizacao`
- `tarefa_inicio`
- `tarefa_termino`
- `tarefa_prazo`
- `tarefa_nome`
- `checklist_nome`
- `checklist_descricao`
- `justificativa`
- `image_url`
- `image_path`
- `data_justificativa`
- `grupo_script`
- `confianca_script`
- `motivo_script`
- `brilho_medio`
- `variacao_visual`
- `pixels_escuros`
- `pixels_quase_pretos`
- `nitidez_aproximada`
- `largura`
- `altura`
- `analisada_por_ia`
- `grupo_ia`
- `confianca_ia`
- `motivo_ia`
- `descricao_visual`
- `acao_sugerida`
- `erro_ia`
- `provedor_ia`
- `modelo_ia`
- `grupo_final`
- `confianca_final`
- `motivo_final`
- `possui_analise_ia`

## Objetivo do dashboard

Construir uma tela principal de BI para auditoria operacional, sem aparencia de landing page. O primeiro viewport deve ser o dashboard em si, com filtros, KPIs e graficos.

O usuario precisa conseguir responder rapidamente:

1. Quantas rondas justificadas foram auditadas no periodo?
2. Quantas estao sem comprovacao?
3. Quantas foram classificadas como vermelho, amarelo ou verde?
4. Qual e a taxa de inconformidade?
5. Quais colaboradores, tarefas e checklists concentram mais risco?
6. Quais casos devem ser revisados primeiro?
7. A IA foi usada? Em quantos casos? Qual foi a decisao/sugestao da IA?
8. Ha padroes por data, horario, colaborador, tarefa ou tipo de evidencia?

## KPIs obrigatorios

No topo, criar cards compactos e objetivos com:

- Total de rondas justificadas auditadas.
- Total e percentual de `sem_comprovacao`.
- Total e percentual de `vermelho`.
- Total e percentual de `amarelo`.
- Total e percentual de `verde`.
- Taxa de inconformidade: (`sem_comprovacao` + `vermelho`) / total.
- Taxa de risco ampliado: (`sem_comprovacao` + `vermelho` + `amarelo`) / total.
- Total com evidencia visual: registros com `image_url` ou `image_path`.
- Total sem evidencia visual.
- Cobertura de IA: percentual com `possui_analise_ia = true`.
- Confianca media final: media de `confianca_final`.

## Filtros obrigatorios

Criar uma barra de filtros fixa ou bem acessivel com:

- Periodo por `data`, com atalhos: hoje, 7 dias, 30 dias, mes atual e periodo customizado.
- Grupo final: todos, sem comprovacao, vermelho, amarelo, verde.
- Colaborador.
- Tarefa/plano de ronda (`tarefa_nome`).
- Checklist.
- Origem da auditoria (`auditoria_origem`).
- Com IA / sem IA (`possui_analise_ia`).
- Acao sugerida da IA (`acao_sugerida`): aceitar, revisar, recusar.
- Faixa de confianca final.

Adicionar botao para limpar filtros.

## Graficos e componentes

Crie as seguintes secoes:

### 1. Visao executiva

- Grafico de barras ou rosca mostrando a distribuicao por `grupo_final`.
- Grafico de linha mostrando a evolucao diaria dos grupos.
- Card de taxa de inconformidade com comparacao visual entre grupos.

### 2. Risco operacional

- Ranking de colaboradores com mais casos `sem_comprovacao` + `vermelho`.
- Ranking de tarefas/checklists com maior taxa de inconformidade.
- Heatmap por dia da semana e hora usando `data_execucao_inicio` ou `data`.
- Barras empilhadas por `tarefa_nome` mostrando verde, amarelo, vermelho e sem comprovacao.

### 3. Qualidade da evidencia

- Scatter plot ou matriz comparando `brilho_medio`, `variacao_visual`, `pixels_escuros` e `nitidez_aproximada`, colorido por `grupo_final`.
- Cards de alerta para casos com:
  - `pixels_quase_pretos` alto.
  - `brilho_medio` muito baixo.
  - `nitidez_aproximada` baixa.
  - erro de imagem ou erro de IA.

### 4. Analise por IA

Mostrar apenas quando existirem registros com IA:

- Total analisado por IA.
- Distribuicao de `analisada_por_ia`: aprovada, reprovada, duvidosa, sem imagem, erro.
- Distribuicao de `acao_sugerida`: aceitar, revisar, recusar.
- Tabela com divergencias entre `grupo_script` e `grupo_ia`.
- Cards/tabela de casos com `erro_ia`.

### 5. Fila de auditoria

Criar uma tabela detalhada, com busca e ordenacao, priorizando primeiro:

1. `sem_comprovacao`
2. `vermelho`
3. `amarelo`
4. `verde`

Colunas da tabela:

- Prioridade visual.
- Grupo final.
- Confianca final.
- Colaborador.
- Data.
- Tarefa.
- Checklist.
- Justificativa.
- Motivo final.
- Link da evidencia (`image_url`) com botao "Abrir foto".
- Grupo script.
- Grupo IA.
- Acao sugerida IA.
- Erro IA.

Ao clicar em uma linha, abrir um painel lateral de detalhes com:

- Todos os metadados da ronda.
- Justificativa completa.
- Motivo tecnico do script.
- Motivo da IA, se existir.
- Descricao visual da IA, se existir.
- Preview da imagem quando `image_url` ou `image_path` estiver disponivel.

## Design e UX

Estilo visual: BI operacional, limpo, denso, profissional e facil de escanear. Nao criar hero/landing page.

Usar as cores dos grupos:

- `sem_comprovacao`: cinza escuro ou preto suave.
- `vermelho`: vermelho.
- `amarelo`: amarelo/ambar.
- `verde`: verde.
- estados neutros: cinza.

Evitar tela decorativa. Priorizar leitura, filtros, ranking, tabela e investigacao rapida.

Requisitos de interface:

- Layout responsivo para desktop e tablet.
- Cards compactos.
- Graficos com tooltip.
- Tabelas com ordenacao, busca e paginacao.
- Estados vazios claros quando nao houver dados.
- Loading states.
- Tratamento de erro de conexao/fonte de dados.
- Exportar tabela filtrada para CSV.
- Botao para copiar link da foto, quando existir.

## Calculos esperados

Considere:

```text
total = count(ronda_id)
sem_comprovacao = count(grupo_final = 'sem_comprovacao')
vermelho = count(grupo_final = 'vermelho')
amarelo = count(grupo_final = 'amarelo')
verde = count(grupo_final = 'verde')
inconformidade = (sem_comprovacao + vermelho) / total
risco_ampliado = (sem_comprovacao + vermelho + amarelo) / total
com_evidencia = count(image_url not null/vazio OR image_path not null/vazio)
sem_evidencia = total - com_evidencia
cobertura_ia = count(possui_analise_ia = true) / total
confianca_media = avg(confianca_final)
```

Para ranking de risco, use como pontuacao:

```text
sem_comprovacao = 100 pontos
vermelho = 90 pontos
amarelo = 50 pontos
verde = 0 pontos
```

Mostrar tanto volume quanto taxa, para evitar conclusoes erradas em colaboradores/tarefas com poucos registros.

## Dados de exemplo para desenvolvimento

O CSV gerado pelo projeto possui colunas como:

```csv
atividade_id,tarefa_id,colaborador,data,data_execucao_inicio,execucao_disponibilizacao,tarefa_disponibilizacao,tarefa_inicio,tarefa_termino,tarefa_prazo,tarefa_nome,checklist_nome,checklist_descricao,justificativa,image_url,data_justificativa,grupo,confianca,motivo,grupo_local,confianca_local,motivo_local,brilho_medio,variacao_visual,pixels_escuros,pixels_quase_pretos,nitidez_aproximada,largura,altura,grupo_ia,confianca_ia,motivo_ia,erro_ia
```

Mapeie `grupo` como equivalente a `grupo_final` quando estiver usando CSV antigo que ainda nao tenha a view Postgres.

## Entrega esperada

Entregue um dashboard funcional com:

- Pagina principal `/dashboard`.
- Conexao preparada para Postgres/view ou importacao CSV.
- Componentes reutilizaveis para KPIs, filtros, graficos e tabela.
- Dados mockados suficientes para visualizar a tela caso a fonte real ainda nao esteja conectada.
- Layout profissional em portugues do Brasil.
- Codigo organizado e facil de conectar depois ao banco real.

Nao crie uma pagina institucional. Crie diretamente o produto: um BI de auditoria de rondas pronto para operacao.

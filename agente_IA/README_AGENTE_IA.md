# Agente IA de Validacao de Evidencias

Este agente le um CSV de rondas justificadas, analisa a justificativa do colaborador junto com a imagem enviada e gera um novo arquivo `.xlsx` com a coluna:

```text
analisada por IA
```

## O Que Ele Valida

Para cada linha, o agente observa:

- justificativa do colaborador;
- dados da tarefa/checklist, quando existirem no CSV;
- classificacao anterior do auditor, quando existir;
- foto enviada em `image_url` ou `image_path`;
- coerencia entre texto e imagem.

## Resultado Da IA

O XLSX final inclui as colunas:

- `analisada por IA`: `aprovada`, `reprovada`, `duvidosa`, `sem imagem` ou `erro`;
- `grupo_analise_ia`: grupo tecnico da analise;
- `confianca_analise_ia`: confianca entre 0 e 1;
- `motivo_analise_ia`: motivo da decisao;
- `descricao_visual_ia`: o que a imagem parece mostrar;
- `acao_sugerida_ia`: `aceitar`, `revisar` ou `recusar`;
- `erro_analise_ia`: erro tecnico, quando houver.

## Configuracao

O agente usa o `.env` da pasta `auditor_rondas`.

Para usar Ollama Cloud, deixe assim:

```env
IA_PROVIDER=ollama
OLLAMA_MODEL=gemma4:31b-cloud
```

Para usar OpenAI, troque o provedor e preencha a chave:

```env
IA_PROVIDER=openai
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-4.1
```

## Instalacao

Na pasta `auditor_rondas`, instale:

```powershell
python -m pip install -r agente_IA\requirements_agente_ia.txt
```

## Como Rodar

Exemplo usando um CSV da pasta `resultados`:

```powershell
py agente_IA\agente_analise_ia.py --entrada resultados\resultado_2026-04-27.csv --saida resultados\resultado_2026-04-27_ia.xlsx
```

Para forcar Ollama no comando, sem depender do `.env`:

```powershell
python agente_IA\agente_analise_ia.py --entrada resultados\resultado_2026-04-27.csv --saida resultados\resultado_2026-04-27_ia.xlsx --provedor-ia ollama
```

Para testar somente as primeiras 5 linhas:

```powershell
python agente_IA\agente_analise_ia.py --entrada resultados\resultado_2026-04-27.csv --saida resultados\teste_ia.xlsx --limite 5
```

Por padrao, o agente baixa a imagem localmente e envia para a IA como base64. Isso ajuda quando a URL nao esta acessivel diretamente pela OpenAI.

Se quiser enviar a URL diretamente:

```powershell
python agente_IA\agente_analise_ia.py --entrada resultados\resultado_2026-04-27.csv --saida resultados\resultado_ia.xlsx --nao-baixar-links
```

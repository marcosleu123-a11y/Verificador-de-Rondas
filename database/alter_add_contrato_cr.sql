-- Migração para enriquecer a base de BI com contrato e estrutura/local.

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS contrato_cr TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS estrutura_id TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS nivel_03 TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS nivel_04 TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS andar TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS local TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS ambiente TEXT;

ALTER TABLE dbo.rondas_base
ADD COLUMN IF NOT EXISTS qrcode TEXT;

DROP VIEW IF EXISTS dbo.vw_bi_auditoria_rondas;

CREATE VIEW dbo.vw_bi_auditoria_rondas AS
SELECT
    r.id AS ronda_id,
    r.execucao_id,
    e.iniciado_em AS auditoria_iniciada_em,
    e.finalizado_em AS auditoria_finalizada_em,
    e.origem AS auditoria_origem,
    e.data_inicio AS auditoria_data_inicio,
    e.data_fim AS auditoria_data_fim,
    e.campo_periodo AS auditoria_campo_periodo,
    e.usar_ia AS auditoria_usar_ia,
    e.arquivo_excel AS auditoria_arquivo_excel,
    r.atividade_id,
    r.tarefa_id,
    r.contrato_cr,
    r.estrutura_id,
    r.nivel_03,
    r.nivel_04,
    r.andar,
    r.local,
    r.ambiente,
    r.qrcode,
    r.colaborador,
    r.data,
    r.data_execucao_inicio,
    r.execucao_disponibilizacao,
    r.tarefa_disponibilizacao,
    r.tarefa_inicio,
    r.tarefa_termino,
    r.tarefa_prazo,
    r.tarefa_nome,
    r.checklist_nome,
    r.checklist_descricao,
    r.justificativa,
    r.image_url,
    r.image_path,
    r.data_justificativa,
    s.id AS analise_script_id,
    s.grupo AS grupo_script,
    s.confianca AS confianca_script,
    s.motivo AS motivo_script,
    s.brilho_medio,
    s.variacao_visual,
    s.pixels_escuros,
    s.pixels_quase_pretos,
    s.nitidez_aproximada,
    s.largura,
    s.altura,
    s.analisado_em AS script_analisado_em,
    ia.id AS analise_ia_id,
    ia.analisada_por_ia,
    ia.grupo AS grupo_ia,
    ia.confianca AS confianca_ia,
    ia.motivo AS motivo_ia,
    ia.descricao_visual,
    ia.acao_sugerida,
    ia.erro AS erro_ia,
    ia.provedor_ia,
    ia.modelo_ia,
    ia.analisado_em AS ia_analisado_em,
    CASE
        WHEN ia.grupo IS NOT NULL AND ia.grupo <> '' THEN ia.grupo
        ELSE s.grupo
    END AS grupo_final,
    CASE
        WHEN ia.confianca IS NOT NULL THEN ia.confianca
        ELSE s.confianca
    END AS confianca_final,
    CASE
        WHEN ia.motivo IS NOT NULL AND ia.motivo <> '' THEN ia.motivo
        ELSE s.motivo
    END AS motivo_final,
    CASE
        WHEN ia.id IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS possui_analise_ia
FROM dbo.rondas_base r
LEFT JOIN dbo.auditoria_execucoes e
    ON e.id = r.execucao_id
LEFT JOIN dbo.analise_script s
    ON s.ronda_id = r.id
LEFT JOIN dbo.analise_ia ia
    ON ia.ronda_id = r.id;

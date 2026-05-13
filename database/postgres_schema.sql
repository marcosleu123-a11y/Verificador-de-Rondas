CREATE SCHEMA IF NOT EXISTS dbo;

CREATE TABLE IF NOT EXISTS dbo.auditoria_execucoes (
    id BIGSERIAL PRIMARY KEY,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ,
    origem TEXT NOT NULL DEFAULT 'sql_server',
    data_inicio DATE,
    data_fim DATE,
    campo_periodo TEXT,
    usar_ia BOOLEAN NOT NULL DEFAULT FALSE,
    arquivo_excel TEXT,
    total_registros INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dbo.rondas_base (
    id BIGSERIAL PRIMARY KEY,
    execucao_id BIGINT REFERENCES dbo.auditoria_execucoes(id),
    atividade_id TEXT,
    tarefa_id TEXT,
    contrato_cr TEXT,
    estrutura_id TEXT,
    nivel_03 TEXT,
    nivel_04 TEXT,
    andar TEXT,
    local TEXT,
    ambiente TEXT,
    qrcode TEXT,
    colaborador TEXT,
    data TIMESTAMP,
    data_execucao_inicio TIMESTAMP,
    execucao_disponibilizacao TIMESTAMP,
    tarefa_disponibilizacao TIMESTAMP,
    tarefa_inicio TIMESTAMP,
    tarefa_termino TIMESTAMP,
    tarefa_prazo TIMESTAMP,
    tarefa_nome TEXT,
    checklist_nome TEXT,
    checklist_descricao TEXT,
    justificativa TEXT,
    image_url TEXT,
    image_path TEXT,
    data_justificativa TIMESTAMP,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dbo.analise_script (
    id BIGSERIAL PRIMARY KEY,
    ronda_id BIGINT NOT NULL REFERENCES dbo.rondas_base(id) ON DELETE CASCADE,
    grupo TEXT,
    confianca NUMERIC(5,2),
    motivo TEXT,
    brilho_medio NUMERIC(10,4),
    variacao_visual NUMERIC(10,4),
    pixels_escuros NUMERIC(10,4),
    pixels_quase_pretos NUMERIC(10,4),
    nitidez_aproximada NUMERIC(10,4),
    largura INTEGER,
    altura INTEGER,
    analisado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dbo.analise_ia (
    id BIGSERIAL PRIMARY KEY,
    ronda_id BIGINT NOT NULL REFERENCES dbo.rondas_base(id) ON DELETE CASCADE,
    analise_script_id BIGINT REFERENCES dbo.analise_script(id) ON DELETE SET NULL,
    analisada_por_ia TEXT,
    grupo TEXT,
    confianca NUMERIC(5,2),
    motivo TEXT,
    descricao_visual TEXT,
    acao_sugerida TEXT,
    erro TEXT,
    provedor_ia TEXT,
    modelo_ia TEXT,
    analisado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW dbo.vw_bi_auditoria_rondas AS
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

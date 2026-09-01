import sqlite3
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS cobrancas (
    id_titulo TEXT,
    etapa INTEGER NOT NULL DEFAULT 1,   -- 1 = 2 dias apos vencimento | 2 = ultimo dia (vctpro)
    codemp INTEGER,
    codfil INTEGER,
    codcli TEXT,
    numero_nf TEXT,
    cliente_nome TEXT,
    telefone TEXT,
    valor REAL,
    data_vencimento TEXT,
    conversation_id TEXT,
    status TEXT DEFAULT 'pendente',   -- pendente | enviado | falhou | respondido | negociacao
    data_envio TEXT,
    respondeu INTEGER DEFAULT 0,
    erro TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_titulo, etapa)
);
"""


def get_connection():
    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def ja_enviado(id_titulo, etapa):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT status FROM cobrancas
            WHERE id_titulo = ? AND etapa = ?
              AND status IN ('enviado', 'respondido', 'negociacao')
            """,
            (id_titulo, etapa),
        ).fetchone()
    return row is not None


def registrar_titulo(titulo):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cobrancas (id_titulo, etapa, codemp, codfil, codcli, numero_nf, cliente_nome, telefone, valor, data_vencimento)
            VALUES (:id_titulo, :etapa, :codemp, :codfil, :codcli, :numero_nf, :cliente_nome, :telefone, :valor, :data_vencimento)
            ON CONFLICT(id_titulo, etapa) DO NOTHING
            """,
            titulo,
        )


def marcar_enviado(id_titulo, etapa, conversation_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE cobrancas
            SET status = 'enviado', conversation_id = ?, data_envio = CURRENT_TIMESTAMP, erro = NULL
            WHERE id_titulo = ? AND etapa = ?
            """,
            (conversation_id, id_titulo, etapa),
        )


def marcar_falha(id_titulo, erro, etapa=None):
    with get_connection() as conn:
        if etapa is None:
            conn.execute(
                """
                UPDATE cobrancas SET status = 'falhou', erro = ?
                WHERE id_titulo = ?
                  AND status NOT IN ('enviado', 'respondido', 'negociacao')
                """,
                (str(erro), id_titulo),
            )
        else:
            conn.execute(
                "UPDATE cobrancas SET status = 'falhou', erro = ? WHERE id_titulo = ? AND etapa = ?",
                (str(erro), id_titulo, etapa),
            )


def marcar_respondido(conversation_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE cobrancas SET respondeu = 1, status = 'respondido' WHERE conversation_id = ?",
            (str(conversation_id),),
        )
import oracledb
import config
from datetime import datetime

# thick mode - necessario para o driver antigo do Sapiens/Oracle
oracledb.init_oracle_client(lib_dir=config.ORACLE_CLIENT_LIB_DIR)


def get_connection():
    return oracledb.connect(
        user=config.ORACLE_USER,
        password=config.ORACLE_PASSWORD,
        dsn=config.ORACLE_DSN,
    )

def buscar_titulos_vencidos(dias_janela=None, query_path="sql/query_titulos_vencidos.sql"):
    dias_janela = dias_janela or config.DIAS_JANELA

    with open(query_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with get_connection() as conn:
        cursor = conn.cursor()
        binds = {"dias_janela": dias_janela} if ":dias_janela" in sql.lower() else {}
        cursor.execute(sql, binds)
        colunas = [c[0].lower() for c in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(colunas, row)) for row in rows]

def registrar_observacao_cobranca(codemp, codfil, numtit, codtpt, etapa):
    agora = datetime.now()
    quando = f"em {agora:%d/%m/%Y} as {agora:%H:%M}"
    telefone = "43 3377-0081"
    if etapa == 1:
        texto = f"1° cobrança enviada por WhatsApp|{telefone}|(bot) {quando}"
    else:
        texto = f"{etapa}a cobranca (aviso antes do cartorio) enviada por WhatsApp|{telefone}|(bot) {quando}"

    chave = {"codemp": codemp, "codfil": codfil, "numtit": numtit,
             "codtpt": codtpt, "codusu": config.COD_USU_BOT}

    with get_connection() as conn:
        cur = conn.cursor()

        # Etapa 2 em diante: acrescenta " / texto" na ultima observacao do bot
        if etapa != 1:
            cur.execute(
                """
                UPDATE sapiens.USU_T301OBS
                   SET usu_obstcr = usu_obstcr || ' / ' || :texto
                 WHERE usu_codemp = :codemp AND usu_codfil = :codfil
                   AND usu_numtit = :numtit AND usu_codtpt = :codtpt
                   AND usu_codusu = :codusu
                   AND usu_seqobs = (SELECT MAX(usu_seqobs) FROM sapiens.USU_T301OBS
                                      WHERE usu_codemp = :codemp AND usu_codfil = :codfil
                                        AND usu_numtit = :numtit AND usu_codtpt = :codtpt
                                        AND usu_codusu = :codusu)
                """,
                {**chave, "texto": texto},
            )
            if cur.rowcount:
                conn.commit()
                return

        # Etapa 1 (ou etapa 2 sem observacao anterior do bot): linha nova
        cur.execute(
            """
            INSERT INTO sapiens.USU_T301OBS
                (usu_codemp, usu_codfil, usu_numtit, usu_codtpt,
                 usu_seqobs, usu_datobs, usu_obstcr, usu_codusu)
            SELECT :codemp, :codfil, :numtit, :codtpt,
                   NVL(MAX(usu_seqobs), 0) + 1, :datobs, :obs, :codusu
            FROM sapiens.USU_T301OBS
            WHERE usu_codemp = :codemp AND usu_codfil = :codfil
              AND usu_numtit = :numtit AND usu_codtpt = :codtpt
            """,
            {**chave, "datobs": agora, "obs": texto},
        )
        conn.commit()
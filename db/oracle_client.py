import oracledb
import config

# thick mode - necessario para o driver antigo do Sapiens/Oracle
# ajustar lib_dir para o caminho do Oracle Instant Client na maquina
oracledb.init_oracle_client()


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
        cursor.execute(sql)
        colunas = [c[0].lower() for c in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(colunas, row)) for row in rows]

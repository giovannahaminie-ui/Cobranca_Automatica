SELECT
    t.codemp,
    t.codfil,
    t.numtit AS id_titulo,
    f.numnfc AS numero_nf,
    f.chvnel AS chave_nfe,
    c.foncli AS telefone,
    c.codcli,
    c.nomcli AS cliente_nome,
    t.codcrt,
    t.codpor,
    t.codsnf,
    t.codtpt,
    t.vlrabe AS valor,
    t.datemi AS data_emissao,
    t.vctori AS data_vencimento
FROM sapiens.E301TCR t
LEFT JOIN sapiens.E085CLI c
    ON c.codcli = t.codcli
LEFT JOIN sapiens.E440NFC f
    ON f.codemp = t.codemp
    AND f.codfil = t.codfil
    AND f.numnfc = t.numnfc
    AND f.codsnf = t.codsnf
WHERE c.codcli = '990139103'
    AND t.numtit = '1344-R1'
    AND t.vctori >= TRUNC(SYSDATE) - 60
    AND t.vlrabe > 0
    AND t.codtpt NOT IN ('GAR', 'GRT', 'SCI', 'RAT')
    AND t.sittit NOT IN ('CA')
ORDER BY t.datemi ASC
SELECT t.codemp,
       t.codfil,
       t.codcli,
       c.nomcli AS cliente_nome,
       c.apecli,
       c.codgre,
       c.foncli AS telefone,
       t.numtit AS id_titulo,
       t.sittit,
       p.codtpt,
       n.numnfv AS Numero_NF,
       t.codsnf,
       t.datemi,
       t.vctori AS Data_Vencimento,
       t.vctpro,
       f.desfpg,
       f.abrfpg,
       t.codtns,
       r.modblo,
       t.vlrori,
       t.vlrabe AS valor,
       t.codpor,
       t.codcrt,
       t.codfpg,
       o.usu_obstcr,
       o.usu_datobs,
       o.usu_codusu,
       e.usu_seqemp
       FROM sapiens.E301TCR t
LEFT JOIN sapiens.E140NFV n ON n.codemp = t.codemp
       AND n.codfil = t.codfil
       AND n.codsnf = t.codsnf
       AND n.numnfv = t.numnfv
LEFT JOIN sapiens.USU_T301OBS o ON o.usu_codemp = t.codemp
       AND o.usu_codfil = t.codfil
       AND o.usu_numtit = t.numtit
LEFT JOIN sapiens.E085CLI c ON c.codcli = t.codcli
LEFT JOIN sapiens.E066FPG f ON f.codemp = t.codemp
       AND f.codfpg = t.codfpg
LEFT JOIN sapiens.USU_TempFil e ON e.usu_codemp = t.codemp
       AND e.usu_codfil = t.codfil
LEFT JOIN sapiens.E002TPT p ON p.codtpt = t.codtpt
LEFT JOIN sapiens.E039POR r ON r.codemp = t.codemp
       AND r.codpor = t.codpor
WHERE (t.datemi > TO_DATE('01/01/2025','dd/mm/yyyy') OR t.vctori > TO_DATE('01/01/2025','dd/mm/yyyy'))
AND t.codtpt NOT IN('GAR','GRT','SCI','RAT')
AND t.sittit NOT IN ('CA')
AND t.vlrabe > 0
AND t.codemp = 1
AND t.codfil = 1
AND t.numtit = '84785-01'

WITH INVOICE AS
(
    SELECT 
    S.LASTFIRST AS "STUDENT",
    S.STUDENT_NUMBER AS "STUDENT_NUMBER",
    G.NAME AS "DISTRICTOFRESIDENCE",
    A.N_ENTRYDATE AS,
    A.N_EXITDATE AS,
    1 AS "REPORTORDER",
    A.AUD_SEQ
    FROM STUDENTS S
    INNER JOIN AU_REENROLLMENTS A
    ON S.DCID = A.STUDENTID
    INNER JOIN GEN G
    ON G.CAT = 'districts' AND A.N_DISTRICTOFRESIDENCE = G.VALUE
    WHERE S.DCID = 3318
    
    UNION
    
    SELECT
    S.LASTFIRST,
    S.STUDENT_NUMBER,
    H.NAME AS "DISTRICTOFRESIDENCE",
    S.ENTRYDATE,
    S.EXITDATE,
    2,
    1000
    FROM STUDENTS S
    INNER JOIN GEN H
    ON H.CAT = 'districts' AND S.DISTRICTOFRESIDENCE = H.VALUE
    WHERE S.DCID = 3318
)
SELECT
STUDENT,
STUDENT_NUMBER AS "STUDENT_NUMBER",
DISTRICTOFRESIDENCE AS "DISTRICT OF RESIDENCE",
N_ENTRYDATE AS "START DATE",
N_EXITDATE AS "END DATE"
FROM INVOICE I
ORDER BY I.REPORTORDER ASC, I.AUD_SEQ ASC

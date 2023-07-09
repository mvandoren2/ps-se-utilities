SELECT DISTINCT 
FIRST_NAME, 
SCHOOLID,
REPLACE(FIRST_NAME, ' ', '') || '.' || REPLACE(LAST_NAME, ' ', '') || '@applegroveschools.com' as CALCULATED_EMAIL
FROM TEACHERS 
WHERE FIRST_NAME NOT IN (
'Macro', 'Demo', 'Admin', 'User', 'Auto', 'Level', 'Dev', 'Chad', '34', '35', 'Elmo', 'Maddie', 'Mara', 'Mikliszanski'
) 
AND LAST_NAME NOT IN(
'Nguyen', 'Cohn', 'Featherstone', 'Springel', 'Raymond', 'Rotten', 'McKean', 'Cinnamon', 
'MVD1', 'MVD2', 'MVD3', 'MVD4', 'MVD5', 'MVD6', 'Van Doren', 'Woo', 'Admin', 'Ryms', 'Staff',
'Cuadra'
)
AND SCHOOLID = 300
ORDER BY FIRST_NAME
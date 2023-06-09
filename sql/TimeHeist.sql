/*
	THIS SCRIPT SHOULD ONLY BE USED ON INTERNAL POWERSCHOOL SIS INSTANCES.  THE PURPOSE OF THIS SCRIPT IS TO GENERATE
	A SERIES OF UPDATE SCRIPTS TO ADVANCE THE DATES, YEARS, AND TERMS ON A POWERSCHOOL SIS DATABASE. ITS FIRST ATTEMPT
	AT USAGE WAS IN THE ROLLOVER FOR YEAR 2021 AND HAS ONLY BEEN TESTED ON A CORE SIS SET OF TABLES.  THEORETICALLY
	THIS CAN BE USED ON ANY POWERSCHOOL SIS DATABASE HOWEVER WE ARE NOT RESPONSIBLE FOR RESULTS PERTAINING TO PARTNERS
	AND STATE COMPLIANCE.

	IN ORDER TO LEVERAGE THIS META-SCRIPT THERE ARE A FEW STEPS TO DEPLOY.  HERE ARE THE FOLLOWING STEPS.
	1.	SHUT OFF POWERSCHOOL SERVICES
	2.	RUN THE SCRIPT BELOW.  THE QUERY RESULT WILL INCLUDE A SPECIFIC ORDERED SET OF SQL STATEMENTS
	3.	EXPORT THE QUERY RESULT. IN ORACLE SQL DEVELOPER EXPORT AS A TEXT FILE SAVED AS .SQL FILE, REMOVE THE HEADER, NO STARTING/ENCLOSING QUOTES
	4.	RUN THE CONTENTS OF THE GENERATED FILE ON THE SOURCE POWERSCHOOL SIS DATABASE
	5.	START POWERSCHOOL SERVICES

	NOTE: 	THIS SCRIPT IS PROVIDED AS-IS.  FEEDBACK IS APPRECIATED BUT THERE IS NO OBLIGATION TO MVD ON ANY EDITS/UPDATES.
			IF YOU WOULD LIKE TO AUGMENT THIS SCRIPT FEEL FREE TO TAKE A LOCAL COPY FOR ADJUSTMENTS
*/
WITH TIMEHEIST AS 
(
	/*
		DISABLE ALL TRIGGERS IN PS SCHEMA	
		SOURCE: MVD
	*/
	SELECT
		'ALTER TRIGGER ' || OWNER || '.' || TRIGGER_NAME || ' DISABLE ;' AS STATEMENT,
		10 AS SEQUENCE 
	FROM
		ALL_TRIGGERS 
	WHERE
		OWNER = 'PS' 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		20 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE TERMS TABLE ID BY 100 AND ADVANCE YEARID BY 1	
		SOURCE: MVD
	*/
	SELECT
		'UPDATE TERMS SET ID = ID + 100, IMPORTMAP = IMPORTMAP + 100, YEARID = YEARID + 1;' AS STATEMENT,
		30 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE THE SCHEDULETERMS TABLE IN THE SAME WAY AS THE TERMS TABLE	
		SOURCE: JAY RAYMOND
	*/
	SELECT
		'UPDATE SCHEDULETERMS SET ID = ID + 100, IMPORTMAP = IMPORTMAP + 100, YEARID = YEARID + 1;' AS STATEMENT,
		40 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE THE SCHEDULEREQUESTS TABLE.
		NOTE: YEARID IN THIS TABLE IS ACTUALLY OPERATING AS A TERMID
		SOURCE: MVD
	*/
	SELECT
		'UPDATE SCHEDULEREQUESTS SET YEARID = YEARID + 100;' AS STATEMENT,
		50 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE THE YEAR OF GRADUATION BY 1 FOR ALL STUDENTS THAT HAVE A GRADUATION YEAR	
		SOURCE: JAY RAYMOND
	*/
	SELECT
		'UPDATE STUDENTS SET SCHED_YEAROFGRADUATION = SCHED_YEAROFGRADUATION + 1 WHERE SCHED_YEAROFGRADUATION IS NOT NULL;' AS STATEMENT,
		60 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		70 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE EVERY YEARID / YEAR_ID FIELD IN ALL TABLES EXCEPT TERMS AND PREFS TABLE.  EXCLUDE TERMS BECAUSE THAT YEARID WAS ALREADY ADVANCED PRIOR.
		SOURCE: MVD
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + 1 WHERE ' || COLUMN_NAME || ' IS NOT NULL;' AS STATEMENT,
		80 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		COLUMN_NAME IN 
		(
			'YEARID',
			'YEAR_ID',
			'BUILDYEAR' 
		)
		AND COL.TABLE_NAME NOT IN 
		(
			'TERMS',
			'SCHEDULETERMS',
			'SCHEDULEREQUESTS',
			'PREFS',
			'PS_COMMON_CODE' 
		)
	UNION ALL
	/*
		UPDATE YEARID IN THE PREFS TABLE EXCEPT PREFS THAT HAVE NON-APPLICABLE YEARIDS  
		SOURCE OF EXCLUSION: MATT HUTCHINS
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + 1 WHERE ' || COLUMN_NAME || ' != 0 AND ' || COLUMN_NAME || ' IS NOT NULL AND ' || COLUMN_NAME || ' > 20;' AS STATEMENT,
		90 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		COLUMN_NAME IN 
		(
			'YEARID',
			'YEAR_ID',
			'BUILDYEAR' 
		)
		AND COL.TABLE_NAME IN 
		(
			'PREFS' 
		)
	UNION ALL
	/*
		UPDATE YEARID IN THE PS_COMMON_CODE EXCEPT SPECIFIC END DATE.	
		SOURCE OF EXCLUSION: MATT HUTCHINS
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + 1 WHERE ' || COLUMN_NAME || ' != 0 AND ' || COLUMN_NAME || ' IS NOT NULL AND TO_CHAR(EFFECTIVE_ENDDATE,''MM-YYYY'') != ''09-9999'';' AS STATEMENT,
		100 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		COLUMN_NAME IN 
		(
			'YEARID',
			'YEAR_ID',
			'BUILDYEAR' 
		)
		AND COL.TABLE_NAME IN 
		(
			'PS_COMMMON_CODE' 
		)
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		110 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE TERMIDS FOR EVERY TABLE EXCLUDING PSM_SECTION, SYNC_TERMMAP, PSM_REPORTINGTERM DUE TO THE FACT THAT THEY THROW CONSTRAINT ERRORS.  UNCLEAR
		AS TO THE CAUSE OF THE CONSTRAINT ERROR AND EVEN REMOVING THESE TABLES TO RUN LATER HASN'T SOLVED THE PROBLEM.  FURTHER INVESTIGATION REQUIRED.
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + 100 WHERE ' || COLUMN_NAME || ' IS NOT NULL;' AS STATEMENT,
		120 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		COLUMN_NAME IN 
		(
			'TERMID' 
		)
		AND COL.TABLE_NAME NOT IN 
		(
			'PSM_SECTION',
			'SYNC_TERMMAP',
			'PSM_REPORTINGTERM' 
		)
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		130 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE EVERY DATETIME FIELD WITHIN THE DATABASE EXCLUDING SPECIFIC TABLES DUE TO ISSUES.
		SOURCE OF EXCLUSION VIEWCONTROL:		NITIN KAUSHIK
		SOURCE OF EXCLUSION PS_COMMON_CODE:		MATT HUTCHINS
		SOURCE OF EXCLUSEION ALERT_*:			JAY RAYMOND
		NOTE: DESPITE EXCLUDING THE ALERT TABLES, THEY ARE STILL RENDERING A 1901
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + NUMTODSINTERVAL(364,''DAY'') WHERE ' || COLUMN_NAME || ' IS NOT NULL;',
		140 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		(
			DATA_TYPE IN 
			(
				'DATE' 
			)
			OR COL.DATA_TYPE LIKE 'TIMESTAMP%' 
			OR COL.DATA_TYPE LIKE 'INTERVAL%' 
		)
		AND COL.OWNER = 'PS' 
		AND COLUMN_NAME NOT IN 
		(
			'WHENCREATED',
			'WHENMODIFIED',
			'LAST_UPDATED_ON',
			'CREATED_TS',
			'LAST_MODIFIED_TS',
			'CREATIONDATE',
			'CREATION_DATE',
			'MODIFICATIONDATE', 
			'ASSETDATE'
		)
		AND COL.TABLE_NAME NOT IN 
		(
			'VIEWCONTROL',
			'PS_COMMON_CODE' 
		)
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		150 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		ADVANCE PS_COMMON_CODE WITH SPECIFIC FILTER.  
		SOURCE OF EXCLUSION:	MATT HUTCHINS
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = ' || COLUMN_NAME || ' + NUMTODSINTERVAL(364,''DAY'') WHERE ' || COLUMN_NAME || ' IS NOT NULL AND TO_CHAR(EFFECTIVE_ENDDATE,''MM-YYYY'') != ''09-9999'';',
		160 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		(
			DATA_TYPE IN 
			(
				'DATE' 
			)
			OR COL.DATA_TYPE LIKE 'TIMESTAMP%' 
			OR COL.DATA_TYPE LIKE 'INTERVAL%' 
		)
		AND COL.OWNER = 'PS' 
		AND COLUMN_NAME NOT IN 
		(
			'WHENCREATED',
			'WHENMODIFIED',
			'LAST_UPDATED_ON',
			'CREATED_TS',
			'LAST_MODIFIED_TS',
			'CREATIONDATE',
			'CREATION_DATE',
			'MODIFICATIONDATE',
			'ASSETDATE' 
		)
		AND COL.TABLE_NAME IN 
		(
			'PS_COMMON_CODE' 
		)
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		170 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		SET ENROLLMENT_TRANSFER_DATE_PEND TO NULL TO PREVENT THE STATUS OF "TRANSFER OUT PENDING".	
		SOURCE:	KEVIN CINNAMON
	*/
	SELECT
		'UPDATE STUDENTS SET ENROLLMENT_TRANSFER_DATE_PEND = NULL;' AS STATEMENT,
		180 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		190 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		RE-ENABLE ALL TRIGGERS
		SOURCE: MVD
	*/
	SELECT
		'ALTER TRIGGER ' || OWNER || '.' || TRIGGER_NAME || ' ENABLE ;' AS STATEMENT,
		200 AS SEQUENCE 
	FROM
		ALL_TRIGGERS 
	WHERE
		OWNER = 'PS' 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		210 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE ABBREVIATIONS ON TERMS TABLE.
		SOURCE: MVD
	*/
	SELECT
		'UPDATE TERMS SET ABBREVIATION = TO_CHAR(YEARID - 10) || ''-'' || TO_CHAR(YEARID - 9) WHERE ABBREVIATION LIKE ''%-%'';' AS STATEMENT,
		220 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE NAME ON TERMS TABLE.
		SOURCE: MVD
	*/
	SELECT
		'UPDATE TERMS SET NAME = TO_CHAR(YEARID + 1990) || ''-'' || TO_CHAR(YEARID + 1991) WHERE NAME LIKE ''%-%'';' AS STATEMENT,
		230 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		240 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE ABBREVIATION ON SCHEDULETERMS TABLE.
		SOURCE: JAY RAYMOND
	*/
	SELECT
		'UPDATE SCHEDULETERMS SET ABBREVIATION = TO_CHAR(YEARID - 10) || ''-'' || TO_CHAR(YEARID - 9) WHERE ABBREVIATION LIKE ''%-%'';' AS STATEMENT,
		250 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE NAME ON SCHEDULETERMS TABLE.
		SOURCE: JAY RAYMOND
	*/
	SELECT
		'UPDATE SCHEDULETERMS SET NAME = TO_CHAR(YEARID + 1990) || ''-'' || TO_CHAR(YEARID + 1991) WHERE NAME LIKE ''%-%'';' AS STATEMENT,
		260 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE NAME ON SCHEDULEBUILDS TABLE.
		SOURCE: MVD
	*/
	SELECT
		'UPDATE SCHEDULEBUILDS SET BUILDNAME = TO_CHAR(BUILDYEAR + 1990) || ''-'' || TO_CHAR(BUILDYEAR + 1991) WHERE BUILDNAME LIKE ''%-%'';' AS STATEMENT,
		270 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		280 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE INCIDENT TABLE TO TOGGLE TRIGGER.
		SOURCE: KEVIN CINNAMON
	*/
	SELECT
		'UPDATE INCIDENT SET INCIDENT_TS = INCIDENT_TS  + NUMTODSINTERVAL(1,''DAY'') WHERE INCIDENT_TS IS NOT NULL;' AS STATEMENT,
		290 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		300 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		UPDATE INCIDENT TABLE TO TOGGLE TRIGGER MINUS ONE DAY.
		SOURCE: KEVIN CINNAMON
	*/
	SELECT
		'UPDATE INCIDENT SET INCIDENT_TS = INCIDENT_TS  + NUMTODSINTERVAL(-1,''DAY'') WHERE INCIDENT_TS IS NOT NULL;' AS STATEMENT,
		310 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		320 AS SEQUENCE 
	FROM
		DUAL 
	UNION ALL
	/*
		FIND ALL ERRONEOUS DATE FIELDS AND NULL THEM OUT
	*/
	SELECT
		'UPDATE ' || COL.TABLE_NAME || ' SET ' || COLUMN_NAME || ' = NULL WHERE ' || COLUMN_NAME || ' < TO_DATE(''31-DEC-1979'',''dd-MON-yyyy'');',
		330 AS SEQUENCE 
	FROM
		SYS.ALL_TAB_COLS COL 
		JOIN
			SYS.ALL_TABLES TAB 
			ON COL.OWNER = TAB.OWNER 
			AND COL.TABLE_NAME = TAB.TABLE_NAME 
	WHERE
		(
			DATA_TYPE IN 
			(
				'DATE' 
			)
			OR COL.DATA_TYPE LIKE 'TIMESTAMP%' 
			OR COL.DATA_TYPE LIKE 'INTERVAL%' 
		)
		AND COL.OWNER = 'PS' 
		AND COLUMN_NAME NOT IN 
		(
			'WHENCREATED',
			'WHENMODIFIED',
			'LAST_UPDATED_ON',
			'CREATED_TS',
			'LAST_MODIFIED_TS',
			'CREATIONDATE',
			'CREATION_DATE',
			'MODIFICATIONDATE' 
		)
		AND COL.TABLE_NAME NOT IN 
		(
			'VIEWCONTROL',
			'PS_COMMON_CODE' 
		)
	UNION ALL
	SELECT
		'COMMIT;' AS STATEMENT,
		340 AS SEQUENCE 
	FROM
		DUAL 
)
SELECT
	STATEMENT 
FROM
	TIMEHEIST 
ORDER BY
	TIMEHEIST.SEQUENCE ASC

/*

ONE OFF SCRIPTS FOR SISGOLD/SG1

UPDATE PREFS SET VALUE = 3200 WHERE NAME LIKE 'scheduleYearID-%' AND DCID IN (26146,9898);
COMMIT;

*/
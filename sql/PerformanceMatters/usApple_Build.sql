-- US_Apple
INSERT INTO
	pmi_build.job_queue(db_name, build_group, client_id, status, processing_server_id, scheduled_start_timestamp) 
	SELECT
		db,
		build_group,
		client_id,
		'READY',
		0,
		now() 
	FROM
		pmi_build.job_schedule 
	WHERE
		client_id = 3100683 
		AND proc_name = 'etl_imp' LIMIT 1 ;


SELECT * from pmi_build.job_queue WHERE status <> 'Done' and db_name not LIKE '%pend' AND build_group < 10
ORDER BY created_time_stamp;
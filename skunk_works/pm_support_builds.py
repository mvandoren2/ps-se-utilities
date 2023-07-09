from sqlite3 import ProgrammingError
from progress.spinner import PieSpinner
import time
import mysql.connector
import getpass

# Actions 
def main():
    host = "opsdb-01.p2.pmstudent.powerschool.host"
    username = input("Username: ")
    password = getpass.getpass()

    try:
        conn = mysql.connector.connect(

        host=host,

        user=username,

        password=password

        )
    except mysql.connector.errors.ProgrammingError:
        print("Invalid Password, Try Again")
        return

    conn.autocommit = True
    cursor = conn.cursor()

    support_site_se_tenants = [
        {
            "db_name" : "tx_applegrove",
            "client_id" : "31009987"
        },
        {
            "db_name" : "us_apple",
            "client_id" : "3100683"
        },
        {
            "db_name" : "us_apple2",
            "client_id" : "3100860"
        },
        {
            "db_name" : "us_pssb",
            "client_id" : "31009660"
        },
    ]

    status_query_condition = ""

    for se_tenant in support_site_se_tenants:

        print(f"Kicking off build for {se_tenant['db_name']}.")

        if status_query_condition:
            status_query_condition += ", "

        cursor.execute(f"""
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
            client_id = {se_tenant['client_id']} 
            AND proc_name = 'etl_imp' LIMIT 1 ;"""
        )

        status_query_condition += f"'{se_tenant['db_name']}'"
    
    cursor.execute(f"select count(*) as pending from pmi_build.job_queue where status <> 'Done' and db_name not like '%pend' and build_group < 10 and db_name in ({status_query_condition});")
    result_set = cursor.fetchone()
    pending_builds = result_set[0]
    while True:
        if pending_builds == 0:
            break
        
        print(f"Pending Builds: {pending_builds}", end="\r")
        time.sleep(3)
        cursor.execute(f"select count(*) as pending from pmi_build.job_queue where status not in ('Done', 'Error') and db_name not like '%pend' and build_group < 10 and db_name in ({status_query_condition});")
        result_set = cursor.fetchone()
        pending_builds = result_set[0]

    print(f"No further pending builds for {status_query_condition} tenants. Done!")

if __name__ == '__main__':
    main()
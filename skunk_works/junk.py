command_steps = [
            {
            "Description" : "Updating ORACLE_HOSTNAME Variable.",
            "Command" : f"setx /M ORACLE_HOSTNAME 10.0.0.30"
            },
            {
            "Description" : "Updating ORACLE_HOSTNAME Variable.",
            "Command" : f"set ORACLE_HOSTNAME= 10.0.0.30"
            },
            {
            "Description" : "Updating Private IP in Oracle tsnames.ora.",
            "Command" : f"((Get-Content -path $Env:ORACLE_HOME\\network\\admin\\tnsnames.ora -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','10.0.0.30') | Set-Content -Path $Env:ORACLE_HOME\\network\\admin\\tnsnames.ora"
            },
            {
            "Description" : "Updating Private IP in Oracle listener.ora.",
            "Command" : f"((Get-Content -path $Env:ORACLE_HOME\\network\\admin\\listener.ora -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','10.0.0.30') | Set-Content -Path $Env:ORACLE_HOME\\network\\admin\\listener.ora"
            },
            {
            "Description" : "Updating Private IP in PowerSchool service.properties.",
            "Command" : f"((Get-Content -path \"C:\\Program Files\\PowerSchool\\configuration\\services\\oracle\\service.properties\" -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','10.0.0.30') | Set-Content -Path \"C:\\Program Files\\PowerSchool\\configuration\\services\\oracle\\service.properties\""
            },
            {
            "Description"  : "Updating Private IP in PowerSchool deployment.properties.",
            "Command" : f"((Get-Content -path \"C:\\Program Files\\PowerSchool\\configuration\\deployment.properties\" -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','10.0.0.30') | Set-Content -Path \"C:\\Program Files\\PowerSchool\\configuration\\deployment.properties\""
            },
            {
            "Description" : "Updating Private IP in Orchestrator oracle_listener_update.sql.",
            "Command" : f"((Get-Content -path $Env:ORCHESTRATOR_HOME\\oracle_listener_update.sql -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','10.0.0.30') | Set-Content -Path $Env:ORCHESTRATOR_HOME\\oracle_listener_update.sql"
            },
            {
            "Description" : "Starting Oracle TNS Listener.",
            "Command" : f"lsnrctl start"
            },
            {
            "Description": "Starting OracleService (This Takes Some Time.)",
            "Command" : f"Start-Service -Name \"OracleServicePSPRODDB\""
            },
            {
            "Description": "Starting OracleVssWriter.",
            "Command" : f"Start-Service -Name \"OracleVssWriterPSPRODDB\""
            },
            {
            "Description": "Starting OracleJobScheduler.",
            "Command" : f"Start-Service -Name \"OracleJobSchedulerPSPRODDB\""
            },
            {
            "Description" : "Starting PowerSchool Installer Service",
            "Command" : f"Start-Service -Name \"PearsonPowerSchoolInstaller\""
            },
            {
            "Description" : "Executing Orchestrator oracle_listener_update.sql.",
            "Command" : f"sqlplus / as sysdba '@%ORCHESTRATOR_HOME%\oracle_listener_update.sql'"
            },
            {
            "Description" : "Dropping PSPRODDB Schema",
            "Command": f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\dropschema psproddb"
            },
            {
            "Description" : "Importing Stock Data Pump",
            "Command" : f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\import psproddb stock.dmp y full"
            },
        ]

for step in command_steps:
    print(step["Command"])
    
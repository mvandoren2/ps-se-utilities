import boto3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum

# Enumerations
class PowerSchoolProduct(Enum):
    SIS = "SIS"
    ESCHOOLPLUS = "ESP"
    SCHOOLOGY = "SGY"
    PERFORMANCE_MATTERS = "PM"
    ENROLLMENT = "ENR"
    INSIGHTS = "UI"
    SPECIAL_PROGRAMS = "PSSP"
    ATTENDANCE_INTERVENTION = "AIS"


class TenantStatus(Enum):
    NEW = "NEW"
    INITIATIED = "INITIATIED"
    INSTANTIATED = "INSTANTIATED"
    PENDING_APPLICATION_INSTALLATION = "PENDING_APPLICATION_INSTALLATION"
    RESERVE = "RESERVE"
    ACTIVE = "ACTIVE"
    PENDING_SHUTDOWN = "PENDING_SHUTDOWN"
    RETAIN = "RETAIN"
    PENDING_RECYCLE = "PENDING_RECYCLE"
    PENDING_DECOMMISSION = "PENDING_DECOMMISSION"


# Data Classes
@dataclass(kw_only=True)
class OrchestratorTenant(ABC):
    common_name : str
    product : PowerSchoolProduct
    status: TenantStatus = TenantStatus.NEW


@dataclass(kw_only=True)
class SISTenant(OrchestratorTenant):
    ssm_available : bool = False
    aws_instance_id : str = ""
    aws_private_ip : str = ""
    aws_allocation_id : str = ""
    aws_public_ip : str = ""
    aws_target_group_arn : str = ""

    def __post_init__(self):
        self.product = PowerSchoolProduct.SIS


@dataclass(kw_only=True)
class PMTenant(OrchestratorTenant):
    core_files_rendered : bool = False
    measure_files_rendered : bool = False

    def __post_init__(self):
        self.product = PowerSchoolProduct.PERFORMANCE_MATTERS

@dataclass(kw_only=True)
class SISAWSConfiguration():
    ami_id : str = "ami-0b08b3ba32be91d3b"
    instance_type = "t3a.xlarge"
    key_name = "mvd-automate"
    iam_profile_instance_arn = "arn:aws:iam::558436896068:instance-profile/SE-Orchestrator"
    security_group_id = "sg-e405c199"
    vpc_id = "vpc-66a7f20f"
    subnet_id = "subnet-7ca7f215"
    availability_zone = "us-east-1a"
    load_balancer_arn = "arn:aws:elasticloadbalancing:us-east-1:558436896068:loadbalancer/app/orchestrator-alb-poc/3dc37c71547fc207"


# Orchestrators
class Orchestrator(ABC):


    @abstractmethod
    def provision_tenant(self, tenant : OrchestratorTenant) -> None:
        pass


    @abstractmethod
    def decommission_tenant(self, tenant : OrchestratorTenant) -> None:
        pass


class SISOrchestrator(Orchestrator):


    def __init__(self):
        self.ec2_resource = boto3.resource("ec2")
        self.ec2_client = boto3.client("ec2")
        self.route53_client = boto3.client("route53")
        self.elb_client = boto3.client('elbv2')
        self.ssm_client = boto3.client('ssm', region_name="us-east-1")
        self.aws_config = SISAWSConfiguration()


    def _await_ssm_availability(self, tenant : SISTenant):
        print(f"{tenant.common_name}: Awaiting SSM Availability.")
        if tenant.ssm_available == False:
            for i in range(1, 1000):
                response = self.ssm_client.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [tenant.aws_instance_id]}])
                if len(response["InstanceInformationList"]) > 0 and \
                        response["InstanceInformationList"][0]["PingStatus"] == "Online" and \
                        response["InstanceInformationList"][0]["InstanceId"] == tenant.aws_instance_id:
                    tenant.ssm_available = True
                    break
                time.sleep(1)


    def _run_powershell_command(self, tenant : SISTenant, powershell_command : str):
        
        if tenant.ssm_available:
            response = self.ssm_client.send_command( InstanceIds=[tenant.aws_instance_id], DocumentName="AWS-RunPowerShellScript", Parameters={'commands':[powershell_command]},)
            command_id = response['Command']['CommandId']
            waiter = self.ssm_client.get_waiter('command_executed')
            waiter.wait(
                CommandId=command_id,
                InstanceId=tenant.aws_instance_id,
                WaiterConfig={
                    'Delay': 2,
                    'MaxAttempts': 30000
                }
            )
            
        else:
            print(f"Instance {tenant.aws_instance_id} not listed as instance managed by AWS SSM")


    def _load_active_tenant_from_common_name(self, common_name : str) -> SISTenant:
        tenant = SISTenant(
            common_name=common_name,
            product=PowerSchoolProduct.SIS,
            status=TenantStatus.ACTIVE,
            ssm_available=True,
        )
        
        response = self.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        f'{tenant.common_name}',
                    ]
                },
            ],
        )

        try:
            tenant.aws_instance_id = response['Reservations'][0]['Instances'][0].get('InstanceId')
        except IndexError:
            print(f"{common_name}: No Instance with Name: {common_name}.")
            tenant.status = TenantStatus.NEW

        return tenant


    def _add_route53_record(self, tenant : SISTenant ) -> None:
        print(f"{tenant.common_name}: Updating Route53 DNS.")
        try:
            self.route53_client.change_resource_record_sets(
                HostedZoneId = 'Z2TZA0SF7FNEIO',
                ChangeBatch= {
                    'Comment': 'Add new instance to Route53',
                    'Changes': [
                        {
                            'Action': 'CREATE',
                            'ResourceRecordSet': {
                                'Name': f'{tenant.common_name}.powerschoolsales.com',
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [
                                {
                                    'Value': '107.21.33.158'
                                },
                                ],
                            }
                        },
                    ]
                }
            )
            print(f"{tenant.common_name}: Route53 Succssfully Updated!")              
        except:
            print("Something went wrong attempting to update Route53. Record Likely Already Exists.")


    def _update_orchestrator_status(self, tenant : SISTenant) -> None:
        response = self.ec2_client.create_tags(
            Resources=[
                tenant.aws_instance_id,
            ],
            Tags=[
                {
                    'Key': 'OrchestratorTenantStatus',
                    'Value': f"{tenant.status.value}"
                },
            ]
        )


    def _create_instance(self, tenant : SISTenant) -> None:
        print(f"{tenant.common_name}: Creating EC2 Instance for {tenant.common_name}.")

        instance = self.ec2_resource.create_instances(
                ImageId=self.aws_config.ami_id,
                MinCount=1,
                MaxCount=1,
                InstanceType=self.aws_config.instance_type,
                KeyName=self.aws_config.key_name,
                IamInstanceProfile={
                    'Arn': self.aws_config.iam_profile_instance_arn
                },
                TagSpecifications=[
                    {
                        "ResourceType": "instance",
                        "Tags": [
                            {
                                "Key": "Name",
                                "Value": f"{tenant.common_name}"
                            },
                            {
                                "Key": "Owner",
                                "Value": "Solution Engineering"
                            },
                            {
                                "Key": "Domain",
                                "Value": f"https://{tenant.common_name}.powerschoolsales.com"
                            },
                            {
                                "Key": "OrchestratorManaged",
                                "Value": "True"
                            },
                            {
                                "Key": "OrchestratorTenantStatus",
                                "Value": f"{tenant.status.value}"
                            },
                            {
                                "Key": "EffectiveDate",
                                "Value": f"{date.today()}"
                            },
                        ]
                    },
                ],
                SecurityGroupIds=[self.aws_config.security_group_id],
                SubnetId=self.aws_config.subnet_id
            )[0]
        
        instance.wait_until_running()
        tenant.aws_instance_id = instance.id
        tenant.aws_private_ip = instance.private_ip_address
        tenant.status = TenantStatus.INSTANTIATED
        self._update_orchestrator_status(tenant)


    def _execute_post_instantiation_commands(self, tenant : SISTenant):
        command_steps = [
            {
            "Description" : "Updating ORACLE_HOSTNAME Variable.",
            "Command" : f"setx /M ORACLE_HOSTNAME {tenant.aws_private_ip}"
            },
            {
            "Description" : "Updating ORACLE_HOSTNAME Variable.",
            "Command" : f"set ORACLE_HOSTNAME= {tenant.aws_private_ip}"
            },
            {
            "Description" : "Updating Private IP in Oracle tsnames.ora.",
            "Command" : f"((Get-Content -path $Env:ORACLE_HOME\\network\\admin\\tnsnames.ora -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','{tenant.aws_private_ip}') | Set-Content -Path $Env:ORACLE_HOME\\network\\admin\\tnsnames.ora"
            },
            {
            "Description" : "Updating Private IP in Oracle listener.ora.",
            "Command" : f"((Get-Content -path $Env:ORACLE_HOME\\network\\admin\\listener.ora -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','{tenant.aws_private_ip}') | Set-Content -Path $Env:ORACLE_HOME\\network\\admin\\listener.ora"
            },
            {
            "Description" : "Updating Private IP in PowerSchool service.properties.",
            "Command" : f"((Get-Content -path \"C:\\Program Files\\PowerSchool\\configuration\\services\\oracle\\service.properties\" -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','{tenant.aws_private_ip}') | Set-Content -Path \"C:\\Program Files\\PowerSchool\\configuration\\services\\oracle\\service.properties\""
            },
            {
            "Description"  : "Updating Private IP in PowerSchool deployment.properties.",
            "Command" : f"((Get-Content -path \"C:\\Program Files\\PowerSchool\\configuration\\deployment.properties\" -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','{tenant.aws_private_ip}') | Set-Content -Path \"C:\\Program Files\\PowerSchool\\configuration\\deployment.properties\""
            },
            {
            "Description" : "Updating Private IP in Orchestrator oracle_listener_update.sql.",
            "Command" : f"((Get-Content -path $Env:ORCHESTRATOR_HOME\\oracle_listener_update.sql -Raw) -replace 'POWERSCHOOLSISPRIVATEIP','{tenant.aws_private_ip}') | Set-Content -Path $Env:ORCHESTRATOR_HOME\\oracle_listener_update.sql"
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
            "Description" : "Setting OracleTNSListener Service to Automatic.",
            "Command" : f"Set-Service -Name \"OracleOH19000TNSListener\" -StartupType Automatic"
            },
            {
            "Description" : "Setting OracleService to Automatic.",
            "Command" : f"Set-Service -Name \"OracleServicePSPRODDB\" -StartupType Automatic"
            },
            {
            "Description" : "Setting TNS OracleJobScheduler Service to Automatic.",
            "Command" : f"Set-Service -Name \"OracleJobSchedulerPSPRODDB\" -StartupType Automatic"
            },
            {
            "Description": "Setting OracleVssWriter Service to Automatic.",
            "Command" : f"Set-Service -Name \"OracleVssWriterPSPRODDB\" -StartupType Automatic"
            },
            {
            "Description" : "Setting PowerSchool Installer Service to Automatic.",
            "Command" : f"Set-Service -Name \"PearsonPowerSchoolInstaller\" -StartupType Automatic"
            },
        ]
    
        print(f"{tenant.common_name}: Executing PowerShell Commands")
        for step in command_steps:
            self._run_powershell_command(tenant, step["Command"])
        print(f"{tenant.common_name}: PowerShell Commands Executed Successfully")


    def _restore_stock_database(self, tenant : SISTenant):
        command_steps = [
                {
                "Description" : "Dropping PSPRODDB Schema",
                "Command": f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\dropschema psproddb"
                },
                {
                "Description" : "Importing Stock Data Pump",
                "Command" : f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\import psproddb stock.dmp y full"
                }
        ]
        print(f"{tenant.common_name}: Executing PowerShell Commands")
        for step in command_steps:
            self._run_powershell_command(tenant, step["Command"])
        print(f"{tenant.common_name}: PowerShell Commands Executed Successfully")


    def provision_tenant(self, tenant : SISTenant, restore_stock_schema : bool=False, stop_after_provisioning : bool=True) -> None:

        self._create_instance(tenant)
        self._await_ssm_availability(tenant)
        self._execute_post_instantiation_commands(tenant)        

        if restore_stock_schema:
            self._restore_stock_database(tenant)
            
        tenant.status = TenantStatus.PENDING_APPLICATION_INSTALLATION
        self._update_orchestrator_status(tenant)

        if stop_after_provisioning:
            print(f"{tenant.common_name}: Stopping Instance")
            self.ec2_client.stop_instances(
                InstanceIds=[tenant.aws_instance_id]
            )


    def decommission_tenant(self, tenant : SISTenant) -> None:
        
        if tenant.status == TenantStatus.PENDING_RECYCLE:
            tenant = self._load_active_tenant_from_common_name(tenant.common_name)

        if tenant.status == TenantStatus.ACTIVE:
            print(f"{tenant.common_name}: Terminating Instance {tenant.aws_instance_id}")
            try:        
                response = self.ec2_client.terminate_instances(
                    InstanceIds=[
                        tenant.aws_instance_id,
                    ]
                )
            except:
                print("Something went wrong attempting to terminate the instance.")

            print(f"{tenant.common_name}: Terminated")


    def recycle_tenant(self, tenant : SISTenant) -> None:
        if tenant.status == TenantStatus.PENDING_RECYCLE:
            replacement_tenant = SISTenant(common_name=tenant.common_name, product=tenant.product)
            self.decommission_tenant(tenant)
            self.provision_tenant(replacement_tenant)


class PMOrchestrator(Orchestrator):


    def provision_tenant(self, tenant : PMTenant) -> None:
        print("Directions to Provision PM Tenant HERE")


    def decommission_tenant(self, tenant : PMTenant) -> None:
        print("Directions to Decommission PM Tenant HERE")
    

# Actions 
def main():
    orchestrator = SISOrchestrator()
    subdomain = "pssb2"
    orchestrator.recycle_tenant(SISTenant(common_name=subdomain, product=PowerSchoolProduct.SIS, status=TenantStatus.PENDING_RECYCLE))
    

if __name__ == '__main__':
    main()
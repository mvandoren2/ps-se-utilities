import boto3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

# Enumerations
class PowerSchoolProduct(Enum):
    SIS = "sis"
    ESCHOOLPLUS = "esp"
    SCHOOLOGY = "sgy"
    ENROLLMENT = "enr"
    INSIGHTS = "ui"
    SPECIAL_PROGRAMS = "pssp"


class TenantStatus(Enum):
    NEW = "new"
    PARTIALLY_COMPLETE = "partially_complete"
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_DECOMMISSION = "pending_decommission"
    PENDING_UPGRADE = "pending_upgrade"


# Data Classes
@dataclass(kw_only=True)
class OrchestratorTenant(ABC):
    common_name : str
    orchestrator_tenant_id : str
    product : PowerSchoolProduct
    status: TenantStatus


@dataclass(kw_only=True)
class SISTenant(OrchestratorTenant):
    ssm_available : bool = False
    aws_instance_id : str = ""
    aws_private_ip : str = ""
    aws_allocation_id : str = ""
    aws_public_ip : str = ""


@dataclass(kw_only=True)
class SISAWSConfiguration():
    ami_id : str = "ami-03f65bdb6e46e3ec9"
    instance_type = "t3a.xlarge"
    key_name = "mvd-automate"
    iam_profile_instance_arn = "arn:aws:iam::558436896068:instance-profile/SE-Orchestrator"
    security_group_id = "sg-e405c199"
    subnet_id = "subnet-7ca7f215"


# Orchestrators
class Orchestrator(ABC):


    @abstractmethod
    def provision_tenant(self, tenant : OrchestratorTenant) -> None:
        pass


    @abstractmethod
    def decommission_tenant(self, tenant : OrchestratorTenant) -> None:
        pass


    @abstractmethod
    def list_tenants(self) -> list[OrchestratorTenant]:
        pass


class SISOrchestrator(Orchestrator):


    def __init__(self):
        self.ec2_resource = boto3.resource("ec2")
        self.ec2_client = boto3.client("ec2")
        self.route53_client = boto3.client("route53")
        self.ssm_client = boto3.client('ssm', region_name="us-east-1")
        self.aws_config = SISAWSConfiguration()


    def _await_ssm_availability(self, tenant : SISTenant):
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
            print(f"{tenant.common_name}: Sent Command {powershell_command}")
        else:
            print(f"Instance {tenant.aws_instance_id} not listed as instance managed by AWS SSM")


    def _load_active_tenant_from_common_name(self, common_name : str) -> SISTenant:
        tenant = SISTenant(
        common_name=common_name,
        orchestrator_tenant_id=common_name,
        product=PowerSchoolProduct.SIS,
        status=TenantStatus.ACTIVE,
        ssm_available=True,
        )
        
        response = self.ec2_client.describe_addresses(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        f'{tenant.common_name}',
                    ]
                },
            ],
        )
        tenant.aws_public_ip = response['Addresses'][0].get('PublicIp')
        tenant.aws_instance_id = response['Addresses'][0].get('InstanceId')
        tenant.aws_allocation_id = response['Addresses'][0].get('AllocationId')

        return tenant


    def provision_tenant(self, tenant : SISTenant) -> None:

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
                        ]
                    },
                ],
                SecurityGroupIds=[self.aws_config.security_group_id],
                SubnetId=self.aws_config.subnet_id
            )[0]
        
        instance.wait_until_running()
        tenant.aws_instance_id = instance.id
        tenant.aws_private_ip = instance.private_ip_address
        print(f"{tenant.common_name}: EC2 Running. Instance ID: {tenant.aws_instance_id}")

        print(f"{tenant.common_name}: Associating Elastic IP.")
        addresses_dict = self.ec2_client.describe_addresses(
            Filters=[
                {
                    'Name': 'tag:OrchestratorManaged',
                    'Values': [
                        f'True',
                    ]
                },
            ],
        )
        for eip_dict in addresses_dict["Addresses"]:
            if not eip_dict.get("InstanceId"):
                tenant.aws_allocation_id = eip_dict.get("AllocationId")
                tenant.aws_public_ip = eip_dict.get('PublicIp')
                try:
                    self.ec2_client.associate_address(
                        DryRun=False,
                        InstanceId=tenant.aws_instance_id,
                        AllocationId=tenant.aws_allocation_id
                    )
                    self.ec2_client.create_tags(
                        Resources=[
                            tenant.aws_allocation_id,
                        ],
                        Tags=[
                            {
                                'Key': 'Name',
                                'Value': f'{tenant.common_name}'
                            },
                            {
                                "Key": "OrchestratorManaged",
                                "Value": "True"
                            },
                        ]
                    )
                    print(f"{tenant.common_name}: Elastic IP Associated. Allocation ID: {tenant.aws_allocation_id} Public IP: {tenant.aws_public_ip}")
                except:
                    print("Something went wrong trying to associate an Elastic IP. Are we out of Elastic IPs?")
                    break

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
                                            'Value': eip_dict.get("PublicIp")
                                        },
                                        ],
                                    }
                                },
                            ]
                        }
                    )
                    print(f"{tenant.common_name}: Route53 Succssfully Updated! {tenant.common_name}.powerschoolsales.com is now accessible via RDP.")    
                            
                except:
                    print("Something went wrong attempting to update Route53")
                    break
                
                self._await_ssm_availability(tenant=tenant)

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
                    "Description":"Starting OracleJobScheduler.",
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
                    "Description" :"Setting OracleTNSListener Service to Automatic.",
                    "Command" : f"Set-Service -Name \"OracleOH19000TNSListener\" -StartupType Automatic"
                    },
                    {
                    "Description" :"Setting OracleService to Automatic.",
                    "Command" : f"Set-Service -Name \"OracleServicePSPRODDB\" -StartupType Automatic"
                    },
                    {
                    "Description" :"Setting TNS OracleJobScheduler Service to Automatic.",
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
                    # {
                    # "Description" : "Dropping PSPRODDB Schema",
                    # "Command": f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\dropschema psproddb"
                    # },
                    # {
                    # "Description" :"Importing Stock Data Pump",
                    # "Command" : f"cd c:\\oracle\\scripts ; c:\\oracle\\scripts\\import psproddb stock.dmp y full"
                    # }
                ]

                for step in command_steps:
                    print(f"{tenant.common_name}: {step['Description']}")
                    self._run_powershell_command(tenant, step["Command"])

                break
                
        print(f"{tenant.common_name}: Pending PowerSchool Installation")


    def decommission_tenant(self, tenant : SISTenant) -> None:
        
        try:
            tenant = self._load_active_tenant_from_common_name(tenant.common_name)
        except IndexError:
            print(f"{tenant.common_name} doesn't seem to exist for decommissioning.")
            return

        print(f"{tenant.common_name}: Decommissioning {tenant.common_name}.")
        try:
            self.route53_client.change_resource_record_sets(
                HostedZoneId = 'Z2TZA0SF7FNEIO',
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': {
                                'Name': f'{tenant.common_name}.powerschoolsales.com',
                                'Type': 'A',
                                'TTL': 300,
                                'ResourceRecords': [
                                {
                                    'Value': tenant.aws_public_ip
                                },
                                ],
                            }
                        }
                    ]
                }
            )
        except:
            print(f"{tenant.common_name}: Something went wrong attempting to update Route53")
        try:        
            self.ec2_client.disassociate_address(
                PublicIp=tenant.aws_public_ip
            )
            self.ec2_client.create_tags(
                        Resources=[
                            tenant.aws_allocation_id,
                        ],
                        Tags=[
                            {
                                'Key': 'Name',
                                'Value': 'AVAILABLE'
                            },
                            {
                                "Key": "OrchestratorManaged",
                                "Value": "True"
                            },
                        ]
                    )
        except:
            print(f"{tenant.common_name}: Something went wrong disassociating the Elastic IP")
        try:        
            response = self.ec2_client.terminate_instances(
                InstanceIds=[
                    tenant.aws_instance_id,
                ]
            )
        except:
            print("Something went wrong attempting to terminate the instance.")

        print(f"{tenant.common_name}: Decommissioned!")


    def list_tenants(self) -> list[SISTenant]:
        print("SISOrchestrator.list_tenants() is not yet implemented.")
        return []

# Actions 
def main():
    orchestrator = SISOrchestrator()
    decommission_list = []
    provision_list = ["zephyr-ami-intermediate-stage"]
    for subdomain in decommission_list:
        orchestrator.decommission_tenant(SISTenant(common_name=subdomain, orchestrator_tenant_id=subdomain, product=PowerSchoolProduct.SIS, status=TenantStatus.PENDING_DECOMMISSION))
    for subdomain in provision_list:
        tic = time.perf_counter()
        orchestrator.provision_tenant(SISTenant(common_name=subdomain, orchestrator_tenant_id=subdomain, product=PowerSchoolProduct.SIS, status=TenantStatus.NEW))
        toc = time.perf_counter()
        print(f"{subdomain}: provisioned in {toc - tic:0.4f} seconds.")

if __name__ == '__main__':
    main()
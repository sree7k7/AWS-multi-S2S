
import os
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct
from aws_multi_s2_s.parameters import cidr_mask, vpc_cidr, destinationCIDR

class CustomVpcStack(Stack):        
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        custom_vpc = ec2.Vpc(
            self,
            "CustomVpc",
            cidr=vpc_cidr,
            max_azs=1,
            nat_gateways=0,            
            subnet_configuration = [
                ec2.SubnetConfiguration(
                    name="PublicSubnetA",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=cidr_mask
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnetB",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,                    
                    cidr_mask=cidr_mask
                )
            ]
        )
### ----- vpn connection 1-----
        AWSVGWToAzureInstance0 = custom_vpc.add_vpn_connection("AWSVGWToAzureInstance0",
            ip = "20.223.100.224", # CGW IP
            # asn=65020,
            tunnel_options=[
                ec2.VpnTunnelOption(
                tunnel_inside_cidr="169.254.21.0/30"
            ),
                ec2.VpnTunnelOption(
                tunnel_inside_cidr="169.254.22.0/30"                   
            )
        ]
    )

### -----VPN bgp connection 2 -----
        AWSVGWToAzureInstance1 = custom_vpc.add_vpn_connection("AWSVGWToAzureInstance1",
            ip="20.223.101.71", # CGW IP
            asn=65000,
            tunnel_options=[
                ec2.VpnTunnelOption(
                tunnel_inside_cidr="169.254.21.4/30"
            ),
                ec2.VpnTunnelOption(
                tunnel_inside_cidr="169.254.22.4/30"                   
            )
        ]
    )
#### ---------- VPC endpoints -------------- ####
        S3endpointGateway = ec2.GatewayVpcEndpoint(self, "S3endpoint",
            vpc=custom_vpc,
            service=ec2.InterfaceVpcEndpointService("com.amazonaws.eu-central-1.s3", 443)
                    )
        ssmmessages = ec2.InterfaceVpcEndpoint(self, "ssmmessages",
            vpc=custom_vpc,
            service=ec2.InterfaceVpcEndpointService("com.amazonaws.eu-central-1.ssmmessages", 443
            )
        )
        VPCEndpointEC2 = ec2.InterfaceVpcEndpoint(self, "VPCEndpointEC2",
            vpc=custom_vpc,
            service=ec2.InterfaceVpcEndpointService("com.amazonaws.eu-central-1.ec2", 443)
        )
        VPCEndpointec2messages = ec2.InterfaceVpcEndpoint(self, "VPCEndpointec2messages",
            vpc=custom_vpc,
            service=ec2.InterfaceVpcEndpointService("com.amazonaws.eu-central-1.ec2messages", 443)
        )
        VPCEndpointssm = ec2.InterfaceVpcEndpoint(self, "VPCEndpointssm",
            vpc=custom_vpc,
            service=ec2.InterfaceVpcEndpointService("com.amazonaws.eu-central-1.ssm", 443)        
        )
####---------- ec2 role---------- ##########
        role = iam.Role(
            self,
            "BackupRole",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2FullAccess'),
            ],
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com')
        )
# ####----------  security Group ----------#####
        sg_group = ec2.SecurityGroup(self, 'BackupSG', vpc=custom_vpc,
        )
        sg_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(destinationCIDR),
            connection=ec2.Port(
                from_port=22,
                to_port=22,
                protocol=ec2.Protocol.TCP,
                string_representation='SSH'
            )
        )
        sg_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc_cidr),
            connection=ec2.Port(
                from_port=443,
                to_port=443,
                protocol=ec2.Protocol.TCP,
                string_representation='HTTPS'
            )
        )
        sg_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(destinationCIDR),
            connection=ec2.Port(
                from_port=-1,
                to_port=-1,
                protocol=ec2.Protocol.ICMP,
                string_representation='ICMP'
            )
        )         

###---------- EC2 ----------###

        user_data = f'''
            #!/bin/bash
            amazon-linux-extras install epel -y
            '''
        instance = ec2.Instance(
            self,
            'Instance',
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL),
            vpc=custom_vpc,
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2022
            ),
            security_group=sg_group,
            role=role,
            user_data=ec2.UserData.custom(user_data),
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            propagate_tags_to_volume_on_creation=True,
            block_devices=[
                ec2.BlockDevice(
                device_name="/dev/xvda",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size= 10,
                    volume_type= ec2.EbsDeviceVolumeType.GP3
                )
            )
            ]                 
        )
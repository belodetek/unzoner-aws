# unzoner-aws
> CloudFormation templates to deploy black.box Unzoner backend(s) into AWS

## ToC
* [AWS account](#aws-account)
* [load environment](#load-environment)
* [install requirements](#install-requirements)
* [configure](#configure)
* [package](#package)
* [create-update stack(s)](#create-update-stack)
* [retrieve variables](#retrieve-variables)
* [deploy backend(s)](#deploy-backends)
* [miscellaneous](#miscellaneous)


## AWS account
> done once per year to maintain free tier discount

* create a [free](https://aws.amazon.com/free/) AWS account and login
* grant `AdministratorAccess` policy to `org-admin` role for use by your master AWS
  account with maximum (12 hours) duration
* note down the new [<aws_account_id>](https://console.aws.amazon.com/billing/home?#/account)


## load environment
> See, [environment-variables](https://github.com/belodetek/black.box/tree/master/unzoner#environment-variables)

## install requirements
> activate root Python virtualenv

    ./update-modules.sh

    python3 -m venv venv

    . venv/bin/activate

    pip install --upgrade pip setuptools wheel

    pip install --upgrade awscli


## configure
> check `~/.aws/config`

    [profile {{DNS_SUB_DOMAIN}}]
    region = {{AWS_REGION}}
    source_profile = default
    role_arn = arn:aws:iam::<aws_account_id>:role/<admin-role>


## package
> check if bucket already exists

    bucket=$(uuid)
    aws s3 mb s3://${bucket}


### custom resource provider
> requires Docker and deactivation of root virtualenv

    pushd cfn-generic-custom-resource/generic_provider \
      && python3 -m venv venv \
      && . venv/bin/activate \
      && pip install --upgrade pip setuptools wheel \
      && pip install -Ur ../requirements.txt -t . \
      && make && popd


### CFN templates

    aws cloudformation package \
      --template-file main-template.yml \
      --s3-bucket ${bucket} \
      --output-template-file main.yml


## create-update stack
> first time deploy in order: `SecretsStack`, `{IAM,S3}Stack` and `{KMS,VPC,Lamda}Stack`;
  then everything else; do `EBSStack` last

    stack_name="${DNS_SUB_DOMAIN}-${ENV}"


    solution_stack="$(aws elasticbeanstalk list-available-solution-stacks \
      | jq -r '.SolutionStacks[]'\
      | grep -E '^64bit Amazon Linux\s2\s.*\srunning Python\s3.8$' | head -n 1)"

    ebs_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"EBSStackName-${stack_name}\").Value")

    ebs_app=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Application-${ebs_stack}\").Value")

    ebs_backend_env=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Backend-${ebs_stack}\").Value")

    ebs_frontend_env=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Frontend-${ebs_stack}\").Value")

    backend_version_label=$(aws elasticbeanstalk describe-environments \
      --environment-name ${ebs_backend_env} | jq -r .Environments[].VersionLabel)

    frontend_version_label=$(aws elasticbeanstalk describe-environments \
      --environment-name ${ebs_frontend_env} | jq -r .Environments[].VersionLabel)

    backend_app_bundle=$(aws elasticbeanstalk describe-application-versions \
      --application-name ${ebs_app} | jq -r --arg vl "$backend_version_label" '.ApplicationVersions[] | select(.VersionLabel==$vl).SourceBundle.S3Key')

    frontend_app_bundle=$(aws elasticbeanstalk describe-application-versions \
      --application-name ${ebs_app} | jq -r --arg vl "$frontend_version_label" '.ApplicationVersions[] | select(.VersionLabel==$vl).SourceBundle.S3Key')

    date +%s > eb-python-flask/.ts


    aws cloudformation deploy \
      --stack-name ${stack_name} \
      --template-file main.yml \
      --s3-bucket ${bucket} \
      --capabilities CAPABILITY_NAMED_IAM \
      --parameter-overrides \
      SolutionStackName="${solution_stack}" \
      BackendAppBundle=${backend_app_bundle} \
      FrontendAppBundle=${frontend_app_bundle} \
      AppIds=${RESIN_APP_ID} \
      DomainName=${DNS_DOMAIN} \
      SecretsTemplate=true \
      S3Template=false \
      IAMTemplate=false \
      VPCTemplate=false \
      KMSTemplate=false \
      LambdaTemplate=false \
      PasswordTemplate=false \
      R53Template=false \
      AlertTemplate=false \
      CloudWatchTemplate=false \
      SGTemplate=false \
      ACMTemplate=false \
      RDSTemplate=false \
      ECTemplate=false \
      EBSTemplate=false \
      --tags \
      Name=${stack_name} \
      --no-execute-changeset


## retrieve variables

    s3_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"S3StackName-${stack_name}\").Value")

    iam_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"IAMStackName-${stack_name}\").Value")

    lambda_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"LambdaStackName-${stack_name}\").Value")

    ebs_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"EBSStackName-${stack_name}\").Value")

    rds_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"RDSStackName-${stack_name}\").Value")

    ec_stack=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"ECStackName-${stack_name}\").Value")

    rds_hostname=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"${rds_stack}-DNSName\").Value")

    rds_password=$(aws ssm get-parameter --with-decryption\
      --name /${stack_name}/RDS_PASSWORD | jq -r '.Parameter.Value')

    rds_instance=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"${rds_stack}-InstanceName\").Value")

    cache_host=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"${ec_stack}-PrimaryEndPointAddress\").Value")

    images_bucket=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"ImagesBucket-${s3_stack}\").Value")

    access_key=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"AccessKey-${iam_stack}\").Value")

    secret_access_key_path=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"SecretAccessKey-${iam_stack}\").Value")

    secret_access_key=$(aws ssm get-parameter --with-decryption \
      --name ${secret_access_key_path} | jq -r '.Parameter.Value')

    api_secret=$(aws ssm get-parameter --with-decryption \
      --name /${stack_name}/API_SECRET | jq -r '.Parameter.Value')

    ebs_app=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Application-${ebs_stack}\").Value")

    ebs_backend_env=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Backend-${ebs_stack}\").Value")

    ebs_backend_env_id=$(aws elasticbeanstalk describe-environments \
      | jq -r ".Environments[] | select(.ApplicationName==\"${ebs_app}\" and .EnvironmentName==\"${ebs_backend_env}\").EnvironmentId" \
      | awk -F'-' '{print $2}')

    ebs_frontend_env=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"Frontend-${ebs_stack}\").Value")

    ebs_frontend_env_id=$(aws elasticbeanstalk describe-environments \
      | jq -r ".Environments[] | select(.ApplicationName==\"${ebs_app}\" and .EnvironmentName==\"${ebs_frontend_env}\").EnvironmentId" \
      | awk -F'-' '{print $2}')

    on_demand_base_capacity=$(aws cloudformation describe-stacks \
      --stack-name ${ebs_stack} \
      | jq -r '.Stacks[].Parameters[] | select(.ParameterKey=="OnDemandBaseCapacity").ParameterValue')

    on_demand_percentage_above_base_capacity=$(aws cloudformation describe-stacks \
      --stack-name ${ebs_stack} \
      | jq -r '.Stacks[].Parameters[] | select(.ParameterKey=="OnDemandPercentageAboveBaseCapacity").ParameterValue')


## deploy backends

### unzoner-api
> change `API_SECRET` back to previous value if re-deploying to a new AWS account

    git clone git@github.com:belodetek/unzoner-api.git

    pushd unzoner-api && git pull

    python3 -m venv venv

    . venv/bin/activate

    pip install --upgrade pip setuptools wheel

    pip install -Ur requirements.txt


#### Elastic Beanstalk application

    eb init --interactive --profile ${AWS_PROFILE} --region ${AWS_REGION}

    for env in $(cat .ebextensions/environment.template \
      | grep -E '^.*:\s[^\n]' | awk -F':' '{print $1}' | xargs echo); do unset $env; done

    # (re)source env vars (e.g.) env-dev

    cat .ebextensions/environment.template | envsubst \
      | grep -E 'option_settings:|aws:|^.*:\s[^\n]' > .ebextensions/environment.config

    cat .ebextensions/environment.config

    eb deploy


#### mixed instances policy

    asg=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"BackendAutoScalingGroupName-${ebs_stack}\").Value")

    lc=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"BackendLaunchConfigurationName-${ebs_stack}\").Value")

    lt=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"BackendLaunchTemplateId-${ebs_stack}\").Value")

    instance_size=$(aws cloudformation describe-stacks\
      --stack-name ${ebs_stack}\
      | jq -r '.Stacks[].Parameters[] | select(.ParameterKey=="InstanceSizeSpot").ParameterValue')

    mixed_instances_policy=$(echo """{
        \"LaunchTemplate\": {
          \"LaunchTemplateSpecification\": {
            \"LaunchTemplateId\": \"${lt}\",
            \"Version\": \"1\"
          },
          \"Overrides\": [
            {
              \"InstanceType\": \"t2.nano\"
            },
            {
              \"InstanceType\": \"t3.nano\"
            },
            {
              \"InstanceType\": \"t3a.nano\"
            },
            {
              \"InstanceType\": \"${instance_size}\"
            }
          ]
        },
        \"InstancesDistribution\": {
          \"OnDemandBaseCapacity\": ${on_demand_base_capacity},
          \"OnDemandPercentageAboveBaseCapacity\": ${on_demand_percentage_above_base_capacity}
        }
      }""" | jq -c)

    echo ${mixed_instances_policy} | jq .

    aws autoscaling update-auto-scaling-group \
      --auto-scaling-group-name ${asg} \
      --mixed-instances-policy "${mixed_instances_policy}"


#### database

    instance_id=$(eb status --verbose | grep healthy\
      | awk -F':' '{print $1}' | head -n 1 | sed "s/^[ \t]*//")

    command_id=$(aws ssm send-command --output text \
      --instance-ids ${instance_id} \
      --document-name "AWS-RunShellScript" \
      --parameters '{"commands":[ "cd /var/app/current", "export $(sudo cat /opt/elasticbeanstalk/deployment/env)", "src/db_create.py", "mysql -h ${RDS_HOSTNAME} -u admin -p${RDS_PASSWORD} -D ebdb < db/purge.mysql" ]}' \
      --query "Command.CommandId")

    aws ssm list-commands --command-id ${command_id} | jq .

    aws ssm list-command-invocations --command-id ${command_id} --details | jq .

    aws rds reboot-db-instance \
      --db-instance-identifier ${rds_instance}


### unzoner-dashboard
> change `API_SECRET` back to previous if re-deploying to a new AWS account

    git clone git@github.com:belodetek/unzoner-dashboard.git

    pushd unzoner-dashboard && git pull

    python3 -m venv venv

    . venv/bin/activate

    pip install --upgrade pip

    pip install -Ur requirements.txt


#### Elastic Beanstalk application

    eb init --interactive --profile ${AWS_PROFILE} --region ${AWS_REGION}

    for env in $(cat .ebextensions/environment.template \
      | grep -E '^.*:\s[^\n]' | awk -F':' '{print $1}' | xargs echo); do unset $env; done

    # (re)source env vars (e.g.) env-dev

    cat .ebextensions/environment.template | envsubst \
      | grep -E 'option_settings:|aws:|^.*:\s[^\n]' > .ebextensions/environment.config

    cat .ebextensions/environment.config

    eb deploy


#### mixed instances policy

    asg=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"FrontendAutoScalingGroupName-${ebs_stack}\").Value")

    lc=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"FrontendLaunchConfigurationName-${ebs_stack}\").Value")

    lt=$(aws cloudformation list-exports \
      | jq -r ".Exports[] | select(.Name==\"FrontendLaunchTemplateId-${ebs_stack}\").Value")

    instance_size=$(aws cloudformation describe-stacks \
      --stack-name ${ebs_stack}\
      | jq -r '.Stacks[].Parameters[] | select(.ParameterKey=="InstanceSize").ParameterValue')

    # AWS Free Tier allowance
    on_demand_base_capacity=1

    mixed_instances_policy=$(echo """{
        \"LaunchTemplate\": {
          \"LaunchTemplateSpecification\": {
            \"LaunchTemplateId\": \"${lt}\",
            \"Version\": \"1\"
          },
          \"Overrides\": [
            {
              \"InstanceType\": \"t2.micro\"
            },
            {
              \"InstanceType\": \"${instance_size}\"
            }
          ]
        },
        \"InstancesDistribution\": {
          \"OnDemandBaseCapacity\": ${on_demand_base_capacity},
          \"OnDemandPercentageAboveBaseCapacity\": ${on_demand_percentage_above_base_capacity}
        }
      }""" | jq -c)

    echo ${mixed_instances_policy} | jq .

    aws autoscaling update-auto-scaling-group \
      --auto-scaling-group-name ${asg} \
      --mixed-instances-policy "${mixed_instances_policy}"


## miscellaneous
> manual steps

* [manually](https://github.com/aws/elastic-beanstalk-roadmap/issues/167) enable IPv6 on LBs
* update your DNS CNAME records
* update AWS authentication on your management host(s)
* update video playback test profiles


### SSM console

    aws ssm start-session --target ${instance_id}


### SSH

    aws ssm get-parameter --with-decryption\
      --name /rsa-private-keys/${ebs_stack}/id_rsa | jq -r '.Parameter.Value'\
      | openssl rsa > id_rsa && chmod 0600 id_rsa

    public_dns_name=$(aws ec2 describe-instances\
      --instance-ids ${instance_id}\
      --query 'Reservations[0].Instances[0].[PublicDnsName]' --output text)

    ssh -i id_rsa ec2-user@${public_dns_name}

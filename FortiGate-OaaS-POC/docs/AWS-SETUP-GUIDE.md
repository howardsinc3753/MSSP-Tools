# AWS Account & CLI Setup Guide

New to AWS? This guide walks you through creating an account and getting your API keys so you can run the OaaS POC deployment.

## 1. Create an AWS Account

1. Go to [https://aws.amazon.com](https://aws.amazon.com) and click **Create an AWS Account**
2. Enter your email, choose an account name, and verify your email
3. Enter your contact info (choose **Business** account type if using a company card)
4. Enter a credit card (you won't be charged until you use resources - this POC costs ~$0.52/day)
5. Verify your phone number
6. Choose **Basic Support** (free)
7. Sign in to the [AWS Console](https://console.aws.amazon.com)

## 2. Create an IAM User for API Access

Don't use your root account for day-to-day work. Create a dedicated IAM user:

1. In the AWS Console, search for **IAM** and open it
2. Click **Users** > **Create user**
3. User name: `oaas-poc-admin` (or whatever you like)
4. Check **Provide user access to the AWS Management Console** (optional - for web UI access)
5. Click **Next**
6. Select **Attach policies directly**
7. Search for and check these policies:
   - `AmazonEC2FullAccess`
   - `AmazonVPCFullAccess`
8. Click **Next** > **Create user**

## 3. Create API Access Keys

1. Click on your new user name to open their details
2. Go to the **Security credentials** tab
3. Scroll to **Access keys** > click **Create access key**
4. Select **Command Line Interface (CLI)**
5. Check the confirmation box and click **Next** > **Create access key**
6. **Save both values now** - the Secret Access Key is only shown once:
   - `Access key ID` (looks like: `AKIAIOSFODNN7EXAMPLE`)
   - `Secret access key` (looks like: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)

## 4. Install the AWS CLI

**Windows:**
Download and run the installer: [https://awscli.amazonaws.com/AWSCLIV2.msi](https://awscli.amazonaws.com/AWSCLIV2.msi)

**Mac:**
```bash
brew install awscli
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify it works:
```bash
aws --version
```

## 5. Configure Your Credentials

```bash
aws configure
```

It will prompt you for four things:
```
AWS Access Key ID:     <paste your access key>
AWS Secret Access Key: <paste your secret key>
Default region name:   us-east-1
Default output format: json
```

Verify it works:
```bash
aws sts get-caller-identity
```

You should see your account ID and user ARN.

## 6. Create an SSH Key Pair

You need a key pair to SSH into the FortiGates:

```bash
aws ec2 create-key-pair \
  --key-name oaas-poc-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/oaas-poc-key.pem
```

Set permissions (Mac/Linux):
```bash
chmod 400 ~/.ssh/oaas-poc-key.pem
```

Remember the key name (`oaas-poc-key`) - you'll enter it during deployment.

## 7. Install Terraform

**Windows:**
Download from [https://developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install) and add to your PATH.

**Mac:**
```bash
brew install terraform
```

**Linux:**
```bash
sudo apt-get update && sudo apt-get install -y terraform
```

Verify:
```bash
terraform version
```

## 8. Accept the FortiGate Marketplace Subscription

1. Open [FortiGate BYOL ARM64 on AWS Marketplace](https://aws.amazon.com/marketplace/pp?sku=33ndn84xbrajb9vmu5lxnfpjq)
2. Click **Continue to Subscribe**
3. Click **Accept Terms**
4. Wait 2-3 minutes for it to activate

This is free - BYOL means you bring your own FortiFlex license.

## You're Ready!

Go back to the main [README](../README.md) and run:

```bash
bash deploy.sh
```

The guided script handles everything from here.

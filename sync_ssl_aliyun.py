# -*- coding: utf-8 -*-
import os
import sys
import time
from typing import List
from dotenv import load_dotenv

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_cdn20180510 import client as cdn_client
from alibabacloud_cdn20180510 import models as cdn_models
from alibabacloud_dcdn20180115 import client as dcdn_client
from alibabacloud_dcdn20180115 import models as dcdn_models
from alibabacloud_cas20200407 import client as cas_client
from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_tea_util import models as util_models

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"Loaded configuration from {dotenv_path}")
else:
    # Fallback to default load_dotenv behavior or warning
    load_dotenv()
    print(f"Warning: Explicit .env file not found at {dotenv_path}, trying default load")


# Configuration
BASE_SSL_PATH = os.getenv('BASE_SSL_PATH', '/etc/nginx/ssl')

# Get target domains from environment variable, fallback to default list if not set
TARGET_DOMAINS_ENV = os.getenv('TARGET_DOMAINS')
if TARGET_DOMAINS_ENV:
    TARGET_DOMAINS = [d.strip() for d in TARGET_DOMAINS_ENV.split(',') if d.strip()]
else:
    TARGET_DOMAINS = [
        'agilestudio.cn',
        '52cmajor.com',
        '33subs.com'
    ]

REGION_ID = os.getenv('REGION_ID', 'cn-hangzhou')  # Default region, though CDN/DCDN are global usually

def create_cdn_client() -> cdn_client.Client:
    """
    Initialize Alibaba Cloud CDN Client
    """
    access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    
    if not access_key_id or not access_key_secret:
        raise ValueError("Please set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET environment variables")

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )
    # Endpoint for CDN
    config.endpoint = f'cdn.aliyuncs.com'
    return cdn_client.Client(config)

def create_dcdn_client() -> dcdn_client.Client:
    """
    Initialize Alibaba Cloud DCDN Client
    """
    access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    
    if not access_key_id or not access_key_secret:
        raise ValueError("Please set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET environment variables")

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )
    
    # Endpoint for DCDN
    config.endpoint = f'dcdn.aliyuncs.com'
    return dcdn_client.Client(config)

def create_cas_client() -> cas_client.Client:
    """
    Initialize Alibaba Cloud CAS Client
    """
    access_key_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    
    if not access_key_id or not access_key_secret:
        raise ValueError("Please set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET environment variables")

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret
    )
    # Endpoint for CAS
    config.endpoint = f'cas.aliyuncs.com'
    return cas_client.Client(config)

def upload_cert_to_cas(client: cas_client.Client, cert_name: str, cert: str, key: str) -> str:
    """
    Upload certificate to CAS and return the CertId
    """
    try:
        print(f"Uploading certificate {cert_name} to CAS...")
        request = cas_models.UploadUserCertificateRequest(
            name=cert_name,
            cert=cert,
            key=key
        )
        response = client.upload_user_certificate(request)
        cert_id = response.body.cert_id
        print(f"Successfully uploaded certificate to CAS. CertId: {cert_id}")
        return str(cert_id)
    except Exception as e:
        print(f"Failed to upload certificate to CAS: {e}")
        raise e

def read_file_content(path: str) -> str:
    """
    Read content from file
    """
    try:
        with open(path, 'r') as f:
            content = f.read().strip()
            if not content:
                print(f"Error: File {path} is empty")
                sys.exit(1)
            return content
    except FileNotFoundError:
        print(f"Error: File not found at {path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {path}: {e}")
        sys.exit(1)

def validate_pem(content: str, type_name: str):
    """
    Simple validation for PEM format
    """
    if "-----BEGIN" not in content:
        print(f"Warning: {type_name} does not look like a PEM file (missing -----BEGIN header)")
    if "-----END" not in content:
        print(f"Warning: {type_name} does not look like a PEM file (missing -----END footer)")
    print(f"Loaded {type_name}, length: {len(content)} characters")

def get_target_domains_cdn(client: cdn_client.Client, domain_suffix: str) -> List[str]:
    """
    Get all CDN domains matching the suffix
    """
    target_domains = []
    try:
        request = cdn_models.DescribeUserDomainsRequest(
            page_size=500  # Adjust if you have more domains
        )
        response = client.describe_user_domains(request)
        
        if response.body.domains and response.body.domains.page_data:
            for domain in response.body.domains.page_data:
                domain_name = domain.domain_name
                if domain_name.endswith(domain_suffix):
                    target_domains.append(domain_name)
                    
    except Exception as e:
        print(f"Error fetching CDN domains for {domain_suffix}: {e}")
    
    return target_domains

def get_target_domains_dcdn(client: dcdn_client.Client, domain_suffix: str) -> List[str]:
    """
    Get all DCDN domains matching the suffix
    """
    target_domains = []
    try:
        request = dcdn_models.DescribeDcdnUserDomainsRequest(
            page_size=500
        )
        response = client.describe_dcdn_user_domains(request)
        
        if response.body.domains and response.body.domains.page_data:
            for domain in response.body.domains.page_data:
                domain_name = domain.domain_name
                if domain_name.endswith(domain_suffix):
                    target_domains.append(domain_name)
                    
    except Exception as e:
        print(f"Error fetching DCDN domains for {domain_suffix}: {e}")
    
    return target_domains

def update_cdn_cert(client: cdn_client.Client, domain: str, cert_name: str, cert_id: str):
    """
    Update SSL certificate for a CDN domain using CertId
    """
    try:
        print(f"Updating CDN cert for: {domain} with CertId: {cert_id}")
        request = cdn_models.SetCdnDomainSSLCertificateRequest(
            domain_name=domain,
            cert_name=cert_name,
            cert_type='cas',  # Changed from 'upload' to 'cas'
            sslprotocol='on',
            cert_id=int(cert_id)  # Pass the CertId from CAS
        )
        client.set_cdn_domain_sslcertificate(request)
        print(f"Successfully updated CDN cert for {domain}")
    except Exception as e:
        print(f"Failed to update CDN cert for {domain}: {e}")

def update_dcdn_cert(client: dcdn_client.Client, domain: str, cert_name: str, cert_id: str):
    """
    Update SSL certificate for a DCDN domain using CertId
    """
    try:
        print(f"Updating DCDN cert for: {domain} with CertId: {cert_id}")
        request = dcdn_models.SetDcdnDomainSSLCertificateRequest(
            domain_name=domain,
            cert_name=cert_name,
            cert_type='cas',  # Changed from 'upload' to 'cas'
            sslprotocol='on',
            cert_id=int(cert_id)  # Pass the CertId from CAS
        )
        client.set_dcdn_domain_sslcertificate(request)
        print(f"Successfully updated DCDN cert for {domain}")
    except Exception as e:
        print(f"Failed to update DCDN cert for {domain}: {e}")

def process_domain(domain_suffix: str, cdn_client: cdn_client.Client, dcdn_client: dcdn_client.Client, cas_client: cas_client.Client):
    """
    Process a single domain suffix: upload cert to CAS, then sync to CDN/DCDN
    """
    print(f"\n====== Processing Domain Group: {domain_suffix} ======")
    
    cert_path = os.path.join(BASE_SSL_PATH, f'{domain_suffix}.fullchain.cer')
    key_path = os.path.join(BASE_SSL_PATH, f'{domain_suffix}.key')
    
    # Read certificates
    print(f"Reading certificate from {cert_path}")
    cert_content = read_file_content(cert_path)
    validate_pem(cert_content, f"Certificate ({domain_suffix})")
    
    print(f"Reading private key from {key_path}")
    key_content = read_file_content(key_path)
    validate_pem(key_content, f"Private Key ({domain_suffix})")
    
    # Create a unique name for the cert using timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    cert_name = f"{domain_suffix}_{timestamp}"
    
    cert_id = None
    # 0. Upload cert to CAS
    try:
        print(f"--- Uploading Certificate for {domain_suffix} to CAS ---")
        cert_id = upload_cert_to_cas(cas_client, cert_name, cert_content, key_content)
    except Exception as e:
        print(f"Error uploading to CAS for {domain_suffix}, skipping this domain group: {e}")
        return

    if not cert_id:
        print(f"Failed to get CertId for {domain_suffix}, skipping...")
        return

    # 1. Process CDN
    try:
        print(f"--- Processing CDN for {domain_suffix} ---")
        cdn_domains = get_target_domains_cdn(cdn_client, domain_suffix)
        print(f"Found {len(cdn_domains)} matching CDN domains: {cdn_domains}")
        
        for domain in cdn_domains:
            update_cdn_cert(cdn_client, domain, cert_name, cert_id)
    except Exception as e:
        print(f"Error in CDN processing for {domain_suffix}: {e}")

    # 2. Process DCDN
    try:
        print(f"--- Processing DCDN for {domain_suffix} ---")
        dcdn_domains = get_target_domains_dcdn(dcdn_client, domain_suffix)
        print(f"Found {len(dcdn_domains)} matching DCDN domains: {dcdn_domains}")
        
        for domain in dcdn_domains:
            update_dcdn_cert(dcdn_client, domain, cert_name, cert_id)
    except Exception as e:
        print(f"Error in DCDN processing for {domain_suffix}: {e}")

def main():
    print("Starting SSL Certificate Sync...")
    
    # Initialize clients once
    try:
        cdn = create_cdn_client()
        dcdn = create_dcdn_client()
        cas = create_cas_client()
    except Exception as e:
        print(f"Failed to initialize clients: {e}")
        sys.exit(1)

    # Process each domain
    for domain in TARGET_DOMAINS:
        process_domain(domain, cdn, dcdn, cas)

    print("\nAll Sync tasks completed.")

if __name__ == '__main__':
    main()

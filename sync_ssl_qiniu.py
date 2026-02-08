import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
import qiniu

# Load environment variables
load_dotenv()

# Configuration
BASE_SSL_PATH = os.getenv('BASE_SSL_PATH', '/etc/nginx/ssl')
TARGET_DOMAINS_ENV = os.getenv('TARGET_DOMAINS')
if TARGET_DOMAINS_ENV:
    TARGET_DOMAINS = [d.strip() for d in TARGET_DOMAINS_ENV.split(',') if d.strip()]
else:
    TARGET_DOMAINS = [
        'agilestudio.cn',
        '52cmajor.com',
        '33subs.com'
    ]

QINIU_ACCESS_KEY = os.getenv('QINIU_ACCESS_KEY')
QINIU_SECRET_KEY = os.getenv('QINIU_SECRET_KEY')

if not QINIU_ACCESS_KEY or not QINIU_SECRET_KEY:
    print("Error: QINIU_ACCESS_KEY and QINIU_SECRET_KEY must be set in .env file.")
    sys.exit(1)

# Initialize Qiniu Auth
q = qiniu.Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)

def get_cert_content(domain):
    """
    Read certificate and private key content from files.
    Assumes files are named: <domain>.fullchain.cer and <domain>.key
    """
    cert_path = os.path.join(BASE_SSL_PATH, f"{domain}.fullchain.cer")
    key_path = os.path.join(BASE_SSL_PATH, f"{domain}.key")

    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"Error: Certificate files not found for {domain}")
        return None, None

    try:
        with open(cert_path, 'r') as f:
            cert_content = f.read().strip()
        with open(key_path, 'r') as f:
            key_content = f.read().strip()
            
        # Basic validation
        if not cert_content.startswith("-----BEGIN CERTIFICATE-----"):
             print(f"Error: Invalid certificate format for {domain}")
             return None, None
        if not key_content.startswith("-----BEGIN PRIVATE KEY-----") and not key_content.startswith("-----BEGIN RSA PRIVATE KEY-----"):
             print(f"Error: Invalid private key format for {domain}")
             return None, None
             
        return cert_content, key_content
    except Exception as e:
        print(f"Error reading certificate files for {domain}: {e}")
        return None, None

def upload_ssl_cert(name, common_name, pri, ca):
    """
    Upload SSL certificate to Qiniu using API.
    Endpoint: POST https://api.qiniu.com/sslcert
    """
    url = "https://api.qiniu.com/sslcert"
    
    data = {
        "name": name,
        "common_name": common_name,
        "pri": pri,
        "ca": ca
    }
    
    # Qiniu signature
    access_token = q.token_of_request(url, body=json.dumps(data), content_type="application/json")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"QBox {access_token}"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"Successfully uploaded certificate: {name}, CertID: {result.get('certID')}")
            return result.get('certID')
        else:
            print(f"Failed to upload certificate {name}. Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error uploading certificate: {e}")
        return None

def update_domain_https(domain, cert_id):
    """
    Update HTTPS configuration for a domain.
    Endpoint: PUT https://api.qiniu.com/domain/<domain>/httpsconf
    """
    url = f"https://api.qiniu.com/domain/{domain}/httpsconf"
    
    data = {
        "certId": cert_id,
        "forceHttps": True,
        "http2Enable": True
    }
    
    # Qiniu signature
    access_token = q.token_of_request(url, body=json.dumps(data), content_type="application/json")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"QBox {access_token}"
    }
    
    try:
        response = requests.put(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"Successfully updated HTTPS config for {domain}")
            return True
        else:
            print(f"Failed to update HTTPS config for {domain}. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error updating domain HTTPS: {e}")
        return False

def get_cdn_domains_by_suffix(suffix):
    """
    Get all CDN domains ending with the given suffix.
    Endpoint: GET https://api.qiniu.com/domain?limit=1000
    """
    url = "https://api.qiniu.com/domain?limit=1000"
    
    access_token = q.token_of_request(url)
    
    headers = {
        "Authorization": f"QBox {access_token}"
    }
    
    target_domains = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            domains = result.get('domains', [])
            for d in domains:
                name = d.get('name')
                if name and name.endswith(suffix):
                    target_domains.append(name)
        else:
             print(f"Failed to list domains. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error fetching domains: {e}")
        
    return target_domains

def main():
    print("Starting Qiniu SSL Sync Script...")
    print(f"Target Domains Suffixes: {TARGET_DOMAINS}")
    
    for domain_suffix in TARGET_DOMAINS:
        print(f"\nProcessing domain suffix: {domain_suffix}")
        
        # 1. Read Certificate
        cert_content, key_content = get_cert_content(domain_suffix)
        if not cert_content or not key_content:
            print(f"Skipping {domain_suffix} due to missing or invalid certificate files.")
            continue
            
        # 2. Upload Certificate
        # Use a unique name to avoid conflicts, or handle existing certs.
        # Here we generate a new name with timestamp.
        timestamp = int(time.time())
        cert_name = f"{domain_suffix.replace('.', '_')}_{timestamp}"
        
        cert_id = upload_ssl_cert(cert_name, domain_suffix, key_content, cert_content)
        if not cert_id:
            print(f"Skipping {domain_suffix} due to upload failure.")
            continue
            
        # 3. Find matching CDN domains
        cdn_domains = get_cdn_domains_by_suffix(domain_suffix)
        if not cdn_domains:
            print(f"No CDN domains found for suffix {domain_suffix}")
            continue
            
        print(f"Found {len(cdn_domains)} matching domains: {cdn_domains}")
        
        # 4. Update each domain
        for domain in cdn_domains:
            print(f"Updating HTTPS for {domain}...")
            update_domain_https(domain, cert_id)

    print("\nDone.")

if __name__ == "__main__":
    main()

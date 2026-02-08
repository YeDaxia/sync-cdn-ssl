# SSL 证书同步工具

[English](README.md) | 中文

这个工具可以自动将 SSL 证书同步到 **阿里云 (CDN & DCDN)** 和 **七牛云**。它的设计初衷是简化在多个内容分发网络 (CDN) 之间更新 SSL 证书的流程。

## 功能特性

- **阿里云**: 将证书上传到 CAS (数字证书管理服务)，并更新关联的 CDN 和 DCDN 域名。
- **七牛云**: 上传证书并更新关联域名。
- **统一执行**: 可以一次性同步所有服务商，也可以单独运行。

## 前置要求

- Python 3.x
- pip (Python 包管理器)

## 安装

1. 克隆仓库:
   ```bash
   git clone <repository_url>
   cd sync-cdn-ssl
   ```

2. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

## 配置

1. 在项目根目录下创建一个 `.env` 文件 (你可以复制下面的示例):

   ```ini
   # Alibaba Cloud Configuration
   ALIBABA_CLOUD_ACCESS_KEY_ID=your_aliyun_access_key
   ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_aliyun_secret_key
   
   # Qiniu Cloud Configuration
   QINIU_ACCESS_KEY=your_qiniu_access_key
   QINIU_SECRET_KEY=your_qiniu_secret_key
   
   # SSL Certificates Base Path
   # 你的证书文件存储的目录
   BASE_SSL_PATH=/etc/nginx/ssl
   
   # Target Domains (comma separated)
   # 这些域名必须在 BASE_SSL_PATH 中有对应的证书文件
   TARGET_DOMAINS=example.com,another-domain.com
   ```

2. **证书文件命名规范**:
   工具要求 `BASE_SSL_PATH` 目录下的证书文件必须符合以下命名规范，其中 `<domain>` 对应 `TARGET_DOMAINS` 中的域名:
   
   - **证书 (完整链)**: `<domain>.fullchain.cer`
   - **私钥**: `<domain>.key`
   
   例如，如果 `TARGET_DOMAINS=example.com`，你必须有:
   - `/etc/nginx/ssl/example.com.fullchain.cer`
   - `/etc/nginx/ssl/example.com.key`

## 生成 SSL 证书 (可选)

这个工具非常适合配合 [acme.sh](https://github.com/acmesh-official/acme.sh) 生成的证书使用。以下是如何生成符合本工具命名规范的证书的简要指南。

1. **安装 acme.sh**:
   ```bash
   curl https://get.acme.sh | sh -s email=my@example.com
   ```

2. **签发证书**:
   (以使用阿里云 DNS API 为例)
   ```bash
   export Ali_Key="<key>"
   export Ali_Secret="<secret>"
   acme.sh --issue --dns dns_ali -d example.com -d *.example.com
   ```

3. **安装证书**:
   使用 `--install-cert` 命令将证书复制到你的 `BASE_SSL_PATH` 并重命名为正确的名称。

   ```bash
   # 假设 BASE_SSL_PATH 是 /etc/nginx/ssl
   acme.sh --install-cert -d example.com \
   --key-file       /etc/nginx/ssl/example.com.key  \
   --fullchain-file /etc/nginx/ssl/example.com.fullchain.cer \
   --reloadcmd     "service nginx force-reload"
   ```

   *注意: 此命令可确保 `acme.sh` 自动续期证书并将更新后的文件复制到指定路径，使其随时可供同步工具使用。*

## 使用方法

### 同步所有服务商
同步证书到阿里云和七牛云:

```bash
python3 sync_all.py
```

### 单独同步
你也可以单独运行特定服务商的脚本:

- **仅阿里云**:
  ```bash
  python3 sync_ssl_aliyun.py
  ```

- **仅七牛云**:
  ```bash
  python3 sync_ssl_qiniu.py
  ```

## 注意事项

- 确保运行脚本的用户对 `BASE_SSL_PATH` 目录和证书文件拥有读取权限。
- 工具使用域名作为后缀来查找证书文件。

## 联系我

- **X (推特)**: [@LuffyDaxia](https://x.com/LuffyDaxia)
- **小红书**: [LuffyDaxia](https://www.xiaohongshu.com/user/profile/5f49259400000000010085fd)


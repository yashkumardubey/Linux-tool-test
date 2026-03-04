# SSL Certificates

Place your SSL certificate files here to enable HTTPS.

## Required Files

| File | Description |
|------|-------------|
| `fullchain.pem` | Full certificate chain (your cert + intermediate CAs) |
| `privkey.pem` | Private key (keep this secret!) |

## How to Obtain Certificates

### Option 1: Let's Encrypt (Free, Recommended)
```bash
# Install certbot
sudo apt install certbot

# Get certificate (standalone mode)
sudo certbot certonly --standalone -d yourdomain.com

# Copy to this directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./
sudo chown $USER:$USER fullchain.pem privkey.pem
chmod 600 privkey.pem
```

### Option 2: Self-Signed (Testing Only)
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=Org/CN=yourdomain.com"
```

### Option 3: Commercial CA
Purchase from DigiCert, Comodo, GoDaddy, etc. and place the files here.

## Permissions
```bash
chmod 644 fullchain.pem
chmod 600 privkey.pem
```

## After Adding Certs

Restart the service:
```bash
# Product
make prod

# Vendor
cd vendor/ && make prod
```

Nginx auto-detects the certs and enables HTTPS with HTTP→HTTPS redirect.

**Important:** Never commit private keys to version control!

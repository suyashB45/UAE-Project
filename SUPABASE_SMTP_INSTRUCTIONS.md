# Configuring SMTP on your Self-Hosted Supabase

To allow Supabase to send authentication and password recovery emails, you need to add the following SMTP configuration to your Supabase installation's `.env` file (this is usually located inside the `docker` directory where you cloned the Supabase repository).

1. Open your Supabase `docker/.env` file.
2. Find the Email/SMTP section and update it with these exact values:

```env
# Email auth
ENABLE_EMAIL_SIGNUP=true
ENABLE_EMAIL_AUTOCONFIRM=false

# SMTP Config
SMTP_ADMIN_EMAIL=team@coact-ai.com
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USER=team@coact-ai.com
SMTP_PASS=Coact@ai2026
SMTP_SENDER_NAME=CoactAI
```

3. Restart your Supabase containers from the directory where its `docker-compose.yml` lives:
```powershell
docker compose down
docker compose up -d
```

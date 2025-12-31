# 🚀 Deployment Guide

This guide covers deploying Vibe Check to production using Railway (recommended) and alternative platforms.

## Railway Deployment (Recommended)

Railway provides the easiest deployment experience with automatic PostgreSQL provisioning.

### Step 1: Prepare Your Repository

1. Initialize git (if not already done):
   ```bash
   cd "Vibe Check"
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Push to GitHub:
   ```bash
   # Create a new repo on GitHub, then:
   git remote add origin https://github.com/yourusername/vibe-check.git
   git push -u origin main
   ```

### Step 2: Set Up Railway

1. Go to [railway.app](https://railway.app) and sign up/login

2. Click **"New Project"** → **"Deploy from GitHub repo"**

3. Select your `vibe-check` repository

4. Railway will detect the Python app automatically

### Step 3: Add PostgreSQL

1. In your Railway project, click **"New"** → **"Database"** → **"Add PostgreSQL"**

2. Railway automatically sets the `DATABASE_URL` environment variable

### Step 4: Configure Environment Variables

In Railway dashboard, go to your app → **Variables** tab:

```bash
# Slack credentials (from api.slack.com/apps)
SLACK_CLIENT_ID=<your_value>
SLACK_CLIENT_SECRET=<your_value>
SLACK_SIGNING_SECRET=<your_value>

# Generate encryption key
ENCRYPTION_KEY=<generate_with_fernet>

# Application settings
PORT=8000
LOG_LEVEL=INFO

# Features
ENABLE_REMINDERS=true
REMINDER_DELAY_HOURS=4
DATA_RETENTION_DAYS=90
```

To generate `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 5: Get Your App URL

1. In Railway, go to your app → **Settings** → **Domains**

2. Click **"Generate Domain"** to get a public URL like:
   ```
   https://vibe-check-production.up.railway.app
   ```

3. Copy this URL - you'll need it for Slack configuration

### Step 6: Initialize Database

1. In Railway dashboard → **Deployments** tab

2. Once deployed, click the three dots → **"View Logs"**

3. The app automatically creates tables on first run

4. Verify in logs you see: "Database tables created successfully"

### Step 7: Configure Slack App

Now update your Slack app with the Railway URL:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Your App

2. **OAuth & Permissions** → Redirect URLs:
   ```
   https://your-app.railway.app/slack/oauth_redirect
   ```

3. **Interactivity & Shortcuts** → Request URL:
   ```
   https://your-app.railway.app/slack/events
   ```

4. **Event Subscriptions** → Request URL:
   ```
   https://your-app.railway.app/slack/events
   ```

5. **Slash Commands** → Update each command Request URL:
   ```
   https://your-app.railway.app/slack/events
   ```

6. Click **"Save Changes"** for each section

### Step 8: Install to Workspace

1. Go to your app URL: `https://your-app.railway.app`

2. Click **"Add to Slack"**

3. Authorize the app

4. You're live! 🎉

### Step 9: Set Up Vibe Check Channel

1. Create a private channel in Slack for feedback (e.g., `#vibe-check-private`)

2. Invite the bot: `/invite @Vibe Check`

3. The bot will use this channel to post client feedback

### Monitoring & Logs

View logs in Railway:
```bash
# Via dashboard
Railway Dashboard → Your App → Deployments → View Logs

# Via CLI
railway login
railway link
railway logs
```

### Updating the App

Railway automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Update feature"
git push origin main
# Railway deploys automatically
```

### Rolling Back

In Railway dashboard:
1. Go to **Deployments**
2. Find previous successful deployment
3. Click three dots → **"Redeploy"**

---

## Alternative: Heroku Deployment

### Prerequisites

- Heroku account
- Heroku CLI installed

### Steps

1. **Create Heroku app**:
   ```bash
   heroku create vibe-check-app
   ```

2. **Add PostgreSQL**:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set SLACK_CLIENT_ID=xxx
   heroku config:set SLACK_CLIENT_SECRET=xxx
   heroku config:set SLACK_SIGNING_SECRET=xxx
   heroku config:set ENCRYPTION_KEY=xxx
   heroku config:set LOG_LEVEL=INFO
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

5. **Initialize database**:
   ```bash
   heroku run python scripts/init_db.py
   ```

6. **View logs**:
   ```bash
   heroku logs --tail
   ```

7. **Get app URL**:
   ```bash
   heroku domains
   # Use this URL for Slack configuration
   ```

---

## Alternative: AWS Deployment

### Using AWS Elastic Beanstalk

1. **Install EB CLI**:
   ```bash
   pip install awsebcli
   ```

2. **Initialize**:
   ```bash
   eb init -p python-3.11 vibe-check
   ```

3. **Create environment**:
   ```bash
   eb create vibe-check-prod
   ```

4. **Set environment variables**:
   ```bash
   eb setenv SLACK_CLIENT_ID=xxx SLACK_CLIENT_SECRET=xxx ...
   ```

5. **Deploy**:
   ```bash
   eb deploy
   ```

6. **View logs**:
   ```bash
   eb logs
   ```

### Using AWS ECS (Docker)

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "app.py"]
   ```

2. **Build and push to ECR**:
   ```bash
   docker build -t vibe-check .
   aws ecr create-repository --repository-name vibe-check
   docker tag vibe-check:latest <ecr-url>/vibe-check:latest
   docker push <ecr-url>/vibe-check:latest
   ```

3. **Create ECS service** via AWS Console or Terraform

4. **Add RDS PostgreSQL** database

5. **Configure environment variables** in ECS task definition

---

## Alternative: Digital Ocean

### Using App Platform

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)

2. Click **"Create App"** → Connect GitHub repo

3. Configure:
   - **Runtime**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `python app.py`

4. Add PostgreSQL database from marketplace

5. Set environment variables in dashboard

6. Deploy and get app URL

---

## Environment-Specific Configurations

### Production Best Practices

1. **Use strong encryption key**:
   ```bash
   # Generate a new key for production
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Enable HTTPS only** (Railway does this automatically)

3. **Set appropriate log level**:
   ```bash
   LOG_LEVEL=INFO  # Not DEBUG in production
   ```

4. **Configure data retention**:
   ```bash
   DATA_RETENTION_DAYS=90  # Adjust as needed
   ```

5. **Monitor database size** and set up backups

### Scaling Considerations

- **Database**: Use connection pooling (already configured)
- **Scheduler**: Single instance only (APScheduler limitation)
- **Web workers**: Can scale horizontally, but scheduler must run on one instance
- **Database backups**: Configure automatic backups on your platform

### Security Checklist

- [ ] HTTPS enabled
- [ ] Strong encryption key in use
- [ ] Environment variables never committed to git
- [ ] Database access restricted by IP/VPC
- [ ] Slack signing secret verified
- [ ] Regular security updates applied
- [ ] Logs don't contain sensitive data

---

## Troubleshooting

### Deployment Issues

**Build fails**:
- Check `requirements.txt` is correct
- Verify Python version in `runtime.txt`
- Check platform-specific requirements

**App crashes on start**:
- Check logs for error messages
- Verify all environment variables are set
- Test database connection
- Ensure PORT is correct

**Scheduler not running**:
- Verify APScheduler initialized (check logs)
- Check database permissions
- Ensure only one app instance has scheduler

**Database connection errors**:
- Verify DATABASE_URL is correct
- Check SSL requirements for your platform
- Test database connectivity

### Performance Issues

**Slow response times**:
- Check database query performance
- Review logs for bottlenecks
- Consider database indexing
- Monitor connection pool usage

**High memory usage**:
- Check for memory leaks
- Review scheduler job count
- Monitor database connection pool

### Getting Help

1. **Check logs** first
2. **Verify environment variables**
3. **Test locally** to reproduce
4. **Check platform status** pages
5. **Review recent changes** for issues

---

## Maintenance

### Regular Tasks

**Weekly**:
- Review error logs
- Check scheduler job status
- Monitor response rates

**Monthly**:
- Review database size
- Check for updates to dependencies
- Review security advisories

**Quarterly**:
- Update dependencies
- Review and clean old data
- Performance review

### Backup Strategy

1. **Database backups**: Enable automatic backups on your platform
2. **Configuration backup**: Keep `.env.example` updated
3. **Code backup**: Use git and GitHub

### Monitoring

Set up monitoring for:
- App uptime
- Error rates
- Response times
- Database performance
- Job execution success rates

### Health Checks

The app includes a `/health` endpoint:
```bash
curl https://your-app.railway.app/health
```

Response indicates:
- Database connectivity
- Scheduler status
- Overall health

---

## Cost Estimates

### Railway (Recommended)
- **Hobby Plan**: $5/month + usage
- **PostgreSQL**: Included
- **Estimated**: $10-20/month for small workload

### Heroku
- **Basic**: $7/month (app) + $5/month (database)
- **Estimated**: $12-25/month

### AWS
- **ECS Fargate**: ~$15/month (0.25 vCPU, 0.5 GB)
- **RDS PostgreSQL**: ~$15/month (t3.micro)
- **Estimated**: $30-40/month

### Digital Ocean
- **Basic App**: $5/month
- **Managed PostgreSQL**: $15/month
- **Estimated**: $20-30/month

---

## Next Steps After Deployment

1. ✅ Test OAuth installation flow
2. ✅ Add your first test client
3. ✅ Send test standup with `/vibe-test`
4. ✅ Set up vibe check channel
5. ✅ Configure monitoring
6. ✅ Set up backups
7. ✅ Train admin users

Congratulations! Your Vibe Check app is deployed! 🎉

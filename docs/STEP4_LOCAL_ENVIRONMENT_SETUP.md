# Step 4: Local Environment Setup Guide

This guide details how to set up the local environment as specified in Step 4 of the project brief.

---

## 4.1 Run SonarQube Locally (with PostgreSQL)

SonarQube Community Build runs with PostgreSQL (separate database instance, not the embedded H2 trial database).

### 1. Launch SonarQube & PostgreSQL
```bash
docker compose -f docker-compose.sonarqube.yml up -d
```
- **SonarQube Web UI**: [http://localhost:9000](http://localhost:9000)
- Initial credentials: `admin` / `admin` (you will be prompted to change the password upon first login).

### 2. Configure Projects
1. Sign in to SonarQube.
2. Create two projects:
   - GitLab sandbox project: `sandbox-gitlab-service`
   - GitHub sandbox project: `sandbox-github-service`

### 3. Create the "Trainee gate"
1. In SonarQube, go to **Quality Gates** > **Create Quality Gate**.
2. Name it **Trainee gate**.
3. Add the two required conditions:
   - **Coverage on New Code** `< 80.0%`
   - **New Issues** `> 0`
4. Set **Trainee gate** as default or assign it to both sandbox projects.

### 4. Create Authentication Tokens
- **Project Analysis Token**:
  - Go to your Project > **Project Settings** > **Analysis Tokens** > Generate token named `CI_SCANNER`.
  - Save this as `SONAR_TOKEN` in your CI repository secrets.
- **User Token for Application (`triage-bot`)**:
  - Go to **Administration** > **Security** > **Users** > Create user `triage-bot`.
  - Grant `Browse` permission to the sandbox projects.
  - Generate a token for `triage-bot` and save it in `.env` as `SONARQUBE_TRIAGE_BOT_TOKEN`.

---

## 4.2 Sandbox Repositories

The complete sample service is located in the `sandbox_repo/` folder:
- **Service & Tests**: `src/service.py`, `tests/test_service.py`
- **5-Stage Pipelines**: `test -> sonarqube -> build -> push -> deploy`
  - GitLab CI: `sandbox_repo/.gitlab-ci.yml`
  - GitHub Actions: `sandbox_repo/.github/workflows/pipeline.yml`
- **Quality Gate Verification**: Both pipelines pass `-Dsonar.qualitygate.wait=true` to wait for quality gate status and fail if coverage < 80% or new issues > 0.
- **Deliberate Failure Testing**:
  - To test **Deployment Failure**: Set environment variable `FAIL_DEPLOY=true`.
  - To test **Test Failure**: Introduce an assertion failure in `tests/test_service.py`.
  - To test **Quality Gate Failure**: Add untested branches to drop coverage below 80%.
  - To test **Secret Scan Failure**: Commit a dummy token like `ghp_123456789012345678901234567890123456`.

---

## 4.3 Local Runners Setup

Cloud runners cannot reach `http://localhost:9000` on your laptop. You need local runners.

### GitHub Actions Self-Hosted Runner
1. In your GitHub repository, navigate to **Settings** > **Actions** > **Runners** > **New self-hosted runner**.
2. Choose **Windows** (or Docker Linux runner) and run the provided registration script.
3. Start the runner:
   ```powershell
   .\run.cmd
   ```
4. Jobs targeting `runs-on: self-hosted` can connect directly to `http://localhost:9000`!

### GitLab Runner (Docker Executor)
1. Run GitLab Runner via Docker:
   ```bash
   docker run -d --name gitlab-runner --restart always \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v gitlab-runner-config:/etc/gitlab-runner \
     --add-host=host.docker.internal:host-gateway \
     gitlab/gitlab-runner:latest
   ```
2. Register the runner with your GitLab project registration token:
   ```bash
   docker exec -it gitlab-runner gitlab-runner register \
     --url "https://gitlab.com/" \
     --registration-token "<YOUR_GITLAB_REGISTRATION_TOKEN>" \
     --executor "docker" \
     --docker-image "python:3.12-slim" \
     --docker-extra-hosts "host.docker.internal:host-gateway"
   ```

---

## 4.4 Webhooks and Credentials

### 1. Expose Local Webhook Endpoints
Use **Cloudflare Tunnel** or **ngrok** to get a public URL for webhooks:
```bash
# Using Cloudflare Tunnel:
cloudflared tunnel --url http://localhost:8000

# Or using ngrok:
ngrok http 8000
```

### 2. Configure Webhooks
Copy the generated public URL (e.g., `https://abc-123.trycloudflare.com`):
- **GitLab Webhook**:
  - URL: `https://abc-123.trycloudflare.com/api/webhooks/gitlab`
  - Secret Token: `gitlab_shared_webhook_secret_123` (matching `.env`)
  - Triggers: Pipeline events, Job events, Merge request events.
- **GitHub Webhook**:
  - Payload URL: `https://abc-123.trycloudflare.com/api/webhooks/github`
  - Content type: `application/json`
  - Secret: `github_shared_webhook_secret_456` (matching `.env`)
  - Triggers: Workflow runs, Workflow jobs, Pull requests.

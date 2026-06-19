# CI/CD Pipeline Guide

## Overview

The RAG Conversational Engine includes a **production-grade CI/CD pipeline** with:

- ✅ Automated testing on multiple Python versions
- ✅ Code quality checks (linting, formatting, type checking)
- ✅ Security scanning (dependencies, secrets, code analysis)
- ✅ Docker containerization with multi-stage builds
- ✅ Automated deployment to staging and production
- ✅ Release management and versioning

## Pipeline Architecture

```
┌──────────┐
│  PR/Push │
└────┬─────┘
     │
     ├─→ CI Pipeline (ci.yml)
     │   ├─ Tests (unit + integration)
     │   ├─ Linting (flake8, pylint)
     │   ├─ Type checking (mypy)
     │   ├─ Security (bandit)
     │   └─ Coverage (codecov)
     │
     ├─→ Security Pipeline (security.yml)
     │   ├─ Dependency scan
     │   ├─ SAST (Semgrep, CodeQL)
     │   ├─ Secret scan
     │   ├─ Container scan
     │   └─ License check
     │
     └─→ CD Pipeline (cd.yml)
         ├─ Build packages
         ├─ Docker image build
         ├─ Deploy to staging
         └─ Deploy to production (on tag)
```

## GitHub Workflows

### 1. CI Pipeline (`.github/workflows/ci.yml`)

**Trigger:** Push to master/main/develop, or Pull Request

**Jobs:**
- **test**: Unit tests on Python 3.10, 3.11, 3.12
- **integration**: Integration tests with real APIs (if configured)
- **lint**: Code formatting checks

**What it does:**
1. Set up Python environment
2. Install dependencies
3. Run linting (flake8)
4. Type checking (mypy)
5. Run unit tests with coverage
6. Run integration tests (if APIs available)
7. Upload coverage to Codecov
8. Security scanning (bandit)

**Output:**
- Test results
- Coverage reports
- Code quality metrics
- Security findings

### 2. Security Pipeline (`.github/workflows/security.yml`)

**Trigger:** Push, PR, or daily schedule (2 AM UTC)

**Jobs:**
- **dependency-check**: Check for vulnerable dependencies
- **bandit**: Python security linter
- **semgrep**: Static analysis
- **codeql**: GitHub's code analysis
- **secret-scan**: Detect hardcoded secrets
- **container-scan**: Scan Docker image (Trivy)
- **license-check**: Verify license compliance

**Output:**
- SARIF reports
- Vulnerability alerts
- License compliance report
- Automated GitHub security tab updates

### 3. CD Pipeline (`.github/workflows/cd.yml`)

**Trigger:** Push to master/main, or new git tags

**Jobs:**
- **build**: Create distribution packages
- **docker-build**: Build and push Docker image
- **deploy-staging**: Deploy to staging environment
- **deploy-prod**: Deploy to production (manual approval)

**What it does:**
1. Build Python packages (wheel, sdist)
2. Build Docker image and push to registries
3. Deploy to staging
4. Create GitHub releases (on tags)
5. Deploy to production (manual approval)

## Local Setup

### Development Environment

```bash
# Clone repository
git clone https://github.com/avik79/rag-conversational-engine-.git
cd rag-conversational-engine

# Install dependencies
uv sync

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Docker Setup

```bash
# Build image locally
docker build -t eira:dev .

# Run container
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  eira:dev

# Or use docker-compose
docker-compose up app
```

## Configuration

### Environment Variables

Before deployment, set these GitHub Secrets:

```bash
# For CI/CD
ANTHROPIC_API_KEY          # Claude API key
OPENAI_API_KEY            # GPT-4o API key
TAVILY_API_KEY            # Weather/news API key

# For Docker/Container Registry
DOCKERHUB_USERNAME        # Docker Hub account
DOCKERHUB_TOKEN           # Docker Hub token

# For Staging Deployment
STAGING_DEPLOY_KEY        # SSH private key
STAGING_DEPLOY_HOST       # Staging server hostname
STAGING_DEPLOY_USER       # SSH username

# For Production Deployment
PROD_DEPLOY_KEY           # SSH private key
PROD_DEPLOY_HOST          # Production server hostname
PROD_DEPLOY_USER          # SSH username
```

### Docker Compose Profiles

```bash
# Development (app only, SQLite)
docker-compose up app

# With distributed Chroma
docker-compose --profile distributed up

# Production (PostgreSQL, Redis)
docker-compose --profile production up

# With monitoring (Prometheus, Grafana)
docker-compose --profile monitoring up

# Everything
docker-compose --profile production --profile monitoring up
```

## Running Tests Locally

### Unit Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_hitl_tools.py -v

# With coverage
pytest --cov=tools --cov=models --cov=app --cov-report=html

# Specific Python version
python3.11 -m pytest
```

### Integration Tests

```bash
# Requires API keys in .env
pytest -m integration -v

# With timeout
pytest -m integration -v --timeout=60
```

### Security Tests

```bash
# Lint with flake8
flake8 . --max-line-length=120

# Type check with mypy
mypy tools models app --ignore-missing-imports

# Security scan with bandit
bandit -r tools models app

# Format check with black
black --check . --line-length=120
```

## Deployment Process

### Automatic Deployments

#### Staging
- **Trigger:** Push to `develop` branch OR push to `master` branch
- **Environment:** Staging server
- **Approval:** Automatic (if CI passes)

#### Production
- **Trigger:** Create a git tag (e.g., `v1.0.0`)
- **Environment:** Production server
- **Approval:** Manual (via GitHub environment rules)

### Manual Deployment

```bash
# Create a release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# This triggers:
# 1. CD pipeline builds and tests
# 2. Creates Docker image (ghcr.io/avik79/rag-conversational-engine:v1.0.0)
# 3. Waits for manual approval
# 4. Deploys to production on approval
# 5. Creates GitHub release with artifacts
```

## Monitoring & Debugging

### View Workflow Status

```bash
# List workflows
gh workflow list

# View workflow runs
gh workflow view ci.yml --limit 10

# View specific run details
gh run view <run-id> --log

# Download logs
gh run download <run-id> -D ./logs
```

### Common Issues

#### Tests Failing in CI but Passing Locally

**Solution:**
```bash
# Use same Python version as CI
python3.11 -m pytest

# Check environment variables
env | grep ANTHROPIC

# Run in isolated environment
python -m venv /tmp/test-env
source /tmp/test-env/bin/activate
pip install -e ".[dev]"
pytest
```

#### Docker Build Failing

**Solution:**
```bash
# Build with verbose output
docker build -t eira:test . --progress=plain

# Check Dockerfile for syntax errors
docker build --dry-run .

# Debug interactively
docker run -it --entrypoint bash eira:test
```

#### Deployment Not Triggering

**Solution:**
1. Check branch protection rules (main branch requires PR review?)
2. Verify secrets are set: `gh secret list`
3. Check workflow file syntax: `github.com/your-org/your-repo/actions`
4. Manually trigger: `gh workflow run ci.yml`

## Performance Optimization

### Caching

The pipelines use GitHub Actions caching:

```yaml
- uses: actions/setup-python@v4
  with:
    cache: 'pip'  # Automatically caches pip dependencies
```

### Parallel Testing

```bash
# Run tests in parallel
pytest -n auto

# Specify number of workers
pytest -n 4
```

### Docker Layer Caching

```bash
# Build command includes caching
docker build --cache-from ghcr.io/avik79/rag-conversational-engine:latest .
```

## Security Best Practices

### Secrets Management

✅ **Do:**
- Use GitHub Secrets for sensitive data
- Rotate secrets regularly
- Use separate secrets for staging/prod
- Limit secret access with environment rules

❌ **Don't:**
- Commit secrets to repository
- Print secrets in logs
- Use same secret for all environments
- Share secrets via email/chat

### Code Security

- Enable branch protection rules
- Require status checks before merge
- Require code reviews
- Enable security scanning
- Use signed commits

### Container Security

- Non-root user in Dockerfile
- Read-only root filesystem (when possible)
- Minimal base image (python:3.11-slim)
- Regular vulnerability scanning
- Use signed images

## Troubleshooting Guide

### Issue: "Permission denied" deploying

**Solution:**
```bash
# Verify SSH key permissions
chmod 600 deploy-key
ssh-keyscan -H $DEPLOY_HOST >> ~/.ssh/known_hosts

# Test SSH connection
ssh -i deploy-key user@host "echo OK"
```

### Issue: "Module not found" in tests

**Solution:**
```bash
# Ensure package is installed in editable mode
pip install -e .

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Issue: Flaky integration tests

**Solution:**
```bash
# Add retry logic
pytest --reruns 3 --reruns-delay 1 -m integration

# Increase timeout
pytest -m integration --timeout=120
```

## References

- **CI Workflow**: `.github/workflows/ci.yml`
- **Security Workflow**: `.github/workflows/security.yml`
- **CD Workflow**: `.github/workflows/cd.yml`
- **Docker**: `Dockerfile`, `docker-compose.yml`
- **GitHub Actions Docs**: https://docs.github.com/en/actions

## Support

For questions or issues:
1. Check workflow logs: GitHub Actions tab
2. Review this guide section
3. Check GitHub status: https://www.githubstatus.com
4. Open GitHub issue with logs attached

---

**Pipeline Status Badge:**

Add to README.md:
```markdown
[![CI](https://github.com/avik79/rag-conversational-engine-/workflows/CI/badge.svg)](https://github.com/avik79/rag-conversational-engine-/actions)
[![Security](https://github.com/avik79/rag-conversational-engine-/workflows/Security/badge.svg)](https://github.com/avik79/rag-conversational-engine-/actions)
```

**Last Updated:** 2026-06-19

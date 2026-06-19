# CI/CD Quick Start — 10 Minutes to Production-Ready Pipeline

## What You Get

✅ Automated testing on every push
✅ Security scanning for vulnerabilities  
✅ Docker containerization
✅ Automated staging deployment
✅ Production releases with approval
✅ Coverage reports and quality metrics

## 1. Set GitHub Secrets (2 minutes)

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

```
ANTHROPIC_API_KEY       (your Claude API key)
OPENAI_API_KEY          (your GPT-4o API key)
TAVILY_API_KEY          (your weather API key)
```

Optional (for Docker registry):
```
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Optional (for deployment):
```
STAGING_DEPLOY_KEY      (SSH private key)
STAGING_DEPLOY_HOST     (e.g., staging.example.com)
STAGING_DEPLOY_USER     (e.g., deploy)
```

## 2. Enable Branch Protection (1 minute)

Go to: **Settings → Branches → Add branch protection rule**

For `main`/`master`:
- ✓ Require a pull request before merging
- ✓ Require status checks to pass before merging
- ✓ Select "ci / test", "ci / lint", "security / bandit"

## 3. Test the Pipeline (5 minutes)

### Verify CI runs on your branch

```bash
# Make a small change
echo "# Updated" >> README.md

# Commit and push
git add -A
git commit -m "Test CI pipeline"
git push origin feature-branch
```

Watch it run: **Actions** tab in GitHub

You should see:
- `ci` workflow running tests
- `security` workflow scanning

### Verify CD runs on main

```bash
# After PR merges to main
# → Triggers `cd` workflow
# → Builds Docker image
# → Deploys to staging
```

## 4. Local Testing (Optional)

Run tests before pushing:

```bash
# Quick test
pytest tests/test_hitl_tools.py -v

# Full suite with coverage
pytest --cov=tools --cov=models --cov=app

# Linting
flake8 . --max-line-length=120
black . --check --line-length=120

# Docker build
docker build -t eira:test .
```

## 5. Create a Release (3 minutes)

```bash
# Tag a version
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

This triggers:
1. ✅ All tests run
2. ✅ Docker image built: `ghcr.io/avik79/rag-conversational-engine:v1.0.0`
3. ✅ Waits for manual approval
4. ✅ Deploys to production
5. ✅ Creates GitHub release

## Common Commands

### View workflow status
```bash
gh workflow list
gh run list --limit 10
gh run view <run-id>
```

### Trigger manually
```bash
gh workflow run ci.yml
gh workflow run cd.yml
```

### Download logs
```bash
gh run download <run-id>
```

### View secrets (read-only)
```bash
gh secret list
```

## File Structure

```
.github/workflows/
├── ci.yml               # Tests & quality checks
├── security.yml         # Security scanning
└── cd.yml              # Build & deploy

Dockerfile             # Container image
docker-compose.yml     # Local dev environment
```

## What Runs Automatically

### On Every Push
1. Run tests (Python 3.10, 3.11, 3.12)
2. Code quality checks
3. Security scanning
4. Build report

### On Push to main
1. Same as above
2. Plus Docker image build
3. Deploy to staging (if deployment configured)

### On Git Tag (v*.*)
1. All above
2. Create GitHub release
3. Deploy to production (manual approval)

## Viewing Results

### Test Results
**GitHub → Actions → ci → test**
- Pass/fail for each Python version
- Coverage percentage
- Failed tests shown inline

### Security Findings
**GitHub → Security → Code scanning**
- Vulnerabilities listed
- Severity level
- Remediation suggestions

### Deployment Status
**GitHub → Deployments**
- Staging deployments (auto)
- Production deployments (manual)
- Rollout history

## Troubleshooting

### "Workflow fails immediately"
- Check Secrets are set: **Settings → Secrets**
- Branch name matches trigger: `.github/workflows/ci.yml` line 4-5

### "Tests fail in CI but pass locally"
- Use same Python version: `python3.11`
- Check environment: `export ANTHROPIC_API_KEY=...`
- Run: `pytest -v --tb=short`

### "Docker build fails"
- Check file paths are correct
- Verify `.dockerignore` exists
- Build locally: `docker build -t test .`

### "Deployment doesn't trigger"
- Verify branch protection rules
- Check workflow file has correct trigger
- Manually trigger: `gh workflow run cd.yml`

## Success Indicators

✅ All 3 workflows visible in Actions tab
✅ Tests run and pass on every push
✅ Security scan completes without errors
✅ Docker image builds successfully
✅ Can deploy manually with: `git tag v1.0.0 && git push origin v1.0.0`

## Next Steps

1. **Add status badge to README**
   ```markdown
   [![CI](https://github.com/avik79/rag-conversational-engine-/workflows/CI/badge.svg)](https://github.com/avik79/rag-conversational-engine-/actions)
   ```

2. **Configure deployment endpoints** (optional)
   - Staging: In `cd.yml` workflow
   - Production: Same file, manual approval step

3. **Monitor test coverage**
   - Codecov.io integration (free for public repos)
   - Coverage badge in README

4. **Set up notifications** (optional)
   - Slack integration for failed tests
   - GitHub issues for security findings

5. **Read full guide**: `CI_CD_GUIDE.md`

## Reference

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Testing and quality |
| `.github/workflows/security.yml` | Vulnerability scanning |
| `.github/workflows/cd.yml` | Build and deploy |
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Local development |
| `CI_CD_GUIDE.md` | Full documentation |

---

**You're done!** Your pipeline is live. 🚀

Push code → Tests run automatically → Merge to main → Deploys to staging → Tag release → Deploys to production (with approval)

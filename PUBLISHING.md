# Uploading sard to PyPI

The package name `sard-subs` was free on PyPI when checked on 2026-11-10.
`python -m build` and `python -m twine check` pass with no warnings, and the wheel
was installed and exercised in a clean venv.

What cannot be automated on your behalf is the PyPI account itself: PyPI guards
sign-up with hCaptcha, verifies the email address, and requires two-factor
authentication before any API token can be created or any package uploaded.

## One-time setup (about 5 minutes, you must do this)

1. Open <https://pypi.org/account/register/>. The name, email and username are
   already filled in; choose your own password, complete the hCaptcha, accept the
   terms, and click **Create account**.
2. Click the verification link PyPI emails to `majdsong7@gmail.com`.
3. Enable two-factor authentication at
   <https://pypi.org/manage/account/#two-factor> (authenticator app is easiest).
   Without 2FA, PyPI blocks token creation and uploads.

## Option A — trusted publishing, no token (recommended)

The repository already contains `.github/workflows/release.yml`, which builds,
lints, tests, checks metadata and publishes on a `v*` tag using OpenID Connect.

After 2FA, add a pending publisher at
<https://pypi.org/manage/account/publishing/> with exactly these values:

| Field | Value |
| --- | --- |
| PyPI project name | `sard-subs` |
| Owner | `majdvik` |
| Repository name | `sard` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then publish a version:

```powershell
cd C:\Users\NTC\Documents\Qoder\2026-11-10-8e3c1e1c\codex-oss\sard
# bump "version" in pyproject.toml first, because v0.1.0 already exists as a GitHub tag
git add pyproject.toml
git commit -m "Bump version for PyPI release"
git tag v0.1.1
git push origin main --tags
```

No secret is stored anywhere.

## Option B — API token

Create an account-scoped token at <https://pypi.org/manage/account/token/>
(project scoping is only possible after the first upload).

Then run either:

```powershell
# interactive, token is read as a SecureString and never written to disk
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\publish.ps1
```

or, with twine directly:

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."
python -m twine upload dist\*
Remove-Item Env:\TWINE_PASSWORD
```

After the first upload, replace the account token with a project-scoped one.

## After publishing

```powershell
pip install sard-subs
sard --version
```

Then add the PyPI badge to `README.md` and record the release date in `CHANGELOG.md`.

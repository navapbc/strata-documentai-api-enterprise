# Security Policy

## Supported versions

We always recommend using the latest version of Strata to ensure you get all
security updates.

## Security scanning

Every pull request is scanned with [gitleaks](https://github.com/gitleaks/gitleaks) for leaked secrets across the full commit history. The DocumentAI Enterprise API additionally executes [pip-audit](https://github.com/pypa/pip-audit) in CI to check its Python dependencies for known CVEs.

## Reporting vulnerabilities

Please do not file GitHub issues for security vulnerabilities, as they are
public!

Nava takes security issues very seriously. If you have any concerns about Strata
or believe you have uncovered a vulnerability, please get in touch via the
e-mail address strata@navapbc.com. In the message, try to provide a description
of the issue and ideally a way of reproducing it. The security team will get
back to you as soon as possible.

Note that this security address should be used only for undisclosed
vulnerabilities. Please report any security problems to us before disclosing it
publicly.
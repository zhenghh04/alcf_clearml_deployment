# Troubleshooting

## `Token is not active`

- Re-export a fresh token with `clearml-globus-token --type <compute|transfer> --login-if-needed`.
- Confirm env var is non-empty (`echo ${#VAR}`).

## `PermissionDenied` on transfer endpoint login

- Endpoint policy may require specific identity domain (for example `alcf.anl.gov`).
- Re-login with correct identity and consent.

## Duplicate endpoint alias matches

- Pass endpoint UUIDs directly to avoid alias ambiguity.

## ClearML `Task` has no `set_environment`

- Use `task.set_parameters_as_dict({"env:KEY": "value"})` (already applied in bridge code).

## Private GitHub repo clone fails in ClearML Agent

- If the task uses `https://github.com/...`, store GitHub credentials in the ClearML Configuration Vault:
```hocon
agent {
  git_user: "<GITHUB_USERNAME>"
  git_pass: "<GITHUB_PAT>"
}
```
- Create the PAT from GitHub **Settings** -> **Developer settings** -> **Personal access tokens**. Prefer a fine-grained token scoped to the target repository with **Contents: Read-only** and **Metadata: Read-only**.
- Restart the agent after updating the vault and confirm the agent log shows `Loaded group vault for user ...`.
- Use a PAT with repository read access.
- If the repo belongs to an organization with SSO or approval rules, authorize or approve the token there too.
- If the repo has private submodules, the token also needs read access to those repos.
- If the task uses `git@github.com:...`, the agent needs SSH key access and a populated `known_hosts`, not `git_user` / `git_pass`.

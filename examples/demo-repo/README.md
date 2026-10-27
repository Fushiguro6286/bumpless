# Bumpless demo repo

A small user-service app written against pydantic **v1** (`requirements.txt` pins `pydantic==1.10.18`), with
Dependabot and the Bumpless workflow set up. When Dependabot opens the pydantic 2.x PR, the tests go red and
Bumpless pushes a migration commit and comments a report on the PR.

## Set up (once)

1. Push this folder as its own GitHub repository.
2. In `.github/workflows/bumpless.yml`, replace `YOUR_GITHUB_USER/bumpless` with the repository that holds
   Bumpless (it must be public, or in the same account with Actions access allowed).
3. Add `NEBIUS_API_KEY` and `TAVILY_API_KEY` under **Settings → Secrets and variables → Dependabot**, and again
   under **Actions** (the `@bumpless` comment job and manual runs read Actions secrets).
4. **Settings → Actions → General → Workflow permissions:** allow read and write.

## Try it

- Wait for Dependabot's pydantic PR, or run the **Bumpless** workflow by hand (Actions → Bumpless → Run
  workflow: package `pydantic`, target `>=2,<3`). A manual run opens its own PR with the report as its body.
- On the PR, comment `@bumpless explain the change in app/models.py`.

The app's `app/storage.py` is deliberately untested, so the report marks its changes Low confidence.

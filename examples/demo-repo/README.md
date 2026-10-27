# Bumpless demo repo

A small user-service app written against pydantic **v1** (`requirements.txt` pins `pydantic==1.10.18`), with
Dependabot and the Bumpless workflow set up. When Dependabot opens the pydantic 2.x PR, the tests go red and
Bumpless pushes a migration commit and comments a report on the PR.

## Set up (once)

1. Push this folder as its own GitHub repository.
2. The workflow uses the Bumpless action from https://github.com/Fushiguro6286/bumpless (or your fork).
3. Add `NEBIUS_API_KEY` and `TAVILY_API_KEY` under **Settings → Secrets and variables → Dependabot**, and again
   under **Actions** (the `@bumpless` comment job and manual runs read Actions secrets).
4. **Settings → Actions → General → Workflow permissions:** allow read and write, and tick **Allow GitHub
   Actions to create and approve pull requests** (manual runs open their own PR).

## Try it

- Wait for Dependabot's pydantic PR, or run the **Bumpless** workflow by hand (Actions → Bumpless → Run
  workflow: package `pydantic`, target `>=2,<3`). A manual run opens its own PR with the report as its body.
- On the PR, comment `@bumpless explain the change in app/models.py`.

The app's `app/storage.py` is deliberately untested, so the report marks its changes Low confidence.

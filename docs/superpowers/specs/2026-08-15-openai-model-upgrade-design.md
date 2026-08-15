# OpenAI Model Upgrade

## Goal

Use the current flagship OpenAI models for RoomSwipe's room analysis and image generation without changing API contracts or exposing local secrets.

## Changes

- Set the room-analysis default to `gpt-5.6-sol`, the flagship vision-capable GPT-5.6 model.
- Set the image generation and editing default to `gpt-image-2`, the current state-of-the-art image model.
- Update `backend/.env.example` with the same model IDs and the Vite development CORS origins.
- Update the ignored local `backend/.env` so local testing uses the new models.
- Add or adjust configuration tests to prevent the tracked defaults from drifting back to older model IDs.

## Secret Handling

`backend/.env` contains the user's API key. It remains ignored and must never be staged, committed, printed, or pushed. Only source code, tests, `.env.example`, and this specification are safe to add to Git.

## Compatibility

The existing `/v1/responses`, `/v1/images/edits`, and `/v1/images/generations` request structures remain unchanged. Both selected models support the modalities and endpoints used by RoomSwipe. No frontend or response-schema change is required.

## Verification

- Run the image-generation tests and configuration tests.
- Run the complete backend and ML test suite.
- Run Ruff across backend source and tests.
- Confirm `backend/.env` is ignored and absent from Git status.
- Pull the latest `master` before pushing the feature branch.

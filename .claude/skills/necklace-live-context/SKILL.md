---
name: necklace-live-context
description: >
  Use when Pawkeyland pet chat needs current necklace facts: pet location,
  home/safe-area state, recent action, current-day/month action summary, or current
  track coverage.
argument-hint: "Choose the specific zero-argument tool; current pet and time parameters are server-bound."
---

# Necklace Live Context

This workspace skill is for **runtime pet chat**, not authoring. It is copied
from the repository-owned `.claude/skills` directory into each session workspace;
do not depend on the developer's global Claude skills.

## Tool

Use one of the zero-argument `mcp__necklace__*` tools below. The tool name is
the query intent.

The server binds the current chat pet through MCP subprocess environment
variables derived from `agent_pet` / remote DB identity. Do not pass `pet_id` or
`pet_type`, fields, action type, dates, months, start/end timestamps, or recent
windows; they are not Agent-facing parameters. The tools are read-only and
return JSON. Only the `live_context` object is safe to treat as factual context
for the reply. If `ok=false`, `error=no_data`, or `live_context` is empty, the
agent has no usable hardware fact for this turn.
If some requested fields appear in `unavailable`, those specific dimensions
also have no usable facts and must not be filled from persona or common pet
habits.

## When To Call

Call only when the user asks for or the reply genuinely needs current hardware
facts:

- current pet location and whether the pet is still at home / in a safe home area;
- recent pet action;
- single action stat for debugging or an explicit single-action user question;
- current-day or current-month action summary;
- current-day location track;
- current-month days with location data.

Do not call for normal affection, greetings, high-emotion comfort, or purely
persona-driven replies.

For "what are you doing / 今天在干嘛 / 最近做什么" questions, request
`mcp__necklace__get_pet_recent_activity`; use
`mcp__necklace__get_pet_today_activity` when the question is day-level. These
activity tools already include the server-owned field bundle. Use location
facts only to express whether the pet is at home / in a safe home area, not to
infer whether the user has returned.

## Tool Guide

- `mcp__necklace__get_pet_location` -> `live_context.pet_location`, plus optional
  `env_pressure`, `env_signal`, `necklace_status`. Upstream `isFamilyWifi` and
  `isFence` are merged by the gateway into the single boolean
  `pet_location.at_home`; do not say "围栏" or repeat both states to the user.
- `mcp__necklace__get_pet_recent_activity` -> `pet_location` plus
  `live_context.pet_action_recent`; the gateway uses server time and at least a
  30-minute recent window.
- `mcp__necklace__get_pet_today_activity` -> `pet_location`,
  `pet_action_recent`, and `live_context.pet_action_day`; the gateway uses the
  server-side current date.
- `mcp__necklace__get_pet_month_activity` -> `live_context.pet_action_month`;
  use only for explicit month-level questions.
- `mcp__necklace__get_pet_today_location_track` ->
  `live_context.pet_track_today`; use only for explicit track questions.
- `mcp__necklace__get_pet_month_location_days` -> `location_days`; use only for
  explicit coverage-date questions and do not turn it into a user fact unless
  the user asked about history coverage.

## Parameters

There are no Agent-facing parameters. Do not supply date, month, start/end
timestamps, recent window, pet id, pet type, fields, or action type. The gateway
reads server-side time, enforces a minimum 30-minute interval for time ranges,
and sends only the required Swagger parameters. Upstream pet-type enum
differences are handled inside the gateway; do not reason about `petType`.

## Safety

The necklace senses the pet and its device, not the user. Do not infer the
user's location, activity, health, sleep, social context, or mood from necklace
data. If a user-facing sentence needs a bridge from pet state to user state,
use vague language and only when the current conversation supports it.
`pet_location.at_home` means the pet is at home / in a safe home area; it does
not mean the user is home, has returned, has not gone out, or is with the pet.
If `pet_location` is present but `recent_actions` or `day_stat` is unavailable,
you may say the pet is still at home, but must not invent activities such as
sleeping, lying down, walking, playing, waiting for the user, sunlight, windows,
birds, weather, or other scene details.

When the tool returns `ok=false`, `error=no_data`, or an empty `live_context`,
do not fill the gap from persona, common pet habits, or guesses. Reply only with
a pet-voice uncertainty such as not being sure or the collar not catching it.
Do not add concrete activity or scene details such as sleeping, walking,
playing, lying by a window, sunlight, birds, weather, or location details.

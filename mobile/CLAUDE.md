# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

The Expo (SDK 54) mobile frontend for CAMI — a conversational AI journaling app for mental health. Connects to a FastAPI backend at `localhost:8000`. See the parent `../CLAUDE.md` for full-system context (agents, API, CLI).

## Development

```bash
# Start the Expo dev server (press 'i' for iOS Simulator)
npx expo start

# The FastAPI backend must be running first
cd ../api && uvicorn main:app --reload --port 8000
```

No tests exist in the mobile directory. After changing API-facing behavior, run the integration test from the project root:

```bash
source ../.env && python ../test_api.py
```

## Architecture

Expo Router (file-based routing) with two screens and a shared layout:

- **`app/_layout.tsx`** — Root `Stack` navigator wrapped in `GestureHandlerRootView` (required for gesture-handler v2). Defines dark theme colors.
- **`app/index.tsx`** — Welcome screen. Renders `Trackball` for 2D emotion input (valence × support type, both normalized to [-1, 1]). Has a Journal/Pin agent toggle. Calls `createSession()` then navigates to `/chat` with `sessionId`.
- **`app/chat.tsx`** — Chat screen. Inverted `FlatList` for messages, typing indicator (`"..."` placeholder), optimistic message insertion on send, and a reframe button that appears in the header after 3+ exchanges.

### Components

- **`Trackball.tsx`** — `Gesture.Pan()` + `useSharedValue`/`useAnimatedStyle`. The `clamp()` helper is annotated `"worklet"` to run on the UI thread; `runOnJS()` bridges the position callback back to JS.
- **`ChatBubble.tsx`** — User (right, blue `#5E8CFF`), assistant (left, `#2a2a2a`), reframe (left, green `#1a3a2a` with italic header).
- **`ChatInput.tsx`** — Multiline input, max 100px height. Send button disables when empty or `disabled` prop is true.

### API Client (`lib/api.ts`)

All HTTP goes through a private `request<T>()` wrapper with 90-second `AbortController` timeout (Claude responses are slow). Targets `http://localhost:8000`.

| Function | Endpoint | Notes |
|---|---|---|
| `createSession(valence, supportType, model?, agent?)` | `POST /session` | Defaults: model `"sonnet"`, agent `"journal"` |
| `getSession(sessionId)` | `GET /session/{id}` | Returns full message history |
| `sendMessage(sessionId, content)` | `POST /session/{id}/message` | Returns agent reply |
| `reframe(sessionId)` | `POST /session/{id}/reframe` | Returns reframed journal entry |

## Conventions

- **Dark theme everywhere**: backgrounds `#121212`/`#1a1a1a`, accent `#5E8CFF`, text white.
- **No state management library** — plain `useState`/`useEffect`/`useCallback`.
- **Inline `StyleSheet.create()`** per component. No shared style utilities.
- **Errors surface via `Alert.alert()`** — all async calls are try/catch wrapped.
- **TypeScript strict mode** is on. All props use local interfaces.
- `App.tsx` and `index.ts` at the root are dead code — Expo Router's entry point (`expo-router/entry` in package.json `"main"`) takes over.

## Dependency Pinning

`react-native-worklets` **must stay at 0.5.1** to match Expo Go's native binary. Bumping it causes a JS/native mismatch crash. Only update when upgrading the Expo SDK itself.

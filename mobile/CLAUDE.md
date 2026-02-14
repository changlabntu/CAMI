# CLAUDE.md — Mobile Frontend

## What This Is

React Native + Expo (SDK 54) mobile app for CAMI. Two-screen flow: a welcome screen with a 2D emotion trackball, then a chat-based journaling session powered by the FastAPI backend (`../api/`).

## Running

```bash
# 1. Start the API backend first (required)
cd ../api && uvicorn main:app --reload --port 8000

# 2. Start Expo, press 'i' for iOS Simulator
npx expo start --clear
```

No test suite or linter. TypeScript strict mode is on (`tsconfig.json`).

## Structure

```
mobile/
├── app/
│   ├── _layout.tsx        # Stack navigator, dark theme, GestureHandlerRootView wrapper
│   ├── index.tsx          # Welcome screen — Trackball + "Start Journaling" button
│   └── chat.tsx           # Chat screen — message list, send, reframe
├── components/
│   ├── Trackball.tsx      # 2D pan gesture for emotion input
│   ├── ChatBubble.tsx     # Message bubble (user/assistant/reframe variants)
│   └── ChatInput.tsx      # Multiline text input + send button
├── lib/
│   └── api.ts             # HTTP client for FastAPI backend
├── app.json               # Expo config (dark UI, portrait, new arch enabled)
├── package.json
└── tsconfig.json
```

## Screen Flow

1. **Welcome** (`index.tsx`) — User drags ball on Trackball to set emotion coordinates. Live text shows description ("Feeling somewhat down, wanting compassion"). "Start Journaling" calls `POST /session` with valence + support_type, navigates to chat with `sessionId`.

2. **Chat** (`chat.tsx`) — Loads existing messages from `GET /session/{id}` on mount. Inverted FlatList for messages. Typing indicator ("...") shown while waiting. "Reframe" button appears in header after 3+ exchanges; shows confirmation dialog, calls `POST /session/{id}/reframe`, displays result as a special green-tinted bubble.

## Key Components

### Trackball (`components/Trackball.tsx`)
- 260px circular area with 50px draggable ball
- Uses `Gesture.Pan()` (gesture-handler v2) + `useSharedValue`/`useAnimatedStyle` (reanimated)
- `clamp()` runs as a worklet to constrain ball within circle
- Outputs: `valence = x/radius` (-1..1), `supportType = -y/radius` (-1..1)
- Axis labels: Left=Bad, Right=Good, Top=Advice, Bottom=Compassion

### ChatBubble (`components/ChatBubble.tsx`)
- User: right-aligned, blue (`#5E8CFF`)
- Assistant: left-aligned, dark gray (`#2a2a2a`)
- Reframe: left-aligned, green-tinted (`#1a3a2a`) with italic header

### ChatInput (`components/ChatInput.tsx`)
- Multiline TextInput, disabled during loading
- Send button grayed out when empty or loading

## API Client (`lib/api.ts`)

All requests target `http://localhost:8000` with 90-second timeout (Claude responses can take 10-30+ seconds).

| Function | Endpoint | Notes |
|---|---|---|
| `createSession(valence, supportType)` | `POST /session` | Returns `session_id` + `greeting` |
| `getSession(sessionId)` | `GET /session/{id}` | Returns message history |
| `sendMessage(sessionId, content)` | `POST /session/{id}/message` | Returns assistant reply |
| `reframe(sessionId)` | `POST /session/{id}/reframe` | Returns reframed journal entry |

## Design Tokens

- Background: `#121212` (screens), `#1a1a1a` (header)
- Accent: `#5E8CFF` (buttons, user bubbles, trackball ball)
- Reframe green: `#1a3a2a` (bubble), `#8fdfb0` (text)
- Text: `#fff` (primary), `#aaa` (secondary), `#888` (labels)

## Known Issues / Gotchas

- `react-native-worklets` must be pinned to **0.5.1** to match Expo Go's native binary. If you run `npm install` and it upgrades to 0.7+, you'll get a JS/native mismatch error. Fix: `npm install react-native-worklets@0.5.1 --legacy-peer-deps`.
- Use `npx expo install --fix` to align other deps with SDK 54, but it won't catch the worklets issue.
- The API URL is hardcoded to `localhost:8000` in `lib/api.ts`. For device testing, change to your machine's local IP.
- `GestureHandlerRootView` must wrap the entire app (done in `_layout.tsx`) or gestures won't work.

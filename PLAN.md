# CAMI Mobile App — Welcome Screen + Journal Chat

## Context

CAMI currently has a CLI-only journal agent (`talk_to_journal.py` → `JournalAgent`). We're building a React Native + Expo mobile app with a FastAPI backend. The first screen is a **2D trackball** for emotion input (valence: bad↔good, support: compassion↔advice), which then feeds into a chat-based journaling session.

## Project Structure

```
CAMI/
├── agents/                    # existing — untouched
│   └── agent_journal.py       # JournalAgent class
├── api/                       # NEW — FastAPI backend
│   ├── main.py
│   └── requirements.txt
├── mobile/                    # NEW — Expo React Native app
│   ├── app/
│   │   ├── _layout.tsx        # Stack navigator
│   │   ├── index.tsx          # Welcome screen (trackball)
│   │   └── chat.tsx           # Chat screen
│   ├── components/
│   │   ├── Trackball.tsx      # 2D emotion trackball
│   │   ├── ChatBubble.tsx     # Message bubble
│   │   └── ChatInput.tsx      # Text input + send button
│   ├── lib/
│   │   └── api.ts             # HTTP client for FastAPI
│   ├── app.json
│   ├── package.json
│   └── tsconfig.json
├── talk_to_journal.py         # existing — untouched
└── .env                       # existing — API keys
```

## Phase 1: FastAPI Backend (`api/main.py`)

**File:** `api/main.py`

- Import `JournalAgent` from `agents/agent_journal.py` via `sys.path` insert
- Load `.env` from parent directory
- In-memory session store: `dict[str, JournalAgent]`
- CORS middleware (allow all for dev)

**Endpoints:**

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/session` | POST | `{ valence: float, support_type: float, model?: str }` | `{ session_id, greeting }` |
| `/session/{id}/message` | POST | `{ content: str }` | `{ role, content, metadata }` |
| `/session/{id}/reframe` | POST | — | `{ reframed_entry, metadata }` |

**Emotion → System Prompt:** On session creation, append a natural-language description of the emotion coordinates to `agent.messages[0]["content"]` (the system prompt). No changes to `agent_journal.py` needed.

```python
def describe_emotion(valence: float, support_type: float) -> str:
    # Maps valence (-1..1) to feeling description
    # Maps support_type (-1..1) to counselor approach description
    # Returns a paragraph appended to SYSTEM_PROMPT
```

**Strip "Counselor:" prefix** from `reply()` response before returning to the client (the chat UI uses bubble alignment instead).

**`api/requirements.txt`:** `fastapi`, `uvicorn[standard]`, `python-dotenv`, `langchain-anthropic`, `langchain-core`

## Phase 2: Expo App Scaffold

```bash
cd CAMI
npx create-expo-app mobile --template blank-typescript
cd mobile
npx expo install expo-router react-native-safe-area-context react-native-screens expo-linking expo-constants expo-status-bar
npx expo install react-native-reanimated react-native-gesture-handler
```

- `app/_layout.tsx` — Stack navigator, dark theme
- `app/index.tsx` — Welcome screen placeholder
- `app/chat.tsx` — Chat screen placeholder
- `lib/api.ts` — `createSession()`, `sendMessage()`, `reframe()` functions

## Phase 3: Trackball Component (`components/Trackball.tsx`)

**How it works:**
- Circular area (~260px diameter) with a draggable ball (~50px) inside
- Uses `Gesture.Pan()` from gesture-handler v2 + `useSharedValue`/`useAnimatedStyle` from reanimated
- On each pan update: compute distance from center, clamp to circle radius
- Track offset so re-grab continues from current position (not center)
- `onPositionChange(valence, supportType)` callback: `valence = x/radius`, `supportType = -y/radius`

**Axis labels** positioned around the circle:
- Left: "Bad" / Right: "Good"
- Top: "Advice" / Bottom: "Compassion"

**Welcome screen (`app/index.tsx`):**
- Trackball component at center
- Live text below trackball showing current emotion description
- "Start Journaling" button → calls `POST /session`, navigates to `/chat` with `sessionId` + `greeting` as params

## Phase 4: Chat Screen (`app/chat.tsx`)

- Read `sessionId` and `greeting` from route params via `useLocalSearchParams()`
- Initialize messages with the greeting as first assistant message
- **FlatList** (inverted) for message rendering
- **ChatBubble**: user messages right-aligned (accent color), assistant left-aligned (dark gray)
- **ChatInput**: multiline TextInput + Send button, disabled while loading
- **Send flow**: append user msg → call API → append assistant msg
- **Typing indicator** (animated dots) while waiting for response
- **KeyboardAvoidingView** with `behavior="padding"` for iOS
- **Reframe button** in header — calls `/session/{id}/reframe`, displays result as a special styled message

## Implementation Order

1. **`api/main.py`** + `api/requirements.txt` — Build and test with curl
2. **Expo scaffold** — `create-expo-app`, install deps, set up routing + `lib/api.ts`
3. **Trackball.tsx** — Gesture + animation component
4. **Welcome screen** — Wire trackball → API → navigate to chat
5. **ChatBubble + ChatInput** components
6. **Chat screen** — Message list, send flow, typing indicator, reframe button
7. **Polish** — Error handling, strip "Counselor:" prefix, `.gitignore` updates

## Verification

1. Start FastAPI: `cd api && uvicorn main:app --reload --port 8000`
2. Test endpoints with curl (create session → send messages → reframe)
3. Start Expo: `cd mobile && npx expo start`
4. Open on iOS simulator or device via Expo Go
5. Full flow: position trackball → tap Start → chat with agent → tap Reframe

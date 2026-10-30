# NeuroLift AI-Fusion — Mobile App (iOS & Android)

Expo React Native app for the NeuroLift simulation environment, targeting iOS and Android.

## Stack

| Layer | Technology |
|---|---|
| Framework | Expo SDK 57 + React Native 0.86 |
| Language | TypeScript |
| Navigation | Expo Router (file-based) |
| Linting | ESLint 9 + `eslint-config-expo` (flat config, see `eslint.config.js`) |
| Styling | React Native StyleSheet |
| HTTP | Native `fetch` |
| Backend | FastAPI (`/backend`) |

## Quick Start

```bash
cd apps/mobile

# Install dependencies
npm install

# Start Expo development server
npx expo start
```

Then press:
- `i` — open iOS Simulator (macOS only)
- `a` — open Android Emulator
- `w` — open in browser
- Scan QR code with Expo Go on a physical device

## Screens

| Tab | Description |
|---|---|
| Dashboard | Stats overview and process summary |
| Avatars | Create and monitor Avatar instances |
| Aides | Create and manage Aide coaching instances |
| Sessions | Start and track training sessions |
| Fusion | Attempt Avatar + Aide → Advocate fusion |

## Environment Variables

Create a `.env.local` file:

```env
EXPO_PUBLIC_API_URL=http://your-backend-host:8000/api
```

> **Note:** When running on a physical device, replace `localhost` with your machine's local IP address.

## Workspace dependency notes

This app is an npm workspace member of the repository root. The `Mobile — Type Check
& Lint` job installs from the workspace root, so both apps share one hoisted
`node_modules`. Two consequences are pinned deliberately:

- The root `package.json` pins `eslint` 9 and `react`/`react-dom` 19 as dev
  dependencies. `eslint-config-expo` 57 flat config requires `eslint/config`, which
  only exists in ESLint >= 9, and `expo-doctor` rejects two React majors in one
  tree. Pinning them at the root hoists the majors this app needs; `apps/web` keeps
  its own ESLint 8 / React 18 copies nested (and installs independently in its own
  job). Removing those pins brings back
  `ERR_PACKAGE_PATH_NOT_EXPORTED: './config'` from `expo lint`.
- The root `overrides` entry pins `react-native-screens` to the SDK-expected
  4.26.x. Without it npm keeps a second copy under `expo-router`, which
  `expo-doctor` reports as a duplicate native module.

`eslint.config.js` is committed on purpose: when it is missing, `expo lint`
generates one at run time, so CI lint rules would depend on whatever
`eslint`/`eslint-config-expo` versions Expo happened to install that day.

## Build for Production

```bash
# Install EAS CLI
npm install -g eas-cli

# Configure EAS
eas build:configure

# Build for iOS
eas build --platform ios

# Build for Android
eas build --platform android
```

## Project Structure

```
apps/mobile/
├── app/
│   ├── _layout.tsx          # Root stack layout
│   └── (tabs)/
│       ├── _layout.tsx      # Tab bar layout
│       ├── index.tsx        # Dashboard
│       ├── avatars.tsx      # Avatars
│       ├── aides.tsx        # Aides
│       ├── sessions.tsx     # Sessions
│       └── fusion.tsx       # Fusion
├── src/
│   └── api/
│       └── client.ts        # API client
├── assets/                  # Icons, splash screen
├── app.json                 # Expo config
└── package.json
```

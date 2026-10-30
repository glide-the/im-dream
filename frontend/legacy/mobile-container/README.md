<!-- [Sync] 2026-10-25: document the explicit app-hosted Bash qualification fixture; original env and production command denial remain. -->
<!-- [Sync] 2026-10-25: record ordinary env equality, original Session relocation/resume, and the remaining intermittent completion feedback failure. -->
<!-- [Sync] 2026-10-25: qualify mandatory sandbox startup with the immutable iOS command-denial backend; Bash execution remains pending. -->
<!-- [Sync] 2026-10-25: 复用原env键与正常网页登录，撤回新增Admin客户端类型；当前产物保留本机验收范围。 -->
<!-- [Sync] 2026-10-25: preserve web authentication and visual resources; remove native account RPCs. -->
<!-- [Sync] 2026-10-25: prepare Node24/original Runtime and record relay-free SDK protocol qualification. -->
<!-- [Sync] 2026-10-25: record packaged iOS Simulator web login and real Chat acceptance. -->
<!-- [Sync] 2026-10-25: use the public Admin authority and relay only the Mac Dream Web port. -->
<!-- [Input] Canonical React source, shared bridge manifest, native host sources, and qualified embedded runtimes. -->
<!-- [Output] Reproducible local build and validation entry points for iOS and Android containers. -->
<!-- [Pos] Mobile workspace guide; release policy is documented in docs/deploy/mobile-app-release.md. -->
<!-- [Sync] 2026-10-25: document the configured iOS LAN Web flow, signed development artifact, and physical business-test boundary. -->
<!-- [Sync] 2026-10-25: embed the iOS public Python backend slice and document its build prerequisite. -->
<!-- [Sync] 2026-10-24: simplify iOS to the WebView container and direct startup replies. -->
<!-- [Sync] 2026-10-24: align scoped transport, empty external allowlists, and Android bootstrap prerequisites. -->

<!-- [Sync] 2026-10-25: document the credential-free original Next standalone build and same-ASGI application HTTP path. -->

# Ink & Memory mobile hosts

## React Native iOS delivery — 2026-10-27

The current iOS entry is `react-native/src/App.tsx`, linked into the existing `ios/InkMemory.xcworkspace`. RN owns startup/recovery, Chat/Decks/More and the More navigation screen. The native `InkBusinessSurface` retains the original persistent WKWebView and its normal Web login. Original Python, Node, Next and Claude run in the application. The earlier implementation records below retain their original dates and validation scope.

Install the locked RN packages with `pnpm --dir mobile/react-native install --frozen-lockfile`, then run `pod install --deployment` in `mobile/ios`. Existing prepared Python/Node/Guest resources remain prerequisites. Build a standalone package with:

```bash
bash mobile/ios/scripts/build-rn-ios.sh 'id=<paired iPhone UDID>'
```

The default configuration is Release. `CONFIGURATION=Debug` selects a development build. `INK_IOS_DERIVED_DATA` and `INK_IOS_BUILD_JOBS` configure build output and parallelism. RN JavaScript is bundled inside the app. Original Web resources are built in the isolated Next source directory.

Hardware acceptance has verified original normal Web login, account/session/CSRF, Thread/Deck/model reads, native RN root, retained WebView identity through three routes, mobile Dream exclusion and one real Chat with 73 stream chunks, EOF and persisted assistant output. Stop, reopening and final package evidence continue in the [current execution record](../docs/exec/mobile-app-design-review-20261024.md#2026-10-27-rn-ios实施与交付).

`scripts/run-business-acceptance.py` selects explicit app-hosted tests. A password is read only when `--password` is supplied, with terminal echo disabled, and reaches a temporary mode-0600 xctestrun. The temporary configuration is removed after the run. Real Chat requires `--model-alias`; one test permits one submission and records only transport/persistence metadata. Existing history and normal business records remain available.

The mobile workspace contains two native applications:

- `ios/`: React Native with the existing Swift runtime and WKWebView adapters.
- `android/`: Kotlin and Android WebView.

Both hosts retain one React business source in `frontend/app/_dream` and one versioned bridge manifest in `shared/bridge/contract.json`. The iOS independent path packages the original Next standalone server with the same React, Route Handlers and BFF. Android retains its earlier local-resource scaffold. The existing Web deployment remains independently maintained.

## 2026-10-25 implementation record

Both hosts share the same React business source. An iOS build with an empty `DREAM_LAN_HOST` loads the original Next standalone server at the registered loopback origin from the ordinary env, with `ios/host-config.json` as its fallback. Its original HTTP proxy connects to the same application-owned ASGI instance through an ephemeral loopback listener. The explicit historical `DREAM_LAN_HOST` option starts a development relay for port 5173 and loads the existing Mac Dream Web/BFF at `http://localhost:5173/`. Authentication uses the existing Dream web form, the public Admin HTTPS authority, and the original BFF callback; the native bridge has no account methods. The iOS host directly handles app information, startup readiness, and lifecycle/network state. Android retains its earlier scaffold. Requests carry page generation and identifiers. Existing business entry points and login rules remain unchanged.

The iOS app starts bundled CPython 3.13.17 and FastAPI before loading the React entry. After the native Runtime endpoint qualifies, it mounts the same 24 production router modules plus `routers.public`, with the original application-owned ThreadFactory. Its native adapter forwards validated method, query, headers and bounded inline body to the same in-process ASGI application. `/api/default-voices` returns the original five configured voices and prompt content. Protected user/profile, Session, Deck, preference and report routes require original authorization and return 401 without it. A signed physical build has reached the original React page over Wi-Fi. The same packaged host completed the existing password login through the public Admin authority, the BFF session, workspace loading, and one real Chat turn in iOS Simulator. The paired phone must become available before repeating that acceptance on hardware. Original Next-to-ASGI HTTP and WKWebView React hydration have target receipts. Authenticated business, attachments and the complete Claude toolset on iOS remain unqualified. Android's runtime integration remains pending. Current execution and device-signing evidence is recorded in [the implementation review](../docs/exec/mobile-app-design-review-20261024.md#2026-10-25-公网admin切换与模拟器验收).

## Validation

The relay-free iOS compatibility path embeds the original Runtime 0.1.12 JavaScript in Node24 workers within the application process. Target tests have exercised original SDK initialization, streaming, Read/Write, SDK MCP, permission denial, session resume and interrupt with mandatory sandbox settings enabled. The iOS command backend freezes and verifies native external-process denial; every Bash/external command receives ENOSYS. The original CLI startup gate and tool permission checks remain active. The persistent Python ASGI adapter and native concurrent read/cancel have separate target receipts. The fifth visible Chat submission completed a real model turn through the original React, BFF and on-device Python/Runtime, with the expected reply, terminal UI, and normal Admin message/settlement records. Ordinary reopening restored history. The seventh submission resumed the same Session and produced a new real reply and normal settlement; its completion UI timed out. Node path formatting and exclusive container-directory relocation preserve the original transcript bytes. A subsequent original-Session follow-up completed with terminal feedback, and the original Stop action retained a partial reply and normal cancellation settlement. Attachments, broader stability, the complete toolset and physical-device qualification remain pending. The independent receipts and earlier Mac relay receipt remain separately recorded in the implementation review.

From the repository root:

```bash
python3 mobile/ios/scripts/prepare-python.py
python3 mobile/ios/scripts/prepare-node.py
python3 mobile/ios/scripts/prepare-next.py
(cd mobile/ios/Next/build-source && env -i PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" NEXT_TELEMETRY_DISABLED=1 CI=1 node node_modules/next/dist/bin/next build --webpack)
node mobile/scripts/check-bridge-contract.mjs
corepack pnpm --dir frontend mobile:test
xcodebuild -workspace mobile/ios/InkMemory.xcworkspace -scheme InkMemory -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
```

The preparation command requires Apple Silicon macOS, Xcode, Cargo and an existing host `python3.13`. It downloads SHA-256-pinned CPython, pure Python wheels and a matching local Rust compiler, then builds the locked pydantic-core 2.41.5 for arm64 device/simulator. All dependency files remain under ignored `mobile/ios/Python/`. Xcode copies explicit backend sources and converts native extension modules to framework bundles. The local resource phase copies existing `backend/.env` to `app/.env` for Python and existing `frontend/.env.local` beside the original Next server for Node. Both consumers retain existing filenames and key names. Admin credentials are consumed only by the original BFF/data clients. An unsigned iPhoneOS build requires `CODE_SIGNING_ALLOWED=NO`; actual iPhone installation requires Developer Mode, a development Team and valid provisioning. Distribution license notices for Rust transitive dependencies still require completion before external distribution.

`prepare-node.py` verifies the Node Mobile archive SHA-256 and the published original Runtime archive SHA-512. It prepares only JavaScript, the Node library and license/provenance files under ignored `mobile/ios/Node/` and `mobile/ios/RuntimeArtifacts/`. Tracked adapter sources remain in `mobile/ios/runtime/`. Desktop executables remain excluded. Build this path with `DREAM_LAN_HOST=`; protocol tests assert that the Mac relay is disabled.

Android requires JDK 17, Android SDK 36, Build Tools 36.x, and Gradle 9.6. The repository pins the distribution in `gradle/wrapper/gradle-wrapper.properties`; it does not contain `gradlew` or the wrapper JAR. Run the preflight first, then generate the wrapper during the dependency-initialization task:

```bash
cd mobile/android
sh scripts/check-toolchain.sh
# After the missing SDK and Gradle bootstrap have been installed in a later task:
gradle wrapper --gradle-version 9.6.0
./gradlew testDebugUnitTest assembleDebug
```

The isolated Next build uses existing frontend dependencies and copies no `.env` file. `prepare-next.py` leaves the existing `frontend/.next` and Mac Web process untouched. `bundle-next.py` relocates traced dependency links into the application, retains original static/public assets and excludes desktop native modules. Original Next image optimization through native Sharp remains unqualified. The runtime build phase copies the existing normal env separately from React resources, with file mode 0600. The original configured loopback origin selects the existing registered callback; no extra client type or authentication mode is introduced. Current local build artifacts contain the configured service/Cookie material and require credential review before external distribution. Actual login and model acceptance remain separate from the successful local build.

Generated Next/Web resources and native build directories are excluded from Git.


## Explicit POSIX compatibility qualification

The named native fixture runs actual ARM64 Linux Bash inside the existing Dream Simulator app host. Its private pipes, arrays, command substitution, background wait, file writes and exit code passed. The original Runtime retains its external-command ENOSYS boundary. Original Node/Python child-process integration, command permission equivalence, cancellation and hardware execution require further qualification.

The builder uses the existing app, exact temporary source/patch and already compiled target archives; it installs no dependency. The interpreter source remains in the owned temporary prototype directory. Run from the repository root with the recorded local inputs:

```bash
python3 mobile/ios/scripts/build-posix-qualification.py \
  --prototype /tmp/ink-ios-posix-compat-20261025 \
  --app /tmp/ink-ios-node-compat-20261025/Build/Products/Debug-iphonesimulator/InkMemory.app \
  --xctestrun /tmp/ink-ios-first-reply-stop-real-20261025.xctestrun \
  --output /tmp/ink-ios-posix-compat-20261025/repository-fixture
```

This command compiles and signs only an owned app copy. The generated `simulator-fixture.xctestrun` selects one provider-free `PosixCompatibilityTests` method. These C/Objective-C sources remain outside the standard Xcode targets. Source provenance, package licenses, failed first receipts and actual `xcodebuild test-without-building` command are preserved in the [execution record](../docs/exec/mobile-app-design-review-20261024.md#2026-10-25-应用内系统命令执行兼容原型). Normal backend/frontend env remains byte-equal to the original files.

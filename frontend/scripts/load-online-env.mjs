// [Input] The complete private frontend .env.online file and inherited process configuration.
// [Output] Online Admin environment loaded before the unchanged Next.js CLI and its workers.
// [Pos] Node preloader for dev:online; --import remains valid in Next's child NODE_OPTIONS.
// [Sync] 2026-11-09: load dotenv through Node's API instead of the child-incompatible --env-file flag.
import { loadEnvFile } from 'node:process';
import { fileURLToPath } from 'node:url';

loadEnvFile(fileURLToPath(new URL('../.env.online', import.meta.url)));

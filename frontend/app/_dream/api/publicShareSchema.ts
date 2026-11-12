// [Input] Public text-only note/chat snapshot DTO.
// [Output] Shared server/client validation without account or platform imports.
// [Pos] Anonymous share wire boundary.
import {z} from 'zod';
export const publicShareSnapshot = z.discriminatedUnion('kind', [
  z.strictObject({kind: z.literal('note'), title: z.string(), created_at: z.string().nullable(), paragraphs: z.array(z.string())}),
  z.strictObject({kind: z.literal('chat'), title: z.string(), created_at: z.string().nullable(), messages: z.array(z.strictObject({role: z.enum(['user', 'assistant']), content: z.string()}))}),
]);
export type PublicShareSnapshot = z.infer<typeof publicShareSnapshot>;

import fr from "./fr.json";

/**
 * Minimal translation lookup. Every user-visible string goes through a key
 * (cahier des charges, partie 1.4); a full ICU library replaces this when the
 * back-office needs plurals or a second language.
 */
export type MessageKey = keyof typeof fr;

const messages: Record<MessageKey, string> = fr;

export function t(key: MessageKey): string {
  return messages[key];
}

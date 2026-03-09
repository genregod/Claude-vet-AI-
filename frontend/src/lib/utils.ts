import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Convert a human-readable quick-action label to the backend QuickAction
 * enum value. Example: "Learn about appeals" → "learn_about_appeals".
 */
export function toQuickActionEnum(label: string): string {
  return label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
}

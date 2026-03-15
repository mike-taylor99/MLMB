import { useEffect } from "react";

const SUFFIX = "MLMB";

/**
 * Set the browser document title reactively.
 *
 * Pass a page-specific string (e.g. "Predict") or a dynamic value
 * that may start as undefined while data loads.  When `title` is
 * falsy the document title is left unchanged.
 *
 * Format: "Title — MLMB"
 */
export function useDocumentTitle(title: string | undefined | null) {
  useEffect(() => {
    if (!title) return;
    document.title = `${title} — ${SUFFIX}`;
  }, [title]);
}

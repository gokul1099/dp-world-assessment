"use client";

import type { LicenceFields } from "@/types/licence";

interface LicenceFormProps {
  fields: LicenceFields;
  onSave: (fields: LicenceFields) => void;
}

// Features 3 & 4 — auto-populated form the user can review and correct before saving.
export function LicenceForm(_props: LicenceFormProps) {
  return <section aria-label="Extracted licence details">Licence form</section>;
}

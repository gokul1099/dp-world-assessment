"use client";

import { useState } from "react";

import { ApiError } from "@/api/client";
import { updateDocumentFields } from "@/api/documents";
import { SourceBadge } from "@/features/chat/SourceBadge";
import type { LicenceFields } from "@/types/licence";

interface LicenceFormProps {
  documentId: string;
  fields: LicenceFields;
  /** OCR text per page from the upload; saved together with the fields. */
  pageTexts: string[];
  /** Called with the saved fields once the backend has stored them. */
  onSaved: (fields: LicenceFields) => void;
  /** Show a page of the document in the viewer (from a field's "Page N" badge). */
  onShowPage: (page: number) => void;
}

type MainFieldKey = Exclude<keyof LicenceFields, "other_fields">;

interface FieldConfig {
  key: MainFieldKey;
  label: string;
  type: "text" | "date" | "textarea" | "classes";
  required?: boolean;
}

const MAIN_FIELDS: FieldConfig[] = [
  { key: "full_name", label: "Full name", type: "text", required: true },
  { key: "licence_number", label: "Licence number", type: "text", required: true },
  { key: "date_of_birth", label: "Date of birth", type: "date" },
  { key: "date_of_issue", label: "Date of issue", type: "date" },
  { key: "date_of_expiry", label: "Date of expiry", type: "date" },
  { key: "address", label: "Address", type: "textarea" },
  { key: "licence_classes", label: "Vehicle classes", type: "classes" },
  { key: "issuing_authority", label: "Issuing authority", type: "text" },
];

type FormValues = Record<MainFieldKey, string>;
type FormErrors = Partial<Record<MainFieldKey, string>>;
interface OtherValue {
  key: string; // original key from the API, kept so saving maps back correctly
  label: string;
  value: string;
  page: number | null;
}

// Turn the API's extracted fields into plain strings for inputs.
function toFormValues(fields: LicenceFields): FormValues {
  const values = {} as FormValues;
  for (const { key } of MAIN_FIELDS) {
    const raw = fields[key].value;
    values[key] = Array.isArray(raw) ? raw.join(", ") : (raw ?? "");
  }
  return values;
}

function toOtherValues(fields: LicenceFields): OtherValue[] {
  return Object.entries(fields.other_fields).map(([key, field]) => ({
    key,
    label: (key.charAt(0).toUpperCase() + key.slice(1)).replace(/_/g, " "),
    value: field.value ?? "",
    page: field.source_page,
  }));
}

// Turn the inputs back into the API shape, keeping each field's confidence and source page.
function toLicenceFields(original: LicenceFields, values: FormValues, other: OtherValue[]) {
  const result = { ...original, other_fields: { ...original.other_fields } };
  for (const { key } of MAIN_FIELDS) {
    const text = values[key].trim();
    const value =
      key === "licence_classes"
        ? text
          ? text.split(",").map((c) => c.trim()).filter(Boolean)
          : null
        : text || null;
    result[key] = { ...original[key], value } as never;
  }
  for (const item of other) {
    result.other_fields[item.key] = {
      ...original.other_fields[item.key],
      value: item.value.trim() || null,
    };
  }
  return result as LicenceFields;
}

function validate(values: FormValues): FormErrors {
  const errors: FormErrors = {};
  const today = new Date().toISOString().slice(0, 10);
  if (!values.full_name.trim()) errors.full_name = "Full name is required.";
  if (!values.licence_number.trim()) errors.licence_number = "Licence number is required.";
  // ISO dates (YYYY-MM-DD) compare correctly as strings.
  const { date_of_birth: dob, date_of_issue: issued, date_of_expiry: expires } = values;
  if (dob && dob >= today) errors.date_of_birth = "Date of birth must be in the past.";
  if (dob && issued && issued <= dob) errors.date_of_issue = "Must be after the date of birth.";
  if (issued && expires && expires <= issued)
    errors.date_of_expiry = "Must be after the date of issue.";
  return errors;
}

// Features 3 & 4 — auto-populated form the user reviews, corrects and saves.
export function LicenceForm({
  documentId,
  fields,
  pageTexts,
  onSaved,
  onShowPage,
}: LicenceFormProps) {
  const [values, setValues] = useState<FormValues>(() => toFormValues(fields));
  const [other, setOther] = useState<OtherValue[]>(() => toOtherValues(fields));
  const [errors, setErrors] = useState<FormErrors>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function update(key: MainFieldKey, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function updateOther(index: number, value: string) {
    setOther((prev) => prev.map((item, i) => (i === index ? { ...item, value } : item)));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      setSaveError("Please fix the highlighted fields.");
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      const saved = await updateDocumentFields(
        documentId,
        toLicenceFields(fields, values, other),
        pageTexts,
      );
      onSaved(saved.fields ?? toLicenceFields(fields, values, other));
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      aria-labelledby="licence-form-title"
      className="w-full rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950 sm:p-8"
    >
      <h2 id="licence-form-title" className="text-lg font-semibold">
        Licence details
      </h2>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
        Filled in automatically from the document. Check the details, correct anything that&apos;s
        wrong, then save.
      </p>

      <form
        noValidate
        className="mt-6 grid grid-cols-1 gap-x-4 gap-y-5 sm:grid-cols-2"
        onSubmit={handleSubmit}
      >
        {MAIN_FIELDS.map((config) => (
          <Field
            key={config.key}
            config={config}
            value={values[config.key]}
            error={errors[config.key]}
            notFound={fields[config.key].value === null}
            page={fields[config.key].source_page}
            onShowPage={onShowPage}
            disabled={saving}
            onChange={(value) => update(config.key, value)}
          />
        ))}

        {other.length > 0 && (
          <div className="col-span-full mt-2 grid grid-cols-1 gap-x-4 gap-y-5 border-t border-zinc-200 pt-5 dark:border-zinc-800 sm:grid-cols-2">
            <h3 className="col-span-full text-sm font-semibold text-zinc-700 dark:text-zinc-300">
              Other information
            </h3>
            {other.map((item, index) => (
              <div key={item.key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-2">
                  <label htmlFor={`other-${item.key}`} className={labelClass}>
                    {item.label}
                  </label>
                  {item.page && <SourceBadge source={{ page: item.page, snippet: null }} onShowPage={onShowPage} />}
                </div>
                <input
                  id={`other-${item.key}`}
                  type="text"
                  value={item.value}
                  disabled={saving}
                  onChange={(e) => updateOther(index, e.target.value)}
                  className={inputClass}
                />
              </div>
            ))}
          </div>
        )}

        <div className="col-span-full mt-2 flex flex-col gap-3 border-t border-zinc-200 pt-5 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            {saveError}
          </p>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            {saving && (
              <span
                aria-hidden="true"
                className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white dark:border-zinc-900/30 dark:border-t-zinc-900"
              />
            )}
            {saving ? "Saving…" : "Save and continue"}
          </button>
        </div>
      </form>
    </section>
  );
}

const labelClass = "text-sm font-medium text-zinc-700 dark:text-zinc-300";
const inputClass =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 disabled:opacity-60 aria-[invalid=true]:border-red-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:[color-scheme:dark] dark:aria-[invalid=true]:border-red-500";

interface FieldProps {
  config: FieldConfig;
  value: string;
  error?: string;
  notFound: boolean;
  page: number | null;
  onShowPage: (page: number) => void;
  disabled: boolean;
  onChange: (value: string) => void;
}

function Field({ config, value, error, notFound, page, onShowPage, disabled, onChange }: FieldProps) {
  const id = `field-${config.key}`;
  const messageId = `${id}-message`;
  const showNotFound = !error && notFound && value === "";
  const wide = config.type === "textarea" || config.type === "classes";
  const common = {
    id,
    value,
    disabled,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error || showNotFound ? messageId : undefined,
    className: inputClass,
  };

  return (
    <div className={`flex flex-col gap-1.5 ${wide ? "sm:col-span-2" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={id} className={labelClass}>
          {config.label}
          {config.required && <span className="text-red-600"> *</span>}
        </label>
        {page && <SourceBadge source={{ page, snippet: null }} onShowPage={onShowPage} />}
      </div>
      {config.type === "textarea" ? (
        <textarea {...common} rows={2} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input
          {...common}
          type={config.type === "date" ? "date" : "text"}
          placeholder={config.type === "classes" ? "e.g. B, C1" : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {error && (
        <p id={messageId} className="text-xs text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
      {showNotFound && (
        <p id={messageId} className="text-xs text-amber-700 dark:text-amber-400">
          Not found in document
        </p>
      )}
    </div>
  );
}

"use client";

import { useState, useRef } from "react";
import { X, Upload, FileText } from "lucide-react";
import { uploadDocuments } from "@/services/api";

const ACCEPT = ".pdf,.html,.htm";
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface UploadModalProps {
  onClose: () => void;
}

export default function UploadModal({ onClose }: UploadModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [bucket, setBucket] = useState<string>("");
  const [errors, setErrors] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (selected: FileList | null) => {
    if (!selected) return;
    const valid: File[] = [];
    const errs: string[] = [];
    for (let i = 0; i < selected.length; i++) {
      const f = selected[i];
      const ext = "." + (f.name.split(".").pop()?.toLowerCase() ?? "");
      if (![".pdf", ".html", ".htm"].includes(ext)) {
        errs.push(`${f.name}: unsupported type`);
        continue;
      }
      if (f.size > MAX_SIZE_BYTES) {
        errs.push(`${f.name}: exceeds ${MAX_SIZE_MB}MB`);
        continue;
      }
      valid.push(f);
    }
    setFiles((prev) => [...prev, ...valid]);
    setErrors((prev) => [...prev, ...errs]);
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    setErrors([]);
    try {
      const resp = await uploadDocuments(files);
      setErrors(resp.errors);
      if (resp.uploaded.length > 0) {
        setSuccess(true);
        setBucket(resp.bucket ?? "YOUR-PROJECT-raw-docs");
        setFiles([]);
      }
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message
        : e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Upload failed";
      setErrors([typeof msg === "string" ? msg : "Upload failed"]);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-[hsl(var(--background))] rounded-xl border border-[hsl(var(--border))] p-6 w-full max-w-md shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload Documents
          </h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-[hsl(var(--muted))]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {success ? (
          <div className="space-y-2">
            <p className="text-sm text-green-600 font-medium">
              Documents uploaded. Run ingestion to add them to the knowledge base.
            </p>
            <p className="text-xs text-[hsl(var(--muted-foreground))] font-mono break-all">
              PYTHONPATH=$PWD uv run --directory acquisition python -m acquisition.cli run --source-dir
              gs://{bucket}/uploads/ --chunk-method recursive --version 2 --skip-vertex
            </p>
            <button
              onClick={() => { setSuccess(false); onClose(); }}
              className="mt-2 px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--brand))] text-white hover:opacity-90"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              PDF or HTML files, max {MAX_SIZE_MB}MB each.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              multiple
              className="hidden"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
            />
            <button
              onClick={() => inputRef.current?.click()}
              className="w-full py-3 border-2 border-dashed border-[hsl(var(--border))] rounded-lg
                         hover:border-[hsl(var(--brand))] hover:bg-[hsl(var(--muted))]/30 transition
                         flex items-center justify-center gap-2 text-sm"
            >
              <FileText className="w-4 h-4" />
              Choose files
            </button>

            {files.length > 0 && (
              <ul className="text-sm space-y-1 max-h-32 overflow-y-auto">
                {files.map((f, i) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <span className="truncate">{f.name}</span>
                    <button
                      onClick={() => removeFile(i)}
                      className="text-red-500 hover:text-red-600 shrink-0"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {errors.length > 0 && (
              <ul className="text-sm text-red-600 space-y-1">
                {errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                           hover:bg-[hsl(var(--muted))] transition"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={uploading || files.length === 0}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--brand))] text-white
                           hover:opacity-90 disabled:opacity-50 transition"
              >
                {uploading ? "Uploading..." : "Upload"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

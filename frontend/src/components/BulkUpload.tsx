import { useCallback, useRef, useState } from "react";
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

const MAX_FILES = 50;
const MAX_SIZE_GB = 1;
const MAX_BYTES = MAX_SIZE_GB * 1024 * 1024 * 1024;
const API_BASE = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");

interface FileItem {
  file: File;
  status: "pending" | "uploading" | "processing" | "done" | "error";
  error?: string;
  result?: Record<string, unknown>;
}

interface Props {
  sessionId: string;
  onDocumentProcessed?: (result: Record<string, unknown>) => void;
}

export function BulkUpload({ sessionId, onDocumentProcessed }: Props) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const valid: FileItem[] = [];
    for (const f of Array.from(incoming)) {
      if (files.length + valid.length >= MAX_FILES) break;
      if (f.size > MAX_BYTES) continue; // skip oversized
      valid.push({ file: f, status: "pending" });
    }
    setFiles((prev) => [...prev, ...valid]);
  };

  const uploadFile = async (index: number) => {
    const item = files[index];
    if (!item || item.status !== "pending") return;

    // 1. Get presigned URL
    setFiles((prev) => prev.map((f, i) => i === index ? { ...f, status: "uploading" } : f));
    try {
      const urlRes = await fetch(
        `${API_BASE}/api/claims/session/${sessionId}/upload-url?filename=${encodeURIComponent(item.file.name)}&content_type=${encodeURIComponent(item.file.type || "application/octet-stream")}`,
        { method: "POST" }
      );
      if (!urlRes.ok) throw new Error("Failed to get upload URL");
      const { upload_url, s3_key } = await urlRes.json();

      // 2. PUT directly to S3
      const putRes = await fetch(upload_url, {
        method: "PUT",
        body: item.file,
        headers: { "Content-Type": item.file.type || "application/octet-stream" },
      });
      if (!putRes.ok) throw new Error("S3 upload failed");

      // 3. Trigger Claude extraction
      setFiles((prev) => prev.map((f, i) => i === index ? { ...f, status: "processing" } : f));
      const procRes = await fetch(
        `${API_BASE}/api/claims/session/${sessionId}/process-upload?s3_key=${encodeURIComponent(s3_key)}&filename=${encodeURIComponent(item.file.name)}`,
        { method: "POST" }
      );
      if (!procRes.ok) throw new Error("Processing failed");
      const result = await procRes.json();

      setFiles((prev) => prev.map((f, i) => i === index ? { ...f, status: "done", result } : f));
      onDocumentProcessed?.(result);
    } catch (e: any) {
      setFiles((prev) => prev.map((f, i) => i === index ? { ...f, status: "error", error: e.message } : f));
    }
  };

  const uploadAll = () => {
    files.forEach((_, i) => uploadFile(i));
  };

  const remove = (index: number) => setFiles((prev) => prev.filter((_, i) => i !== index));

  const pendingCount = files.filter((f) => f.status === "pending").length;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${dragging ? "border-navy bg-navy/5" : "border-gray-300 hover:border-navy hover:bg-gray-50"}`}
      >
        <Upload className="h-10 w-10 mx-auto text-gray-400 mb-3" />
        <p className="font-semibold text-gray-700">Drop documents here or click to browse</p>
        <p className="text-sm text-gray-500 mt-1">DD-214, STRs, medical records, nexus letters — up to {MAX_FILES} files, {MAX_SIZE_GB}GB each</p>
        <input ref={inputRef} type="file" multiple className="hidden"
          accept=".pdf,.txt,.md,.doc,.docx"
          onChange={(e) => addFiles(e.target.files)} />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border">
              <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{item.file.name}</p>
                <p className="text-xs text-gray-500">{(item.file.size / 1024 / 1024).toFixed(1)} MB</p>
              </div>
              <StatusIcon status={item.status} />
              {item.status === "done" && item.result && (
                <span className="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                  {(item.result as any).document_type ?? "Processed"}
                </span>
              )}
              {item.status === "error" && (
                <span className="text-xs text-red-600 truncate max-w-[120px]">{item.error}</span>
              )}
              {(item.status === "pending" || item.status === "error") && (
                <button onClick={() => remove(i)} className="text-gray-400 hover:text-red-500">
                  <X size={16} />
                </button>
              )}
            </div>
          ))}

          {pendingCount > 0 && (
            <Button onClick={uploadAll} className="w-full bg-navy text-white hover:bg-navy-dark mt-2">
              Upload & Analyze {pendingCount} Document{pendingCount > 1 ? "s" : ""}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: FileItem["status"] }) {
  if (status === "uploading" || status === "processing")
    return <Loader2 className="h-4 w-4 animate-spin text-navy" />;
  if (status === "done")
    return <CheckCircle className="h-4 w-4 text-green-600" />;
  if (status === "error")
    return <AlertCircle className="h-4 w-4 text-red-500" />;
  return null;
}

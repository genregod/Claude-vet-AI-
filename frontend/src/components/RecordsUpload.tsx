/**
 * RecordsUpload — Military records upload component with drag-and-drop
 *
 * Allows veterans to upload their DD-214, STRs, medical records, etc.
 * Uses AI to extract data and auto-fill the questionnaire.
 *
 * Features:
 *  - Drag-and-drop file upload zone
 *  - File type validation (PDF, TXT, MD)
 *  - Upload progress indicator
 *  - Shows extraction results: document type, confidence, affected pages
 *  - Lists previously uploaded files
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import {
  uploadMilitaryRecords,
  getUploadedFiles,
  type UploadRecordsResponse,
  type UploadedFile,
  type AIEstimates,
} from "@/lib/claimsApi";
import {
  Upload,
  FileText,
  FileCheck,
  AlertCircle,
  CheckCircle2,
  X,
  Loader2,
  Shield,
  File as FileIcon,
  Sparkles,
} from "lucide-react";

const ACCEPTED_TYPES = [".pdf", ".txt", ".md"];
const MAX_SIZE_MB = 20;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

const DOC_TYPE_LABELS: Record<string, string> = {
  dd214: "DD-214 (Discharge Papers)",
  str: "Service Treatment Records",
  va_rating: "VA Rating Decision",
  medical_records: "Medical Records",
  nexus_letter: "Nexus Letter",
  cp_exam: "C&P Exam Report",
  buddy_statement: "Buddy/Lay Statement",
  unknown: "Document",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-800",
  moderate: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-600",
};

interface RecordsUploadProps {
  sessionId: string;
  onAutoFill: (pages: Record<string, Record<string, unknown>>) => void;
  onEstimatesUpdate: (estimates: AIEstimates) => void;
}

export function RecordsUpload({
  sessionId,
  onAutoFill,
  onEstimatesUpdate,
}: RecordsUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [lastResult, setLastResult] = useState<UploadRecordsResponse | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Load previously uploaded files on mount
  useEffect(() => {
    async function loadFiles() {
      try {
        const data = await getUploadedFiles(sessionId);
        setUploadedFiles(data.files);
      } catch {
        // Silently fail — user can still upload
      }
    }
    loadFiles();
  }, [sessionId]);

  const validateFile = useCallback((file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      return `Unsupported file type "${ext}". Accepted: ${ACCEPTED_TYPES.join(", ")}`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum: ${MAX_SIZE_MB} MB`;
    }
    return null;
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        toast({
          title: "Invalid File",
          description: validationError,
          variant: "destructive",
        });
        return;
      }

      setError(null);
      setIsUploading(true);
      setUploadProgress(10);
      setLastResult(null);

      // Simulate progress while waiting for AI extraction
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 85) return prev;
          return prev + Math.random() * 10;
        });
      }, 500);

      try {
        const result = await uploadMilitaryRecords(sessionId, file);
        clearInterval(progressInterval);
        setUploadProgress(100);
        setLastResult(result);

        // Update uploaded files list
        setUploadedFiles((prev) => [
          ...prev,
          {
            filename: result.filename,
            saved_as: "",
            size_bytes: file.size,
            document_type: result.document_type,
            confidence: result.confidence,
            pages_affected: result.pages_affected,
          },
        ]);

        // Trigger auto-fill in the questionnaire
        if (
          result.auto_fill_pages &&
          Object.keys(result.auto_fill_pages).length > 0
        ) {
          onAutoFill(result.auto_fill_pages);
        }

        // Update AI estimates
        if (result.ai_estimates) {
          onEstimatesUpdate(result.ai_estimates);
        }

        toast({
          title: "Records Processed",
          description: result.message,
        });
      } catch (err) {
        clearInterval(progressInterval);
        const message =
          err instanceof Error ? err.message : "Upload failed. Please try again.";
        setError(message);
        toast({
          title: "Upload Failed",
          description: message,
          variant: "destructive",
        });
      } finally {
        setIsUploading(false);
        setTimeout(() => setUploadProgress(0), 2000);
      }
    },
    [sessionId, validateFile, onAutoFill, onEstimatesUpdate, toast]
  );

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleUpload(files[0]);
      }
    },
    [handleUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleUpload(files[0]);
      }
      // Reset input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [handleUpload]
  );

  return (
    <Card className="border-2 border-dashed border-gray-200 shadow-md">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-navy text-lg">
          <Upload className="h-5 w-5" />
          Upload Military Records
          <Badge variant="secondary" className="ml-auto text-xs">
            <Sparkles className="h-3 w-3 mr-1" />
            AI Auto-Fill
          </Badge>
        </CardTitle>
        <p className="text-sm text-gray-500">
          Upload your DD-214, service treatment records, medical records, or
          other military documents. Our AI will extract information and
          auto-fill the questionnaire for you.
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          className={`relative flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200 ${
            isDragOver
              ? "border-navy bg-navy/5 scale-[1.02]"
              : isUploading
              ? "border-gray-300 bg-gray-50 cursor-wait"
              : "border-gray-300 bg-white hover:border-navy/50 hover:bg-gray-50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            onChange={handleFileSelect}
            className="hidden"
            disabled={isUploading}
          />

          {isUploading ? (
            <div className="text-center space-y-3">
              <Loader2 className="h-10 w-10 text-navy animate-spin mx-auto" />
              <div>
                <p className="font-semibold text-navy">Analyzing Document...</p>
                <p className="text-sm text-gray-500">
                  Our AI is extracting information from your records
                </p>
              </div>
              <Progress value={uploadProgress} className="h-2 w-48 mx-auto" />
            </div>
          ) : (
            <>
              <div className="bg-navy/10 p-3 rounded-full mb-3">
                <Upload className="h-8 w-8 text-navy" />
              </div>
              <p className="font-semibold text-gray-800">
                {isDragOver ? "Drop your file here" : "Drag & drop your records here"}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                or{" "}
                <span className="text-navy font-medium underline">
                  click to browse
                </span>
              </p>
              <div className="flex flex-wrap gap-2 mt-3 justify-center">
                {[
                  { ext: "PDF", icon: FileText },
                  { ext: "TXT", icon: FileIcon },
                ].map(({ ext, icon: Icon }) => (
                  <Badge key={ext} variant="outline" className="text-xs">
                    <Icon className="h-3 w-3 mr-1" />
                    {ext}
                  </Badge>
                ))}
                <Badge variant="outline" className="text-xs text-gray-400">
                  Max {MAX_SIZE_MB}MB
                </Badge>
              </div>
            </>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 text-red-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Upload Error</p>
              <p>{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Extraction Result */}
        {lastResult && (
          <div className="p-4 rounded-xl bg-green-50 border border-green-200 space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span className="font-semibold text-green-800">
                Document Processed Successfully
              </span>
              <Badge
                className={`ml-auto ${
                  CONFIDENCE_COLORS[lastResult.confidence] || CONFIDENCE_COLORS.low
                }`}
              >
                {lastResult.confidence} confidence
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Document Type:</span>
                <p className="font-medium">
                  {DOC_TYPE_LABELS[lastResult.document_type] ||
                    lastResult.document_type}
                </p>
              </div>
              <div>
                <span className="text-gray-500">Pages Auto-Filled:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {lastResult.pages_affected.map((page) => (
                    <Badge key={page} variant="secondary" className="text-xs">
                      {page.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {lastResult.raw_findings && (
              <div className="text-sm">
                <span className="text-gray-500">Summary:</span>
                <p className="mt-1 text-gray-700">{lastResult.raw_findings}</p>
              </div>
            )}

            <p className="text-xs text-gray-500 italic">
              Review the auto-filled fields on each page. You can edit any
              field that was filled in.
            </p>
          </div>
        )}

        {/* Previously Uploaded Files */}
        {uploadedFiles.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Uploaded Documents ({uploadedFiles.length})
              </h4>
              <div className="space-y-2">
                {uploadedFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 p-2 rounded-lg bg-gray-50 text-sm"
                  >
                    <FileCheck className="h-4 w-4 text-green-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{file.filename}</p>
                      <p className="text-xs text-gray-500">
                        {DOC_TYPE_LABELS[file.document_type] || file.document_type}
                        {" · "}
                        {(file.size_bytes / 1024).toFixed(0)} KB
                      </p>
                    </div>
                    <Badge
                      className={`text-xs flex-shrink-0 ${
                        CONFIDENCE_COLORS[file.confidence] || CONFIDENCE_COLORS.low
                      }`}
                    >
                      {file.confidence}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Accepted document types */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 text-sm text-blue-800">
          <Shield className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium">Accepted Document Types</p>
            <p className="text-blue-600 mt-0.5">
              DD-214 · Service Treatment Records · VA Rating Decisions ·
              Medical Records · Nexus Letters · C&P Exam Reports · Buddy Statements
            </p>
            <p className="text-blue-500 mt-1 text-xs">
              All uploads are encrypted at rest (AES-256) and never shared with third parties.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

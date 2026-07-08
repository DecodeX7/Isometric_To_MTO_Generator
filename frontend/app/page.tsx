"use client";

import { useEffect, useMemo, useState } from "react";
import { DrawingPreview } from "@/components/DrawingPreview";
import { MetadataPanel } from "@/components/MetadataPanel";
import { MtoTable } from "@/components/MtoTable";
import { SummaryCards } from "@/components/SummaryCards";
import { UploadPanel } from "@/components/UploadPanel";
import { csvDownloadUrl, fetchJob, uploadDrawing } from "@/lib/api";
import type { JobResponse, JobStatus, MTOResult } from "@/lib/types";

function statusLabel(status?: JobStatus): string {
  if (!status) return "Waiting";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [result, setResult] = useState<MTOResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const activeStatus = job?.status ?? (file ? "queued" : undefined);
  const statusSteps = useMemo(
    () => [
      { label: "Upload", active: Boolean(file), done: Boolean(file) },
      { label: "Validate", active: Boolean(job), done: Boolean(job) },
      { label: "AI Extract", active: isProcessing || job?.status === "processing", done: Boolean(result) },
      { label: "Review & Export", active: Boolean(result), done: Boolean(result) }
    ],
    [file, job, isProcessing, result]
  );

  function handleFileSelected(selected: File) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setError(null);
    setJob(null);
    setResult(null);
    setProgress(0);
  }

  function reset() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
    setProgress(0);
    setJob(null);
    setResult(null);
    setError(null);
    setIsProcessing(false);
  }

  async function pollUntilDone(jobId: string) {
    for (let attempt = 0; attempt < 420; attempt += 1) {
      const current = await fetchJob(jobId);
      setJob(current);
      if (current.status === "completed") {
        setResult(current.result);
        return;
      }
      if (current.status === "failed") {
        throw new Error(current.error ?? "Processing failed.");
      }
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
    throw new Error(
      "Processing is taking longer than expected. Check the backend terminal or try a cleaner/cropped drawing."
    );
  }

  async function startProcessing() {
    if (!file) return;
    setIsProcessing(true);
    setError(null);
    setResult(null);
    setJob(null);
    setProgress(0);

    try {
      const upload = await uploadDrawing(file, setProgress);
      setProgress(100);
      const firstJob: JobResponse = {
        job_id: upload.job_id,
        status: upload.status,
        filename: file.name,
        result: null,
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setJob(firstJob);
      await pollUntilDone(upload.job_id);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Something went wrong while processing the drawing.";
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <main>
      <section className="heroShell">
        <div className="container heroGrid">
          <div>
            <h1>Isometric Drawing to Automated MTO Generator</h1>
            <p className="heroLead">
              Upload one piping isometric drawing and generate a validated Material Take-Off with metadata,
              pipe length, fittings, flanges, valves, gaskets, bolt sets, confidence and CSV export.
            </p>
            <div className="heroBadges">
              <span>Next.js</span>
              <span>FastAPI</span>
              <span>Gemini Vision</span>
              <span>Pydantic Validation</span>
            </div>
          </div>
          <aside className="heroPanel">
            <div className="heroPanelTop">
              <span className={`statusPill status-${activeStatus ?? "waiting"}`}>{statusLabel(activeStatus)}</span>
              <span className="miniText">Job-based extraction pipeline</span>
            </div>
            <div className="flowList">
              {statusSteps.map((step, index) => (
                <div className={`flowStep ${step.active ? "active" : ""} ${step.done ? "done" : ""}`} key={step.label}>
                  <span>{index + 1}</span>
                  <strong>{step.label}</strong>
                </div>
              ))}
            </div>
            <p className="heroPanelNote">
              Live Gemini mode uses optimized multi-view preprocessing. Without a key, the app still runs with a labelled mock fallback.
            </p>
          </aside>
        </div>
      </section>

      <div className="container appGrid">
        <div className="leftStack">
          <UploadPanel
            file={file}
            isProcessing={isProcessing}
            progress={progress}
            onFileSelected={handleFileSelected}
            onStart={startProcessing}
            onReset={reset}
          />
          <DrawingPreview previewUrl={previewUrl} fileType={file?.type ?? null} />
        </div>

        <section className="card resultCard">
          <div className="cardHeader resultHeader">
            <div>
              <h2 className="cardTitle">Extracted MTO</h2>
              <p className="cardSubtext">
                Status: <strong>{job?.status ?? "waiting for upload"}</strong>
                {job?.job_id && <span className="jobId">Job ID: {job.job_id}</span>}
              </p>
            </div>
            {result && job && (
              <a className="btn primary exportBtn" href={csvDownloadUrl(job.job_id)}>
                Export CSV
              </a>
            )}
          </div>

          {error && <div className="errorBox">{error}</div>}

          {isProcessing && !result && (
            <div className="liveProcessingBox">
              <div className="spinner" />
              <div>
                <strong>Live extraction is running</strong>
                <p>
                  Dense scanned PDFs can take several minutes. The backend is preprocessing the page into optimized views and asking Gemini for structured JSON.
                </p>
              </div>
            </div>
          )}

          {!result && !isProcessing && !error && (
            <div className="emptyState">
              <div className="emptyIcon">MTO</div>
              <h3>No extraction result yet</h3>
              <p>Upload a drawing and click <strong>Generate MTO</strong> to start the AI pipeline.</p>
            </div>
          )}

          {result && (
            <>
              {result.extraction_info.warnings.length > 0 && (
                <div className="warningBox">
                  <strong>Pipeline note:</strong> {result.extraction_info.warnings.join(" ")}
                </div>
              )}

              <div className="providerStrip">
                <div>
                  <span>Provider</span>
                  <strong>{result.extraction_info.provider}</strong>
                </div>
                <div>
                  <span>Mode</span>
                  <strong>{result.extraction_info.mode}</strong>
                </div>
                <div>
                  <span>Model</span>
                  <strong>{result.extraction_info.model}</strong>
                </div>
              </div>

              <SummaryCards summary={result.summary} />
              <MetadataPanel meta={result.drawing_meta} />
              <MtoTable items={result.items} />
            </>
          )}
        </section>
      </div>
    </main>
  );
}

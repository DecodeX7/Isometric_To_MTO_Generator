"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";

const MAX_SIZE_BYTES = 20 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg", "application/pdf"];

interface UploadPanelProps {
  file: File | null;
  isProcessing: boolean;
  progress: number;
  onFileSelected: (file: File) => void;
  onStart: () => void;
  onReset: () => void;
}

export function UploadPanel({
  file,
  isProcessing,
  progress,
  onFileSelected,
  onStart,
  onReset
}: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function validateAndSelect(candidate: File) {
    if (!ALLOWED_TYPES.includes(candidate.type)) {
      setLocalError("Please upload only a PNG, JPG/JPEG, or PDF isometric drawing.");
      return;
    }
    if (candidate.size > MAX_SIZE_BYTES) {
      setLocalError("File is larger than 20 MB. Please upload a smaller drawing.");
      return;
    }
    setLocalError(null);
    onFileSelected(candidate);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (selected) validateAndSelect(selected);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) validateAndSelect(dropped);
  }

  return (
    <section className="card">
      <div className="cardHeader">
        <h2 className="cardTitle">Upload isometric drawing</h2>
        <p className="cardSubtext">
          Upload one PNG, JPG, or PDF. The backend validates file type and size again before processing.
        </p>
      </div>

      <div
        className={`uploadBox ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div className="uploadIcon">ISO</div>
        <strong>{file ? file.name : "Drag and drop your drawing here"}</strong>
        <p className="cardSubtext">
          {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "or choose a file from your computer"}
        </p>

        <input
          ref={inputRef}
          className="fileInput"
          type="file"
          accept="image/png,image/jpeg,application/pdf"
          onChange={handleInputChange}
        />

        <div className="actions">
          <button className="btn secondary" type="button" onClick={() => inputRef.current?.click()} disabled={isProcessing}>
            Choose file
          </button>
          <button className="btn primary" type="button" onClick={onStart} disabled={!file || isProcessing}>
            {isProcessing ? "Processing..." : "Generate MTO"}
          </button>
          {file && (
            <button className="btn secondary" type="button" onClick={onReset} disabled={isProcessing}>
              Reset
            </button>
          )}
        </div>

        {isProcessing && (
          <div className="progressTrack" aria-label="Upload progress">
            <div className="progressBar" style={{ width: `${progress}%` }} />
          </div>
        )}
      </div>

      {localError && <div className="errorBox">{localError}</div>}
    </section>
  );
}

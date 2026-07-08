"use client";

interface DrawingPreviewProps {
  previewUrl: string | null;
  fileType: string | null;
}

export function DrawingPreview({ previewUrl, fileType }: DrawingPreviewProps) {
  return (
    <section className="card">
      <div className="cardHeader">
        <h2 className="cardTitle">Drawing preview</h2>
        <p className="cardSubtext">Preview is kept client-side. The backend receives the uploaded file for extraction.</p>
      </div>
      <div className="previewBox">
        {!previewUrl ? (
          <div className="emptyPreview">
            <strong>No drawing selected</strong>
            <p>Upload a sample isometric to preview it here.</p>
          </div>
        ) : fileType === "application/pdf" ? (
          <iframe src={previewUrl} title="Uploaded PDF drawing preview" />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={previewUrl} alt="Uploaded isometric drawing preview" />
        )}
      </div>
    </section>
  );
}

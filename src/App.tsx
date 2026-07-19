/**
 * App.tsx — Social Video Downloader
 * Dark-mode React UI wired to the Flask backend via src/api/client.ts
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  analyzeVideo,
  downloadVideo,
  ApiClientError,
  VideoInfo,
  VideoFormat,
} from "./api/client";

// ── tiny helpers ──────────────────────────────────────────────────────────────

function formatCount(n: number | null): string {
  if (n === null || n === undefined) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatBytes(b: number | null): string {
  if (!b) return "—";
  if (b >= 1_073_741_824) return `${(b / 1_073_741_824).toFixed(1)} GB`;
  if (b >= 1_048_576) return `${(b / 1_048_576).toFixed(1)} MB`;
  return `${(b / 1024).toFixed(0)} KB`;
}

function formatUploadDate(raw: string | null): string {
  if (!raw || raw.length !== 8) return "—";
  const y = raw.slice(0, 4);
  const m = raw.slice(4, 6);
  const d = raw.slice(6, 8);
  return `${y}-${m}-${d}`;
}

function platformColor(p: string): string {
  const l = p.toLowerCase();
  if (l.includes("facebook")) return "bg-blue-600";
  if (l.includes("instagram"))
    return "bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400";
  if (l.includes("tiktok")) return "bg-black border border-gray-600";
  return "bg-indigo-600";
}

function platformIcon(p: string): string {
  const l = p.toLowerCase();
  if (l.includes("facebook")) return "f";
  if (l.includes("instagram")) return "𝒊";
  if (l.includes("tiktok")) return "♪";
  return p.charAt(0).toUpperCase();
}

// ── sub-components ────────────────────────────────────────────────────────────

function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      className="animate-spin"
      style={{ width: size, height: size }}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
      <div
        className="bg-gradient-to-r from-indigo-500 to-green-400 h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

function StatChip({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center bg-gray-700/60 rounded-xl px-3 py-2.5 gap-0.5">
      <span className="text-lg">{icon}</span>
      <span className="text-white font-semibold text-sm">{value}</span>
      <span className="text-gray-400 text-xs">{label}</span>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

type Phase = "input" | "analyzing" | "result" | "downloading" | "done";

export default function App() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState<Phase>("input");
  const [error, setError] = useState("");
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<VideoFormat | null>(null);
  const [dlProgress, setDlProgress] = useState(0);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const downloadAnchorRef = useRef<HTMLAnchorElement>(null);

  // ── auto-trigger browser download once blob is ready ──────────────────────
  useEffect(() => {
    if (blobUrl && downloadAnchorRef.current && videoInfo) {
      const anchor = downloadAnchorRef.current;
      const safe = videoInfo.title
        .replace(/[^a-z0-9_\-. ]/gi, "_")
        .slice(0, 80);
      anchor.href = blobUrl;
      anchor.download = `${safe}.mp4`;
      anchor.click();
    }
  }, [blobUrl, videoInfo]);

  // ── cleanup blob URL on unmount ───────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  // ── handlers ──────────────────────────────────────────────────────────────

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text.trim());
      setError("");
    } catch {
      setError("Clipboard access denied — please paste the URL manually.");
    }
  }, []);

  const handleClear = useCallback(() => {
    setUrl("");
    setError("");
    textareaRef.current?.focus();
  }, []);

  const handleAnalyze = useCallback(async () => {
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Please enter a URL first.");
      return;
    }
    setError("");
    setPhase("analyzing");

    try {
      // ✅ analyzeVideo كترجع VideoInfo مباشرة
      const resp = await analyzeVideo(trimmed);
      setVideoInfo(resp);
      setSelectedFormat(resp.formats?.[0] ?? null);
      setPhase("result");
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : "Something went wrong — is the backend running?";
      setError(msg);
      setPhase("input");
    }
  }, [url]);

  const handleDownload = useCallback(async () => {
    if (!videoInfo) return;
    setPhase("downloading");
    setDlProgress(0);
    setBlobUrl(null);

    try {
      // ✅ downloadVideo كتقبل callback كـ argument عادي
      const objectUrl = await downloadVideo(
        videoInfo.webpage_url ?? url.trim(),
        selectedFormat?.format_id,
        (pct: number) => setDlProgress(pct)
      );
      setBlobUrl(objectUrl);
      setDlProgress(100);
      setPhase("done");
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : "Download failed — please try again.";
      setError(msg);
      setPhase("result");
    }
  }, [videoInfo, selectedFormat, url]);

  const handleReset = useCallback(() => {
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    setBlobUrl(null);
    setVideoInfo(null);
    setSelectedFormat(null);
    setUrl("");
    setError("");
    setDlProgress(0);
    setPhase("input");
  }, [blobUrl]);

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      <a ref={downloadAnchorRef} className="hidden" aria-hidden="true" />

      <header className="sticky top-0 z-20 bg-gray-900/90 backdrop-blur border-b border-gray-800 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-xl shadow-lg shadow-indigo-900/50">
              <svg
                className="h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-base font-bold leading-tight tracking-tight">
                Social Video Downloader
              </h1>
              <p className="text-xs text-gray-500 leading-none">
                Facebook · Instagram · TikTok
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center px-4 py-10">
        <div className="w-full max-w-2xl space-y-6">
          {/* ── Input Card ── */}
          <div className="bg-gray-900 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden">
            <div className="px-6 pt-6 pb-4 border-b border-gray-800">
              <h2 className="text-xl font-bold">Paste a Video Link</h2>
              <p className="text-gray-400 text-sm mt-0.5">
                Supports public posts, reels, and short videos.
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div className="relative">
                <textarea
                  ref={textareaRef}
                  rows={3}
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setError("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleAnalyze();
                    }
                  }}
                  placeholder="https://www.instagram.com/reel/…"
                  disabled={phase === "analyzing" || phase === "downloading"}
                  className="w-full px-4 py-3 pr-10 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none text-sm placeholder-gray-500 disabled:opacity-50 transition"
                />
                {url && phase === "input" && (
                  <button
                    onClick={handleClear}
                    className="absolute top-3 right-3 text-gray-500 hover:text-gray-300 transition"
                    aria-label="Clear URL"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>

              {error && (
                <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 text-red-300 text-sm rounded-xl px-4 py-3">
                  <svg
                    className="h-4 w-4 mt-0.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span>{error}</span>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handlePaste}
                  disabled={phase === "analyzing" || phase === "downloading"}
                  className="flex items-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-sm font-medium transition disabled:opacity-40"
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                  Paste
                </button>

                <button
                  onClick={handleAnalyze}
                  disabled={
                    phase === "analyzing" ||
                    phase === "downloading" ||
                    !url.trim()
                  }
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-semibold text-sm transition disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                >
                  {phase === "analyzing" ? (
                    <>
                      <Spinner size={16} /> Analyzing…
                    </>
                  ) : (
                    <>
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"
                        />
                      </svg>
                      Analyze Video
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* ── Result Card ── */}
          {videoInfo &&
            (phase === "result" ||
              phase === "downloading" ||
              phase === "done") && (
              <div className="bg-gray-900 rounded-2xl border border-gray-800 shadow-2xl overflow-hidden animate-fadeIn">
                {/* Thumbnail */}
                <div className="relative w-full aspect-video bg-gray-800">
                  {videoInfo.thumbnail ? (
                    <img
                      src={videoInfo.thumbnail}
                      alt="Video thumbnail"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-600">
                      <svg
                        className="h-16 w-16"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M15 10l4.55-2.27A1 1 0 0121 8.62v6.76a1 1 0 01-1.45.9L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
                        />
                      </svg>
                    </div>
                  )}

                  {/* Duration badge */}
                  <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-0.5 rounded-md font-mono">
                    {videoInfo.duration}
                  </div>

                  {/* Platform badge */}
                  <div
                    className={`absolute top-2 left-2 w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-lg ${platformColor(
                      videoInfo.platform ?? ""
                    )}`}
                  >
                    {platformIcon(videoInfo.platform ?? "")}
                  </div>

                  {/* Done overlay */}
                  {phase === "done" && (
                    <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-2">
                      <div className="bg-green-500 rounded-full p-3 shadow-xl">
                        <svg
                          className="h-8 w-8 text-white"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2.5}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      </div>
                      <p className="text-white font-semibold text-sm">
                        Download complete!
                      </p>
                    </div>
                  )}
                </div>

                <div className="p-6 space-y-5">
                  {/* Title & uploader */}
                  <div>
                    <h3 className="font-bold text-lg leading-snug line-clamp-2">
                      {videoInfo.title}
                    </h3>
                    <p className="text-gray-400 text-sm mt-1">
                      <span className="font-medium text-gray-300">
                        {videoInfo.uploader}
                      </span>
                      {videoInfo.upload_date && (
                        <>
                          {" "}
                          ·{" "}
                          <span>
                            {formatUploadDate(videoInfo.upload_date)}
                          </span>
                        </>
                      )}
                    </p>
                  </div>

                  {/* Stats */}
                  <div className="grid grid-cols-3 gap-3">
                    <StatChip
                      icon="👁️"
                      label="Views"
                      value={formatCount(videoInfo.view_count ?? null)}
                    />
                    <StatChip
                      icon="❤️"
                      label="Likes"
                      value={formatCount(videoInfo.like_count ?? null)}
                    />
                    <StatChip
                      icon="🎬"
                      label="Platform"
                      value={videoInfo.platform ?? "—"}
                    />
                  </div>

                  {/* Format selector */}
                  {videoInfo.formats && videoInfo.formats.length > 0 && (
                    <div>
                      <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                        Quality
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {videoInfo.formats.map((fmt) => (
                          <button
                            key={fmt.format_id}
                            onClick={() => setSelectedFormat(fmt)}
                            disabled={phase === "downloading"}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition disabled:opacity-40 ${
                              selectedFormat?.format_id === fmt.format_id
                                ? "bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-900/40"
                                : "bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500"
                            }`}
                          >
                            {/* ✅ resolution بدل label */}
                            {fmt.resolution ?? fmt.quality ?? fmt.format_id}
                            {fmt.filesize && (
                              <span className="ml-1.5 text-xs opacity-70">
                                {formatBytes(fmt.filesize)}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Progress bar */}
                  {phase === "downloading" && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-300 font-medium flex items-center gap-2">
                          <Spinner size={14} /> Downloading…
                        </span>
                        <span className="text-indigo-400 font-semibold tabular-nums">
                          {dlProgress}%
                        </span>
                      </div>
                      <ProgressBar value={dlProgress} />
                    </div>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-3 pt-1">
                    {phase !== "done" ? (
                      <button
                        onClick={handleDownload}
                        disabled={phase === "downloading"}
                        className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-green-600 hover:bg-green-500 rounded-xl font-bold text-base transition disabled:opacity-50 active:scale-[0.98] shadow-lg shadow-green-900/30"
                      >
                        {phase === "downloading" ? (
                          <>
                            <Spinner size={18} /> Downloading…
                          </>
                        ) : (
                          <>Download MP4</>
                        )}
                      </button>
                    ) : (
                      <button
                        onClick={handleDownload}
                        className="flex-1 flex items-center justify-center gap-2 py-3.5 bg-green-700 hover:bg-green-600 rounded-xl font-bold text-base transition active:scale-[0.98]"
                      >
                        Download Again
                      </button>
                    )}

                    <button
                      onClick={handleReset}
                      disabled={phase === "downloading"}
                      className="px-4 py-3.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl font-semibold text-sm transition disabled:opacity-40"
                    >
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M4 4v5h.582M20 20v-5h-.582M4.582 9A8 8 0 0119.418 15M19.418 15A8 8 0 014.582 9"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            )}
        </div>
      </main>
    </div>
  );
}
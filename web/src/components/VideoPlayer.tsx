"use client";

interface VideoPlayerProps {
  src: string;
  className?: string;
  width?: number;
  height?: number;
}

export function VideoPlayer({ src, className, width, height }: VideoPlayerProps) {
  return (
    <div className={["w-full", className].filter(Boolean).join(" ")}>
      <video
        src={src}
        controls
        preload="metadata"
        className="w-full rounded-xl bg-black"
        style={{ aspectRatio: width && height ? `${width}/${height}` : "16/9" }}
      >
        Your browser does not support the video element.
      </video>
      {width && height && (
        <p className="mt-1.5 text-right text-xs text-zinc-600">
          {width} &times; {height}
        </p>
      )}
    </div>
  );
}

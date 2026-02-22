import { AbsoluteFill, Sequence, Audio, Img, useVideoConfig, staticFile, OffthreadVideo, interpolate, useCurrentFrame, Loop } from "remotion";
import manifest from "./dragon-manifest.json";
// @ts-ignore
import titleSubtitles from "./title_subtitles.json";
// @ts-ignore
import bodySubtitles from "./body_subtitles.json";
import { Subtitle } from "./Subtitle";
import { SubtitleBackground } from "./SubtitleBackground";


export const DragonStockComposition = () => {
  const { fps } = useVideoConfig();

  const introDuration = manifest.intro.durationInSeconds * fps;
  const bodyDuration = manifest.body.durationInSeconds * fps;

  // Safe access to timeline
  const timeline = (manifest.body as any).timeline;

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* INTRO SEQUENCE */}
      <Sequence from={0} durationInFrames={Math.ceil(introDuration)}>
        <AbsoluteFill>
          {(manifest.intro as any).type === "video" ? (
            <OffthreadVideo
              src={staticFile((manifest.intro as any).visual_src)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              muted
            />
          ) : (
            <Img
              src={staticFile(manifest.intro.visual_src)}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          )}
        </AbsoluteFill>
        <Audio src={staticFile(manifest.intro.audio_src)} />

        {/* Title Subtitles */}
        {titleSubtitles.map((subtitle: any, index: number) => {
          // Provide a key and props
          return (
            <Sequence key={index} from={subtitle.startFrame} durationInFrames={subtitle.endFrame - subtitle.startFrame}>
              <Subtitle text={subtitle.text} durationInFrames={subtitle.endFrame - subtitle.startFrame} />
            </Sequence>
          );
        })}
      </Sequence>

      {/* BODY SEQUENCE */}
      <Sequence from={Math.ceil(introDuration)}>
        <Audio src={staticFile(manifest.body.audio_src)} />

        {/* Timeline Videos */}
        {timeline && timeline.length > 0 ? (
          <TimelineVideoSequence timeline={timeline} />
        ) : (
          <AbsoluteFill style={{ backgroundColor: "#222", justifyContent: "center", alignItems: "center" }}>
            <div style={{ color: "white", fontSize: 40 }}>No timeline or videos found.</div>
          </AbsoluteFill>
        )}

        {/* Fixed Background Layer */}
        <SubtitleBackground />

        {/* Body Subtitles */}
        {bodySubtitles.map((subtitle: any, index: number) => {
          return (
            <Sequence key={index} from={subtitle.startFrame} durationInFrames={subtitle.endFrame - subtitle.startFrame}>
              <Subtitle text={subtitle.text} durationInFrames={subtitle.endFrame - subtitle.startFrame} />
            </Sequence>
          );
        })}
      </Sequence>
    </AbsoluteFill>
  );
};

// Helper to play videos based on a strict timeline
const TimelineVideoSequence: React.FC<{ timeline: any[] }> = ({ timeline }) => {
  const fadeDuration = 15; // 0.5 second overlap for snappier transitions
  const fps = 30;

  return (
    <AbsoluteFill>
      {timeline.map((scene, index) => {
        const isFirst = index === 0;
        const extendedDuration = scene.durationInFrames + fadeDuration;

        // Dynamic Playback Rate Calculation
        const sourceDurationSeconds = scene.source_duration || 10;
        const sourceDurationFrames = Math.floor(sourceDurationSeconds * fps);

        // We need the video to fill `extendedDuration` frames.
        // If we play at 1.0x, it lasts `sourceDurationFrames`.
        // To make it last `extendedDuration`, we need rate = source / extended.
        // Example: Source=100, Needed=120. Rate = 100/120 = 0.83x (Slow down to fit)
        // Example: Source=200, Needed=100. Rate = 200/100 = 2.0x (Speed up? No, keep natural)

        // Default target rate is 0.8 (slow motion cinematic feel)
        let targetRate = 0.8;

        // Effective duration at 0.8x
        const effectiveDurationAtDefault = sourceDurationFrames / targetRate;

        if (effectiveDurationAtDefault < extendedDuration) {
          // Video is too short even at 0.8x.
          // Can we stretch it more? Max stretch to 0.5x
          const maxStretchRate = sourceDurationFrames / extendedDuration;
          if (maxStretchRate >= 0.5) {
            // Yes, stretch it to fit exactly
            targetRate = maxStretchRate;
          } else {
            // Too short even at 0.5x. Must loop.
            targetRate = 0.8; // Stick to default and let loop handle it
          }
        }

        return (
          <Sequence
            key={index}
            from={scene.startFrame}
            durationInFrames={extendedDuration}
            layout="none"
          >
            <FadingVideo
              src={staticFile(scene.video_src)}
              isFirst={isFirst}
              fadeDuration={fadeDuration}
              playbackRate={targetRate}
              sourceDurationFrames={sourceDurationFrames}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

// Helper component to handle opacity fade in

const FadingVideo: React.FC<{
  src: string,
  isFirst: boolean,
  fadeDuration: number,
  playbackRate: number,
  sourceDurationFrames: number
}> = ({ src, isFirst, fadeDuration, playbackRate, sourceDurationFrames }) => {
  const frame = useCurrentFrame();

  const opacity = isFirst
    ? 1
    : interpolate(frame, [0, fadeDuration], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity }}>
      <Loop durationInFrames={sourceDurationFrames}>
        <OffthreadVideo
          src={src}
          playbackRate={playbackRate}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </Loop>
    </AbsoluteFill>
  );
};

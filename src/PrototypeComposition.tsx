import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig, Video } from "remotion";
import React from "react";
import subtitles from "./subtitles.json";
import { Subtitle } from "./Subtitle";

export const PrototypeComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Auto-Zoom (Ken Burns): Start at 1.1x and slowly zoom to 1.25x
  const videoScale = interpolate(frame, [0, durationInFrames], [1.1, 1.25], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "white" }}>
      {/* Background Video */}
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <Video
          src={staticFile("assets/video.mp4")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${videoScale})`,
          }}
        />
      </AbsoluteFill>

      {/* Background Music (BGM) - Low Volume */}
      <Audio src={staticFile("assets/current_bgm.mp3")} volume={0.3} />

      {/* Voice Track - Full Volume */}
      <Audio src={staticFile("assets/juju_voice.mp3")} volume={1.0} />

      {/* Subtitles Layer - Rendered via Sequence for relative timing */}
      {subtitles.map((subtitle, index) => (
        <Sequence
          key={index}
          from={subtitle.startFrame}
          durationInFrames={subtitle.endFrame - subtitle.startFrame}
        >
          <Subtitle
            text={subtitle.text}
            durationInFrames={subtitle.endFrame - subtitle.startFrame}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};


import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig, Video, interpolate, useCurrentFrame } from "remotion";
import React from "react";
import clips from "./montage-manifest.json";
import { Subtitle } from "./Subtitle";
import subtitles from "./subtitles.json";

export const MontageComposition: React.FC = () => {
    const { fps, width, height } = useVideoConfig(); // useVideoConfig to get dynamic dimensions
    const frame = useCurrentFrame();

    const CLIP_DURATION = 60; // 2 seconds per clip

    // Logic for Subtitles (Same as Prototype)
    const currentSubtitle = subtitles.find(
        (s) => frame >= s.startFrame && frame < s.endFrame
    );

    return (
        <AbsoluteFill style={{ backgroundColor: "black" }}>
            {/* Background Music */}
            <Audio src={staticFile("assets/bgm.mp3")} volume={0.5} />

            {/* Montage Sequence */}
            {clips.map((clip, index) => {
                const startFrame = index * CLIP_DURATION;

                // Local animation for each clip (Zoom effect reset per clip)
                // We need to calculate a local frame for the zoom: global frame - startFrame
                // But doing it inside map is tricky if we want true "per sequence" isolation.
                // Remotion's <Sequence> handles time shifting!
                // Inside <Sequence>, useCurrentFrame() returns 0 at the start of the sequence.

                return (
                    <Sequence
                        key={index}
                        from={startFrame}
                        durationInFrames={CLIP_DURATION}
                    >
                        <MontageClip src={clip} />
                    </Sequence>
                );
            })}

            {/* Subtitles (Overlay on top of everything) */}
            {currentSubtitle && (
                <Subtitle text={currentSubtitle.text} />
            )}
        </AbsoluteFill>
    );
};

// Helper component to handle per-clip animation (Ken Burns)
const MontageClip: React.FC<{ src: string }> = ({ src }) => {
    const frame = useCurrentFrame();
    const { durationInFrames } = useVideoConfig(); // This will be CLIP_DURATION inside Sequence? verify.
    // Ideally pass explicit duration if needed, but Sequence usually isolates context.
    // However, useVideoConfig().durationInFrames usually returns the COMPOSITION duration, not Sequence duration?
    // Remotion docs: "The useVideoConfig hook returns the configuration of the composition." 
    // It does NOT update for Sequence.

    const ZOOM_DURATION = 60; // We know our clips are 60 frames

    const scale = interpolate(frame, [0, ZOOM_DURATION], [1.1, 1.25], {
        extrapolateRight: "clamp"
    });

    return (
        <AbsoluteFill style={{ overflow: "hidden" }}>
            <Video
                src={staticFile(src)}
                style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    transform: `scale(${scale})`
                }}
            />
        </AbsoluteFill>
    )
}

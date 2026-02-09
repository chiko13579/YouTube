import React from "react";
import { spring, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

type SubtitleProps = {
    text: string;
    durationInFrames: number;
};

export const Subtitle: React.FC<SubtitleProps> = ({ text, durationInFrames }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Split text into characters
    const characters = text.split("");

    // Dynamic Pacing Logic:
    // Calculate how many frames each character can take to fill the duration.
    // We want the text to finish appearing slightly before the end (e.g., 80% of duration).
    const activeDuration = durationInFrames * 0.8;
    const baseDelay = activeDuration / Math.max(characters.length, 1);

    // Clamp values to keep it looking good
    // Min 1 frame (30fps), Max 5 frames (0.16s)
    const delayPerChar = Math.min(Math.max(baseDelay, 1), 5);

    return (
        <div
            style={{
                position: "absolute",
                bottom: 80,
                width: "100%",
                textAlign: "center",
                display: "flex",
                justifyContent: "center",
                flexWrap: "wrap",
                gap: "4px",
            }}
        >
            {characters.map((char, i) => {
                // Stagger delay based on dynamic calculation
                const delay = i * delayPerChar;

                const scale = spring({
                    fps,
                    frame: frame - delay,
                    config: {
                        damping: 15,
                        stiffness: 200,
                    },
                });

                // Optional: Slight slide up
                const translateY = interpolate(
                    scale,
                    [0, 1],
                    [20, 0],
                    { extrapolateRight: "clamp" }
                );

                return (
                    <span
                        key={i}
                        style={{
                            display: "inline-block",
                            fontFamily: "Zen Maru Gothic, sans-serif",
                            fontSize: 80,
                            fontWeight: 900,
                            color: "#FFFFFF",
                            WebkitTextStroke: "12px #FF4081",
                            paintOrder: "stroke fill",
                            filter: "drop-shadow(6px 6px 0px rgba(0,0,0,0.2))",
                            transform: `scale(${scale}) translateY(${translateY}px)`,
                        }}
                    >
                        {char}
                    </span>
                );
            })}
        </div>
    );
};

import React from "react";

type SubtitleProps = {
    text: string;
    durationInFrames: number;
};

export const Subtitle: React.FC<SubtitleProps> = ({ text }) => {
    return (
        <div
            style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                width: "100%",
                height: "100%",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
            }}
        >
            <div
                style={{
                    // Background is now handled by SubtitleBackground.tsx
                    // We just need to align the text in the same spot.
                    width: "100%",
                    padding: "60px 0",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                }}
            >
                <span
                    style={{
                        fontFamily: '"Zen Maru Gothic", sans-serif',
                        fontSize: 80,
                        fontWeight: 900,
                        color: "#FFFFFF",
                        lineHeight: 1.2,
                        textAlign: "center",
                    }}
                >
                    {text}
                </span>
            </div>
        </div>
    );
};

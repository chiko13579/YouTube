import { AbsoluteFill } from "remotion";
import React from "react";

export const SubtitleBackground: React.FC = () => {
    return (
        <AbsoluteFill
            style={{
                justifyContent: "center",
                alignItems: "center",
            }}
        >
            <div
                style={{
                    width: "100%",
                    backgroundColor: "rgba(0, 0, 0, 0.35)", // 35% opacity
                    padding: "60px 0", // Consistent height/padding
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    // We can set a minHeight to ensure it looks like a band even if empty, 
                    // though usually it's just a visual backdrop.
                    // The text will overlay this exact area.
                }}
            >
                {/* Spacer to give it height if needed, or just let padding handle it? 
                    The user said "padding wider". 
                    Let's ensure it has height even without text by using a non-breaking space or min-height.
                */}
                <div style={{ minHeight: "100px", width: "100%" }}></div>
            </div>
        </AbsoluteFill>
    );
};

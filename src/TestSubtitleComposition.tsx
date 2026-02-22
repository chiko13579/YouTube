import { AbsoluteFill, Sequence, Video, staticFile } from "remotion";
import { Subtitle } from "./Subtitle";
import { SubtitleBackground } from "./SubtitleBackground";

export const TestSubtitleComposition = () => {
    return (
        <AbsoluteFill style={{ backgroundColor: "black" }}>
            <Sequence from={0} durationInFrames={150}>
                <Video
                    src={staticFile("assets/test_video.mp4")}
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    muted
                />
            </Sequence>

            {/* Fixed Background */}
            <Sequence from={0} durationInFrames={150}>
                <SubtitleBackground />
            </Sequence>

            <Sequence from={10} durationInFrames={40}>
                <Subtitle text="テスト字幕です" durationInFrames={40} />
            </Sequence>
            <Sequence from={60} durationInFrames={40}>
                <Subtitle text="背景が見やすいか確認" durationInFrames={40} />
            </Sequence>
            <Sequence from={110} durationInFrames={40}>
                <Subtitle text="スタイル変更完了" durationInFrames={40} />
            </Sequence>
        </AbsoluteFill>
    );
};

import { Composition } from "remotion";
import { DragonStockComposition } from "./DragonStockComposition";
import { TestSubtitleComposition } from "./TestSubtitleComposition";
import manifest from "./dragon-manifest.json";
import "./index.css";

export const RemotionRoot: React.FC = () => {
  const fps = 30;
  // Calculate total frames safely
  const introDuration = manifest.intro ? manifest.intro.durationInSeconds : 10;
  const bodyDuration = manifest.body ? manifest.body.durationInSeconds : 30;

  const durationInFrames = Math.ceil((introDuration + bodyDuration) * fps);

  return (
    <>
      <Composition
        id="DragonStock"
        component={DragonStockComposition}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1920}
        height={1080}
      />
      <Composition
        id="TestSubtitle"
        component={TestSubtitleComposition}
        durationInFrames={150}
        fps={fps}
        width={1920}
        height={1080}
      />
    </>
  );
};
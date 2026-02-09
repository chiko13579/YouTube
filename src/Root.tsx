import "./index.css";
import { Composition } from "remotion";
import { MyComposition } from "./Composition";
import { PrototypeComposition } from "./PrototypeComposition";
import { MontageComposition } from "./MontageComposition";
import { z } from "zod";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MyComp"
        component={MyComposition}
        durationInFrames={60}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="Prototype"
        component={PrototypeComposition}
        durationInFrames={209}
        fps={30}
        schema={z.object({
          mode: z.enum(["vertical", "horizontal"]),
        })}
        defaultProps={{
          mode: "vertical",
        }}
        calculateMetadata={({ props }) => {
          const isHorizontal = props.mode === "horizontal";
          return {
            width: isHorizontal ? 1920 : 1080,
            height: isHorizontal ? 1080 : 1920,
          };
        }}
      />
    </>
  );
};
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
import manifest from "./dragon-manifest.json";

// For dynamic duration, we might need to wrap Root logic.
// But mostly users edit Root.tsx. Let's check Root.tsx content first.
// Oh wait, Root.tsx is where the Composition is defined usually.
registerRoot(RemotionRoot);

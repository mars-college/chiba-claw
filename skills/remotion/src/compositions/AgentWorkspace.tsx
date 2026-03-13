import type {FC} from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type AgentWorkspaceProps = {
  title: string;
  subtitle: string;
  footer: string;
  accent: string;
  background: string;
};

export const AGENT_WORKSPACE_DURATION = 210;

export const AGENT_WORKSPACE_DEFAULT_PROPS: AgentWorkspaceProps = {
  title: "Agent Workspace",
  subtitle: "Edit this composition or add a new one for the user's request.",
  footer: "Render output lands in outputs/remotion/",
  accent: "#ff6f3c",
  background: "#120f1d",
};

const orbStyle = (size: number, top: string, left: string, accent: string, opacity: number) => ({
  position: "absolute" as const,
  width: size,
  height: size,
  top,
  left,
  borderRadius: "9999px",
  background: `radial-gradient(circle, ${accent}, transparent 70%)`,
  filter: "blur(12px)",
  opacity,
});

export const AgentWorkspace: FC<AgentWorkspaceProps> = ({
  title,
  subtitle,
  footer,
  accent,
  background,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const titleEntrance = spring({
    fps: 30,
    frame,
    config: {
      damping: 18,
      mass: 0.9,
      stiffness: 120,
    },
  });

  const subtitleEntrance = spring({
    fps: 30,
    frame: frame - 10,
    config: {
      damping: 16,
      mass: 0.95,
      stiffness: 110,
    },
  });

  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    easing: Easing.inOut(Easing.ease),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const sweep = interpolate(progress, [0, 1], [-220, 220]);
  const cardShift = interpolate(titleEntrance, [0, 1], [80, 0]);
  const footerOpacity = interpolate(frame, [110, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 20% 20%, ${accent}33 0%, transparent 30%), linear-gradient(135deg, ${background}, #05040a 72%)`,
        color: "#f7f2eb",
        fontFamily: "Avenir Next, Helvetica Neue, Helvetica, Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      <div style={orbStyle(320, "12%", `${18 + sweep * 0.04}%`, accent, 0.45)} />
      <div style={orbStyle(420, "56%", `${58 - sweep * 0.03}%`, "#6fd6ff", 0.32)} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          padding: "140px 140px 120px",
        }}
      >
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.16)",
            borderRadius: 44,
            padding: "56px 64px",
            backdropFilter: "blur(18px)",
            background: "rgba(7, 8, 15, 0.56)",
            transform: `translateY(${cardShift}px)`,
            boxShadow: "0 30px 80px rgba(0, 0, 0, 0.35)",
          }}
        >
          <div
            style={{
              fontSize: 24,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: accent,
              marginBottom: 20,
              opacity: 0.88,
            }}
          >
            Remotion Workspace
          </div>
          <div
            style={{
              fontSize: 110,
              lineHeight: 0.92,
              fontWeight: 800,
              letterSpacing: "-0.04em",
              marginBottom: 26,
              transform: `scale(${0.92 + titleEntrance * 0.08})`,
              transformOrigin: "left center",
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontSize: 34,
              lineHeight: 1.3,
              maxWidth: 1180,
              color: "rgba(247, 242, 235, 0.82)",
              opacity: subtitleEntrance,
            }}
          >
            {subtitle}
          </div>
          <div
            style={{
              marginTop: 40,
              height: 6,
              width: `${18 + progress * 62}%`,
              borderRadius: 999,
              background: `linear-gradient(90deg, ${accent}, #ffffff)`,
            }}
          />
        </div>
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          padding: "0 140px 74px",
        }}
      >
        <div
          style={{
            fontSize: 26,
            letterSpacing: "0.04em",
            color: "rgba(247, 242, 235, 0.68)",
            opacity: footerOpacity,
          }}
        >
          {footer}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

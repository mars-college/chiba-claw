import type {CSSProperties, FC} from "react";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const MARS_COLLEGE_AD_DURATION = 450;

const bgTextStyle: CSSProperties = {
  position: "absolute",
  fontSize: 220,
  fontWeight: 900,
  letterSpacing: "-0.08em",
  color: "rgba(255,255,255,0.045)",
  textTransform: "uppercase",
  whiteSpace: "nowrap",
};

const pill = (label: string, accent: string): JSX.Element => (
  <div
    key={label}
    style={{
      padding: "14px 24px",
      borderRadius: 999,
      border: `1px solid ${accent}55`,
      background: "rgba(255,255,255,0.06)",
      color: "#f7efe5",
      fontSize: 28,
      letterSpacing: "0.04em",
      textTransform: "uppercase",
    }}
  >
    {label}
  </div>
);

export const MarsCollegeAd: FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const entrance = spring({
    fps,
    frame,
    config: {damping: 18, stiffness: 120, mass: 0.9},
  });

  const drift = interpolate(frame, [0, MARS_COLLEGE_AD_DURATION], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const ctaOpacity = interpolate(frame, [300, 360], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleY = interpolate(entrance, [0, 1], [70, 0]);
  const titleScale = interpolate(entrance, [0, 1], [0.92, 1]);
  const lineWidth = interpolate(frame, [20, 180], [0, 860], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(circle at 20% 20%, rgba(255,130,92,0.24), transparent 28%), radial-gradient(circle at 78% 30%, rgba(74,189,255,0.22), transparent 30%), linear-gradient(135deg, #140d10 0%, #25151b 44%, #05070d 100%)",
        color: "#fff7ef",
        fontFamily: "Avenir Next, Helvetica Neue, Helvetica, Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          ...bgTextStyle,
          top: 90,
          left: interpolate(drift, [0, 1], [-140, -40]),
        }}
      >
        SOLARPUNK • OFF-GRID • DESERT • AI
      </div>
      <div
        style={{
          ...bgTextStyle,
          bottom: 110,
          right: interpolate(drift, [0, 1], [-80, 40]),
        }}
      >
        POP-UP VILLAGE • FUTURE POSITIVE
      </div>

      <AbsoluteFill style={{padding: "100px 110px"}}>
        <div
          style={{
            width: 240,
            height: 10,
            borderRadius: 999,
            background: "linear-gradient(90deg, #ff8b5e, #ffe2cf)",
            marginBottom: 28,
          }}
        />
        <div
          style={{
            fontSize: 28,
            letterSpacing: "0.26em",
            textTransform: "uppercase",
            color: "#ffaf87",
            marginBottom: 24,
            opacity: 0.95,
          }}
        >
          Mars Lore Spotlight
        </div>

        <Sequence from={0} durationInFrames={210}>
          <div
            style={{
              transform: `translateY(${titleY}px) scale(${titleScale})`,
              transformOrigin: "left top",
            }}
          >
            <div
              style={{
                fontSize: 142,
                lineHeight: 0.9,
                fontWeight: 900,
                letterSpacing: "-0.07em",
                maxWidth: 1200,
              }}
            >
              Mars College
            </div>
            <div
              style={{
                marginTop: 24,
                height: 8,
                width: lineWidth,
                borderRadius: 999,
                background: "linear-gradient(90deg, #ff8b5e, #4abdff)",
              }}
            />
            <div
              style={{
                marginTop: 36,
                maxWidth: 1220,
                fontSize: 46,
                lineHeight: 1.18,
                color: "rgba(255,247,239,0.88)",
              }}
            >
              A three-month high-tech, off-grid, solarpunk pop-up village in the desert outside Bombay Beach.
            </div>
          </div>
        </Sequence>

        <Sequence from={150} durationInFrames={180}>
          <div
            style={{
              marginTop: 340,
              display: "flex",
              gap: 18,
              flexWrap: "wrap",
            }}
          >
            {[
              "Founded as BRAHMAN in 2020",
              "Renamed Mars College in 2021",
              "Built + packed away each year",
              "Leave no trace",
            ].map((label) => pill(label, "#4abdff"))}
          </div>
        </Sequence>

        <Sequence from={255} durationInFrames={150}>
          <div
            style={{
              position: "absolute",
              left: 110,
              right: 110,
              bottom: 130,
              padding: "38px 42px",
              borderRadius: 40,
              background: "rgba(7, 10, 18, 0.56)",
              border: "1px solid rgba(255,255,255,0.12)",
              boxShadow: "0 30px 80px rgba(0,0,0,0.35)",
              backdropFilter: "blur(18px)",
              opacity: ctaOpacity,
            }}
          >
            <div
              style={{
                fontSize: 68,
                fontWeight: 800,
                letterSpacing: "-0.04em",
                marginBottom: 18,
              }}
            >
              Build the future. Then pack it out.
            </div>
            <div
              style={{
                fontSize: 34,
                lineHeight: 1.3,
                color: "rgba(255,247,239,0.84)",
                maxWidth: 1200,
              }}
            >
              Mars College grows by 10–20 full-time Martians each year, decentralizes into camps, and returns season after season.
            </div>
          </div>
        </Sequence>

        <div
          style={{
            position: "absolute",
            right: 110,
            top: 104,
            fontSize: 26,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "rgba(255,247,239,0.7)",
          }}
        >
          Chiba // motion ad concept
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

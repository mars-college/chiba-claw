import type {FC} from "react";
import {Composition} from "remotion";
import {
  AGENT_WORKSPACE_DEFAULT_PROPS,
  AGENT_WORKSPACE_DURATION,
  AgentWorkspace,
} from "./compositions/AgentWorkspace";
import {MARS_COLLEGE_AD_DURATION, MarsCollegeAd} from "./compositions/MarsCollegeAd";

export const RemotionRoot: FC = () => {
  return (
    <>
      <Composition
        id="AgentWorkspace"
        component={AgentWorkspace}
        durationInFrames={AGENT_WORKSPACE_DURATION}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={AGENT_WORKSPACE_DEFAULT_PROPS}
      />
      <Composition
        id="MarsCollegeAd"
        component={MarsCollegeAd}
        durationInFrames={MARS_COLLEGE_AD_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

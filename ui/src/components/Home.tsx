import bbcw from "../assets/bbcw.jpg";
import finalFour from "../assets/final_four.jpg";
import {
  Dropdown,
  PrimaryButton,
  Stack,
  StackItem,
  Text,
} from "@fluentui/react";
import { useNavigate } from "react-router-dom";
import { Top25 } from "./Top25";
import { useState } from "react";

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [isWomens, setIsWomens] = useState(false);

  return (
    <Stack
      horizontalAlign="center"
      tokens={{ childrenGap: 10 }}
      styles={{ root: { padding: "0px 20px", minWidth: 500 } }}
    >
      <Text>
        <h1>Get started with MLMB</h1>
      </Text>
      <Text
        styles={{
          root: { textAlign: "center", maxWidth: 1200, margin: "0px 40px" },
        }}
      >
        Are you interested in leveraging machine learning to forecast game and
        tournament results? If that’s the case, you’ve landed in the perfect
        spot. Here, you can delve into team performance analysis, assess their
        winning probabilities across different scenarios, and gain insights into
        their strengths and weaknesses. Whether they’re playing at home, away,
        or on a neutral field, discover the impactful role of machine learning
        on men’s basketball.
      </Text>
      <Stack
        horizontal
        wrap
        horizontalAlign="center"
        verticalAlign="start"
        tokens={{ childrenGap: 100 }}
        styles={{ root: { paddingTop: 50 } }}
      >
        <Stack
          styles={{ root: { maxWidth: 400, minWidth: 400 } }}
          tokens={{ childrenGap: 10 }}
        >
          <div style={{ height: 400, margin: "auto" }}>
            <img src={finalFour} style={{ height: "100%" }} />
          </div>
          <Text>
            <h3 style={{ marginBlockStart: 0, marginBlockEnd: 0 }}>
              Make a prediction
            </h3>
          </Text>
          <Text>
            Get started with your first prediction! Choose your teams, the type
            of game site, and model here.
          </Text>
          <Stack horizontal>
            <PrimaryButton
              text="Make a prediction"
              onClick={() => navigate("/predict")}
            />
          </Stack>
        </Stack>
        <Stack
          styles={{ root: { maxWidth: 400, minWidth: 400 } }}
          tokens={{ childrenGap: 10 }}
        >
          <div style={{ height: 400, margin: "auto" }}>
            <img src={bbcw} style={{ height: "100%" }} />
          </div>
          <Text>
            <h3 style={{ marginBlockStart: 0, marginBlockEnd: 0 }}>
              From Idea to Reality
            </h3>
          </Text>
          <Text>
            In March 2021, MLMB sprouted as a one-week side project within the
            cozy confines of a college apartment. Born at UConn, renowned as the
            basketball capital of the world, this initiative emerged when a
            computer science and engineering student fused his machine learning
            knowledge with an unwavering passion for college basketball.
          </Text>
        </Stack>
        <Stack
          styles={{ root: { maxWidth: 400, minWidth: 400 } }}
          tokens={{ childrenGap: 10 }}
        >
          <div style={{ height: 400, margin: "auto" }}>
            <Stack
              verticalAlign="start"
              styles={{
                root: {
                  height: 400,
                  width: 400,
                },
              }}
            >
              <Top25 isWomens={isWomens} />
            </Stack>
          </div>
          <Stack horizontal>
            <StackItem grow>
              <Text>
                <h3 style={{ marginBlockStart: 0, marginBlockEnd: 0 }}>
                  MLMB Top 25
                </h3>
              </Text>
            </StackItem>
            <StackItem>
              <Dropdown
                selectedKey={isWomens ? "women" : "men"}
                options={[
                  { key: "men", text: "Men's top 25" },
                  { key: "women", text: "Women's top 25" },
                ]}
                onChange={(_ev, opt) => setIsWomens(opt?.key === "women")}
              />
            </StackItem>
          </Stack>
          <Text>
            We analyze the top 25 teams as per the AP poll and forecast
            potential matchups for every team combination, considering whether
            the game is played at home, away, or on a neutral field. Each team
            is assigned a score based on the number of predicted wins, with
            additional weight given to the game location. Finally, we rank the
            teams in descending order of this calculated score.
          </Text>
        </Stack>
      </Stack>
    </Stack>
  );
};

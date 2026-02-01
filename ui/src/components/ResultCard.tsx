import { Stack, StackItem, Text, getTheme } from "@fluentui/react";
import { teams as TEAMS } from "../assets/teams";
import no_logo from "../assets/no-logo.svg";
import { PredictionResponse } from "../services/types";

export interface IResultCard extends PredictionResponse {}

export const ResultCard: React.FC<IResultCard> = ({
  model,
  neutral,
  home_team,
  away_team,
  home_last_played,
  away_last_played,
  home_win_probability,
  sport,
}) => {
  const theme = getTheme();
  const isWomens = sport === "ncaaw_basketball";

  const teams = TEAMS.filter((team) =>
    isWomens ? !!team.isWomenTeam : !!team.isMenTeam,
  );
  const homeMetadata = teams.find((team) => team["SR key"] === home_team);
  const awayMetadata = teams.find((team) => team["SR key"] === away_team);

  return (
    <Stack
      tokens={{ childrenGap: 10 }}
      styles={{
        root: {
          width: 650,
          border: "1px solid #ddd",
          boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
          padding: 10,
        },
      }}
    >
      <Stack horizontal>
        <StackItem grow>{model}</StackItem>
        <StackItem>{`NCAA ${isWomens ? "W" : ""}BK`}</StackItem>
      </Stack>
      <Stack horizontal>
        <Stack
          grow
          horizontalAlign="center"
          styles={{
            root: {
              padding: 10,
              backgroundColor: awayMetadata?.["background-color"],
            },
          }}
        >
          <img
            style={{
              height: 60,
              backgroundColor:
                !awayMetadata?.["NCAA key"] ||
                !awayMetadata?.["background-color"]
                  ? theme.palette.neutralTertiary
                  : undefined,
            }}
            src={
              !!awayMetadata?.["NCAA key"] &&
              !!awayMetadata?.["background-color"]
                ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${awayMetadata?.["NCAA key"]}.svg`
                : no_logo
            }
          />
        </Stack>
        <Stack
          grow
          horizontalAlign="center"
          styles={{
            root: {
              padding: 10,
              backgroundColor: homeMetadata?.["background-color"],
            },
          }}
        >
          <img
            style={{
              height: 60,
              backgroundColor:
                !homeMetadata?.["NCAA key"] ||
                !homeMetadata?.["background-color"]
                  ? theme.palette.neutralTertiary
                  : undefined,
            }}
            src={
              !!homeMetadata?.["NCAA key"] &&
              !!homeMetadata?.["background-color"]
                ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${homeMetadata?.["NCAA key"]}.svg`
                : no_logo
            }
          />
        </Stack>
      </Stack>
      <Stack horizontal>
        <Stack grow styles={{ root: { flexBasis: "100%" } }}>
          <Text variant="large">
            {awayMetadata?.["NCAA Name"] ?? awayMetadata?.School}
          </Text>
          <Text variant="medium">{`(${((1 - home_win_probability) * 100).toFixed(2)}%)${
            neutral ? "" : " Away"
          }`}</Text>
          <Text variant="xSmall">{away_last_played}</Text>
        </Stack>
        <Stack
          grow
          verticalAlign="center"
          horizontalAlign="center"
          styles={{ root: { flexBasis: "100%" } }}
        >
          <Text
            variant="xxLargePlus"
            styles={{ root: { letterSpacing: "10px" } }}
          >
            {`${home_win_probability >= 0.5 ? "L" : "W"} - ${home_win_probability >= 0.5 ? "W" : "L"}`}
          </Text>
        </Stack>
        <Stack
          grow
          horizontalAlign="end"
          styles={{ root: { flexBasis: "100%" } }}
        >
          <Text variant="large">
            {homeMetadata?.["NCAA Name"] ?? homeMetadata?.School}
          </Text>
          <Text variant="medium">{`${neutral ? "" : "Home "}(${(
            home_win_probability * 100
          ).toFixed(2)}%)`}</Text>
          <Text variant="xSmall">{home_last_played}</Text>
        </Stack>
      </Stack>
    </Stack>
  );
};

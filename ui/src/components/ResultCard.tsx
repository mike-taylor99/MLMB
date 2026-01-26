import { Stack, StackItem, Text, getTheme } from "@fluentui/react";
import { teams as TEAMS } from "../assets/teams";
import no_logo from "../assets/no-logo.svg";
import { PredictionResponse } from "../services/types";

export interface IResultCard extends PredictionResponse {}

export const ResultCard: React.FC<IResultCard> = ({
  model,
  neutral,
  team1,
  team2,
  team1_last_played,
  team2_last_played,
  team1_probability,
  team2_probability,
  winner,
  gender,
}) => {
  const theme = getTheme();
  const isWomens = gender === "women";

  const teams = TEAMS.filter((team) =>
    isWomens ? !!team.isWomenTeam : !!team.isMenTeam,
  );
  const team1Metadata = teams.find((team) => team["SR key"] === team1);
  const team2Metadata = teams.find((team) => team["SR key"] === team2);

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
              backgroundColor: team1Metadata?.["background-color"],
            },
          }}
        >
          <img
            style={{
              height: 60,
              backgroundColor:
                !team1Metadata?.["NCAA key"] ||
                !team1Metadata?.["background-color"]
                  ? theme.palette.neutralTertiary
                  : undefined,
            }}
            src={
              !!team1Metadata?.["NCAA key"] &&
              !!team1Metadata?.["background-color"]
                ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${team1Metadata?.["NCAA key"]}.svg`
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
              backgroundColor: team2Metadata?.["background-color"],
            },
          }}
        >
          <img
            style={{
              height: 60,
              backgroundColor:
                !team2Metadata?.["NCAA key"] ||
                !team2Metadata?.["background-color"]
                  ? theme.palette.neutralTertiary
                  : undefined,
            }}
            src={
              !!team2Metadata?.["NCAA key"] &&
              !!team2Metadata?.["background-color"]
                ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${team2Metadata?.["NCAA key"]}.svg`
                : no_logo
            }
          />
        </Stack>
      </Stack>
      <Stack horizontal>
        <Stack grow styles={{ root: { flexBasis: "100%" } }}>
          <Text variant="large">
            {team1Metadata?.["NCAA Name"] ?? team1Metadata?.School}
          </Text>
          <Text variant="medium">{`(${(team1_probability * 100).toFixed(2)}%)${
            neutral ? "" : " Away"
          }`}</Text>
          <Text variant="xSmall">{team1_last_played}</Text>
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
            {`${winner === "team2" ? "L" : "W"} - ${winner === "team2" ? "W" : "L"}`}
          </Text>
        </Stack>
        <Stack
          grow
          horizontalAlign="end"
          styles={{ root: { flexBasis: "100%" } }}
        >
          <Text variant="large">
            {team2Metadata?.["NCAA Name"] ?? team2Metadata?.School}
          </Text>
          <Text variant="medium">{`${neutral ? "" : "Home "}(${(
            team2_probability * 100
          ).toFixed(2)}%)`}</Text>
          <Text variant="xSmall">{team2_last_played}</Text>
        </Stack>
      </Stack>
    </Stack>
  );
};

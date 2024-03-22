import { Stack, StackItem, Text, getTheme } from "@fluentui/react";
import { teams as mensTeams } from "../assets/mens_teams";
import { teams as womensTeams } from "../assets/womens_teams";
import no_logo from "../assets/no-logo.svg";
import { MatchupOutput } from "../services/types";

export interface IResultCard extends MatchupOutput {}

export const ResultCard: React.FC<IResultCard> = ({
  model,
  isNeutral,
  team1,
  team2,
  team1LastPlayed,
  team2LastPlayed,
  predict,
  predictProba,
  isWomens,
}) => {
  const theme = getTheme();

  const teams = isWomens ? womensTeams : mensTeams;
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
          <Text variant="medium">{`(${(predictProba[0] * 100).toFixed(2)}%)${
            isNeutral ? "" : " Away"
          }`}</Text>
          <Text variant="xSmall">{team1LastPlayed}</Text>
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
            {`${predict[0] == 1 ? "L" : "W"} - ${predict[0] == 1 ? "W" : "L"}`}
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
          <Text variant="medium">{`${isNeutral ? "" : "Home "}(${(
            predictProba[1] * 100
          ).toFixed(2)}%)`}</Text>
          <Text variant="xSmall">{team2LastPlayed}</Text>
        </Stack>
      </Stack>
    </Stack>
  );
};

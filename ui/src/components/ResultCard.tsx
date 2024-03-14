import { Stack, StackItem, Text, getTheme } from "@fluentui/react";
import { teams } from "../assets/teams";
import no_logo from "../assets/no-logo.svg";

export interface IResultCard {
  model: string;
  isNeutral: boolean;
  team1: string;
  team2: string;
}

export const ResultCard: React.FC<IResultCard> = ({
  model,
  isNeutral,
  team1,
  team2,
}) => {
  const theme = getTheme();

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
        <StackItem>NCAA BK</StackItem>
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
          <Text variant="medium">{`(80%)${isNeutral ? "" : " Away"}`}</Text>
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
            W - L
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
          <Text variant="medium">{`${isNeutral ? "" : "Home "}(20%)`}</Text>
        </Stack>
      </Stack>
    </Stack>
  );
};

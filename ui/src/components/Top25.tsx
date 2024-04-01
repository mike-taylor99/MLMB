import {
  IColumn,
  SelectionMode,
  ShimmeredDetailsList,
  Stack,
  IDetailsListStyles,
  mergeStyleSets,
  DetailsList,
} from "@fluentui/react";
import { useConst } from "@fluentui/react-hooks";
import { useGetTop25Query } from "../services/mlmb";
import { teams as TEAMS } from "../assets/teams";
import { ITeam } from "../common/models";
import no_logo from "../assets/no-logo.svg";

const gridStyles: Partial<IDetailsListStyles> = {
  root: {
    overflowX: "hidden",
    selectors: {
      "& [role=grid]": {
        display: "flex",
        flexDirection: "column",
        alignItems: "start",
        height: 400,
      },
    },
  },
  headerWrapper: {
    flex: "0 0 auto",
    selectors: {
      "& [role=row]": {
        paddingTop: 0,
      },
    },
  },
  contentWrapper: {
    flex: "1 1 auto",
    overflow: "hidden",
    maxWidth: "100%",
  },
};

const classNames = mergeStyleSets({
  header: {
    margin: 0,
  },
  focusZone: {
    height: "100%",
    overflowY: "auto",
    overflowX: "hidden",
    maxWidth: "100%",
  },
  selectionZone: {
    height: "100%",
    overflow: "hidden",
  },
});

const focusZoneProps = {
  className: classNames.focusZone,
  "data-is-scrollable": "true",
} as React.HTMLAttributes<HTMLElement>;

export const Top25: React.FC = () => {
  const { data, error, isLoading } = useGetTop25Query();
  const filteredTeams = TEAMS.filter((team) => !!team.isMenTeam).filter(
    (team) => Object.keys(data || {}).includes(team["SR key"])
  );
  const items = filteredTeams
    .map((team) => ({
      ...team,
      score: data?.[team["SR key"]],
    }))
    .sort((a, b) => (b?.score || 0) - (a?.score || 0));

  const columns: IColumn[] = useConst(() => {
    return [
      {
        key: "logo",
        name: "",
        fieldName: "logo",
        minWidth: 40,
        maxWidth: 40,
        isResizable: false,
        onRenderField: (props) => {
          if (!props) return;
          const {
            item,
            column: { currentWidth },
          } = props;
          return (
            <Stack
              verticalAlign="center"
              horizontalAlign="center"
              style={{
                backgroundColor:
                  ((item as ITeam)["background-color"] as string) ?? undefined,
                width: (currentWidth ?? 0) + 20,
                height: 42,
              }}
            >
              <img
                style={{ height: 30 }}
                src={
                  !!(item as ITeam)["NCAA key"] &&
                  !!(item as ITeam)["background-color"]
                    ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${
                        (item as ITeam)["NCAA key"]
                      }.svg`
                    : no_logo
                }
              />
            </Stack>
          );
        },
      },
      {
        key: "column1",
        name: "Name",
        fieldName: "NCAA School",
        minWidth: 40,
        maxWidth: 200,
        isResizable: false,
      },
      {
        key: "score",
        name: "Score",
        fieldName: "score",
        minWidth: 40,
        maxWidth: 40,
        isResizable: false,
      },
    ] as IColumn[];
  });

  return (
    <div>
      {isLoading || error ? (
        <ShimmeredDetailsList
          enableShimmer
          items={[]}
          columns={columns}
          shimmerLines={8}
          selectionMode={SelectionMode.none}
        />
      ) : (
        <DetailsList
          setKey="items"
          items={items || []}
          columns={columns}
          selectionMode={SelectionMode.none}
          ariaLabelForGrid="Item details"
          styles={gridStyles}
          focusZoneProps={focusZoneProps}
          selectionZoneProps={{
            className: classNames.selectionZone,
          }}
        />
      )}
    </div>
  );
};

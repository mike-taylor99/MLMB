import {
  IColumn,
  SelectionMode,
  Stack,
  IDetailsListStyles,
  mergeStyleSets,
  DetailsList,
  DetailsListLayoutMode,
  ConstrainMode,
  CommandBar,
  SearchBox,
  Dropdown,
  getTheme,
} from "@fluentui/react";
import { useConst } from "@fluentui/react-hooks";
import { teams as TEAMS } from "../assets/teams";
import { ITeam } from "../common/models";
import { useWindowDimensions } from "../common/hooks";
import { useState } from "react";
import no_logo from "../assets/no-logo.svg";

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

const isSearchTextIncluded = (team: ITeam, searchText: string) => {
  for (const key in team) {
    if (team.hasOwnProperty(key)) {
      const value = String(team[key as keyof ITeam]).toLowerCase();
      if (value.includes(searchText.toLowerCase())) {
        return true;
      }
    }
  }
  return false;
};

export interface ITeamListProps {}

export const TeamList: React.FC<ITeamListProps> = () => {
  const theme = getTheme();
  const { height } = useWindowDimensions();
  const [searchInput, setSearchInput] = useState("");
  const [isWomens, setIsWomens] = useState(false);

  const teams = TEAMS.filter((team) =>
    isWomens ? !!team.isWomenTeam : !!team.isMenTeam
  );
  const items: ITeam[] = teams
    .map((team) => ({ ...team, key: team["SR key"] }))
    .filter((team) => !searchInput || isSearchTextIncluded(team, searchInput));

  const gridStyles: Partial<IDetailsListStyles> = {
    root: {
      overflowX: "hidden",
      selectors: {
        "& [role=grid]": {
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
          height: `${height - 88 - 20}px`,
        },
      },
    },
    headerWrapper: {
      flex: "0 0 auto",
    },
    contentWrapper: {
      flex: "1 1 auto",
      overflow: "hidden",
      maxWidth: "100%",
    },
  };

  const columns: IColumn[] = useConst(() => {
    return [
      {
        key: "logo",
        name: "",
        fieldName: "NCAA key",
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
              {
                <img
                  style={{
                    height: 30,
                    backgroundColor:
                      !(item as ITeam)["NCAA key"] ||
                      !(item as ITeam)["background-color"]
                        ? theme.palette.neutralTertiary
                        : undefined,
                  }}
                  src={
                    !!(item as ITeam)["NCAA key"] &&
                    !!(item as ITeam)["background-color"]
                      ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${
                          (item as ITeam)["NCAA key"]
                        }.svg`
                      : no_logo
                  }
                />
              }
            </Stack>
          );
        },
      },
      {
        key: "name",
        name: "Name",
        fieldName: "NCAA Name",
        minWidth: 300,
        isResizable: false,
      },
      {
        key: "school",
        name: "School",
        fieldName: "NCAA School",
        minWidth: 200,
        isResizable: false,
      },
      {
        key: "location",
        name: "City, State",
        fieldName: "City, State",
        minWidth: 200,
        isResizable: false,
      },
    ] as IColumn[];
  });

  const onRenderColumn = (
    item?: ITeam,
    _index?: number,
    column?: IColumn
  ): React.ReactNode => {
    const value =
      item && column && column.fieldName
        ? item[column.fieldName as keyof ITeam] || ""
        : "";

    if (column?.key === "school") return !!value ? value : item?.School;
    if (column?.key === "name") return !!value ? value : "--";
    return value;
  };

  return (
    <Stack horizontalAlign="center" styles={{ root: { padding: "0px 20px" } }}>
      <Stack horizontalAlign="start" styles={{ root: { maxWidth: 835 } }}>
        <CommandBar
          items={[
            {
              key: "search",
              onRender: () => (
                <Stack verticalAlign="center">
                  <SearchBox
                    styles={{ root: { minWidth: 735 } }}
                    onChange={(_ev, newValue) => setSearchInput(newValue || "")}
                  />
                </Stack>
              ),
            },
          ]}
          farItems={[
            {
              key: "teams",
              onRender: () => (
                <Stack verticalAlign="center">
                  <Dropdown
                    selectedKey={isWomens ? "women" : "men"}
                    options={[
                      { key: "men", text: "Men" },
                      { key: "women", text: "Women" },
                    ]}
                    styles={{ root: { minWidth: 100 } }}
                    onChange={(_ev, option) =>
                      setIsWomens(option?.key === "women")
                    }
                  />
                </Stack>
              ),
            },
          ]}
          styles={{ root: { padding: 0 } }}
        />
        <DetailsList
          setKey={`${isWomens}`}
          items={items || []}
          columns={columns}
          selectionMode={SelectionMode.none}
          constrainMode={ConstrainMode.unconstrained}
          layoutMode={DetailsListLayoutMode.fixedColumns}
          ariaLabelForGrid="Item details"
          styles={gridStyles}
          focusZoneProps={focusZoneProps}
          selectionZoneProps={{
            className: classNames.selectionZone,
          }}
          onRenderItemColumn={onRenderColumn}
          onRenderDetailsHeader={(props, defaultRender) => {
            if (!props || !defaultRender) return null;
            return defaultRender({
              ...props,
              styles: { root: { paddingTop: 0 } },
            });
          }}
        />
      </Stack>
    </Stack>
  );
};

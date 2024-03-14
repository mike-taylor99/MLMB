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
  getTheme,
  IComboBoxOption,
  Selection,
  CheckboxVisibility,
} from "@fluentui/react";
import { useConst, useForceUpdate } from "@fluentui/react-hooks";
import { teams } from "../assets/teams";
import { IMatchupFormInput, ITeam } from "../common/models";
import { useWindowDimensions } from "../common/hooks";
import no_logo from "../assets/no-logo.svg";
import { Dropdown } from "./formik/Dropdown";
import { ComboBox } from "./formik/ComboBox";
import { useFormikContext } from "formik";
import { Toggle } from "./formik/Toggle";
import { EMPTY_FORM_MATCHUP } from "../common/constants";

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

export const PredictionForm: React.FC = () => {
  const theme = getTheme();
  const { height } = useWindowDimensions();
  const { errors, values, setValues } = useFormikContext<IMatchupFormInput[]>();

  const forceUpdate = useForceUpdate();
  const _selection = useConst(
    new Selection({
      selectionMode: SelectionMode.multiple,
      onSelectionChanged: forceUpdate,
    })
  );

  const comboBoxOptions: IComboBoxOption[] = teams.map((team) => ({
    ...team,
    key: team["SR key"],
    text: team["NCAA Name"] ?? team.School,
  }));

  const gridStyles: Partial<IDetailsListStyles> = {
    root: {
      overflowX: "hidden",
      selectors: {
        "& [role=grid]": {
          display: "flex",
          flexDirection: "column",
          alignItems: "start",
          height: `${height - 88}px`,
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
        key: "model",
        name: "Model",
        minWidth: 150,
        isResizable: false,
      },
      {
        key: "isNeutral",
        name: "Is neutral site?",
        minWidth: 150,
        isResizable: false,
      },
      {
        key: "logo1",
        name: "",
        minWidth: 40,
        maxWidth: 40,
        isResizable: false,
        onRenderField: (props) => {
          if (!props) return;
          const {
            item,
            column: { currentWidth },
          } = props;
          const team = teams.find(
            (team) => team["SR key"] === (item as IMatchupFormInput).team1
          );
          return (
            <Stack
              grow
              verticalAlign="center"
              horizontalAlign="center"
              style={{
                backgroundColor: team?.["background-color"] ?? undefined,
                width: (currentWidth ?? 0) + 20,
              }}
            >
              {
                <img
                  style={{
                    height: 30,
                    backgroundColor:
                      !team?.["NCAA key"] || !team?.["background-color"]
                        ? theme.palette.neutralTertiary
                        : undefined,
                  }}
                  src={
                    !!team?.["NCAA key"] && !!team?.["background-color"]
                      ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${team?.["NCAA key"]}.svg`
                      : no_logo
                  }
                />
              }
            </Stack>
          );
        },
      },
      {
        key: "team1",
        name: "Team 1",
        minWidth: 300,
        isResizable: false,
      },
      {
        key: "logo2",
        name: "",
        minWidth: 40,
        maxWidth: 40,
        isResizable: false,
        onRenderField: (props) => {
          if (!props) return;
          const {
            item,
            column: { currentWidth },
          } = props;
          const team = teams.find(
            (team) => team["SR key"] === (item as IMatchupFormInput).team2
          );
          return (
            <Stack
              grow
              verticalAlign="center"
              horizontalAlign="center"
              style={{
                backgroundColor: team?.["background-color"] ?? undefined,
                width: (currentWidth ?? 0) + 20,
              }}
            >
              {
                <img
                  style={{
                    height: 30,
                    backgroundColor:
                      !team?.["NCAA key"] || !team?.["background-color"]
                        ? theme.palette.neutralTertiary
                        : undefined,
                  }}
                  src={
                    !!team?.["NCAA key"] && !!team?.["background-color"]
                      ? `https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/${team?.["NCAA key"]}.svg`
                      : no_logo
                  }
                />
              }
            </Stack>
          );
        },
      },
      {
        key: "team2",
        name: "Team 2",
        minWidth: 300,
        isResizable: false,
      },
    ] as IColumn[];
  });

  const onRenderColumn = (
    item?: IMatchupFormInput,
    index?: number,
    column?: IColumn
  ): React.ReactNode => {
    const value =
      item && column && column.fieldName
        ? item[column.fieldName as keyof IMatchupFormInput] || ""
        : "";

    if (column?.key === "model")
      return (
        <Dropdown
          fieldName={`[${index}].${column?.key}`}
          options={[{ key: "placeholder", text: "Placeholder" }]}
        />
      );
    if (column?.key === "isNeutral")
      return (
        <Stack grow verticalAlign="end">
          <Toggle
            fieldName={`[${index}].${column?.key}`}
            onText="Neutral site"
            offText="Home/Away"
          />
        </Stack>
      );
    if (["team1", "team2"].includes(column?.key || ""))
      return (
        <ComboBox
          fieldName={`[${index}].${column?.key}`}
          options={comboBoxOptions}
          allowFreeInput
          autoComplete="on"
          onInputValueChange={(text, options) =>
            options.filter(
              (team) => !text || isSearchTextIncluded(team as any, text)
            )
          }
        />
      );
    return value;
  };

  const _onAddMatchup = () => setValues([...values, EMPTY_FORM_MATCHUP]);

  return (
    <Stack horizontalAlign="center">
      <Stack>
        <CommandBar
          items={[
            {
              key: "new",
              text: "New matchup",
              iconProps: { iconName: "Add" },
              onClick: _onAddMatchup as any,
            },
            {
              key: "delete",
              text: "Delete",
              iconProps: { iconName: "Delete" },
              disabled: _selection.getSelectedCount() < 1,
              onClick: () => {
                const indices = _selection.getSelectedIndices();
                const sortedIndices = indices.sort((n1, n2) => n2 - n1);

                const newValues = [...values];
                for (const i of sortedIndices) {
                  if (i >= 0 && i < newValues.length) {
                    newValues.splice(i, 1);
                  }
                }

                setValues(
                  newValues.length > 0 ? newValues : [EMPTY_FORM_MATCHUP]
                );
              },
            },
          ]}
          farItems={[
            {
              key: "submit",
              text: "Submit",
              type: "submit",
              iconProps: { iconName: "Send" },
              disabled: (errors?.length ?? 0) > 0,
              buttonStyles: {
                root: {
                  backgroundColor: theme.semanticColors.primaryButtonBackground,
                  color: theme.semanticColors.primaryButtonText,
                },
                rootHovered: {
                  backgroundColor:
                    theme.semanticColors.primaryButtonBackgroundHovered,
                  color: theme.semanticColors.primaryButtonTextHovered,
                },
                icon: {
                  color: theme.semanticColors.primaryButtonText,
                },
                iconHovered: {
                  color: theme.semanticColors.primaryButtonTextHovered,
                },
              },
            },
          ]}
          styles={{ root: { padding: 0 } }}
        />
        <DetailsList
          setKey="items"
          items={values.map((value, index) => ({ ...value, key: index }))}
          columns={columns}
          selectionMode={SelectionMode.multiple}
          constrainMode={ConstrainMode.unconstrained}
          layoutMode={DetailsListLayoutMode.fixedColumns}
          ariaLabelForGrid="Item details"
          styles={gridStyles}
          focusZoneProps={focusZoneProps}
          checkboxVisibility={CheckboxVisibility.always}
          selection={_selection}
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

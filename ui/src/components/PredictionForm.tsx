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
  Spinner,
} from "@fluentui/react";
import { useConst, useForceUpdate } from "@fluentui/react-hooks";
import { teams as TEAMS } from "../assets/teams";
import { IMatchupFormInput, ITeam } from "../common/models";
import { useWindowDimensions } from "../common/hooks";
import no_logo from "../assets/no-logo.svg";
import { Dropdown } from "./formik/Dropdown";
import { ComboBox } from "./formik/ComboBox";
import { useFormikContext } from "formik";
import { Toggle } from "./formik/Toggle";
import {
  EMPTY_FORM_MATCHUP,
  MODEL_OPTIONS,
  SPAN_OPTIONS,
} from "../common/constants";

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

export interface IPredictionForm {
  isWomens: boolean;
  setIsWomens: React.Dispatch<React.SetStateAction<boolean>>;
}

export const PredictionForm: React.FC<IPredictionForm> = ({
  isWomens,
  setIsWomens,
}) => {
  const theme = getTheme();
  const { height } = useWindowDimensions();
  const { errors, values, isSubmitting, setValues } =
    useFormikContext<IMatchupFormInput[]>();

  const forceUpdate = useForceUpdate();
  const _selection = useConst(
    new Selection({
      selectionMode: SelectionMode.multiple,
      onSelectionChanged: forceUpdate,
    }),
  );

  const teams = TEAMS.filter((team) =>
    isWomens ? !!team.isWomenTeam : !!team.isMenTeam,
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
        key: "span",
        name: "Span",
        minWidth: 150,
        isResizable: false,
      },
      {
        key: "model",
        name: "Model",
        minWidth: 200,
        isResizable: false,
      },
      {
        key: "neutral",
        name: "Site",
        minWidth: 120,
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
            (team) => team["SR key"] === (item as IMatchupFormInput).away_team,
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
        key: "away_team",
        name: "Away Team",
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
            (team) => team["SR key"] === (item as IMatchupFormInput).home_team,
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
        key: "home_team",
        name: "Home Team",
        minWidth: 300,
        isResizable: false,
      },
    ] as IColumn[];
  });

  const onRenderColumn = (
    item?: IMatchupFormInput,
    index?: number,
    column?: IColumn,
  ): React.ReactNode => {
    const value =
      item && column && column.fieldName
        ? item[column.fieldName as keyof IMatchupFormInput] || ""
        : "";

    if (column?.key === "span")
      return (
        <Dropdown
          fieldName={`[${index}].${column?.key}`}
          options={SPAN_OPTIONS}
        />
      );
    if (column?.key === "model")
      return (
        <Dropdown
          fieldName={`[${index}].${column?.key}`}
          options={MODEL_OPTIONS}
        />
      );
    if (column?.key === "neutral")
      return (
        <Stack grow verticalAlign="end">
          <Toggle
            fieldName={`[${index}].${column?.key}`}
            onText="Neutral site"
            offText="Home/Away"
          />
        </Stack>
      );
    if (["away_team", "home_team"].includes(column?.key || ""))
      return (
        <ComboBox
          fieldName={`[${index}].${column?.key}`}
          options={comboBoxOptions}
          allowFreeInput
          autoComplete="on"
          onInputValueChange={(text, options) =>
            options.filter(
              (team) => !text || isSearchTextIncluded(team as any, text),
            )
          }
        />
      );
    return value;
  };

  const _onAddMatchup = () =>
    setValues([
      ...values,
      { ...EMPTY_FORM_MATCHUP, gender: isWomens ? "women" : "men" },
    ]);

  return (
    <Stack horizontalAlign="center" styles={{ root: { padding: "0px 20px" } }}>
      <Stack>
        <CommandBar
          items={[
            {
              key: "new",
              text: "New matchup",
              iconProps: { iconName: "Add" },
              disabled: values?.length > 64,
              onClick: _onAddMatchup as any,
            },
            {
              key: "duplicate",
              text: "Duplicate",
              iconProps: { iconName: "Copy" },
              disabled: _selection.getSelectedCount() < 1,
              onClick: () => {
                const indices = _selection.getSelectedIndices();
                const newValues = [...values];
                indices.forEach((index) => {
                  if (index >= 0 && index < values.length) {
                    const duplicatedItem = { ...values[index] };
                    newValues.push(duplicatedItem);
                  }
                });
                setValues(newValues);
              },
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
                  newValues.length > 0
                    ? newValues
                    : [
                        {
                          ...EMPTY_FORM_MATCHUP,
                          gender: isWomens ? "women" : "men",
                        },
                      ],
                );
              },
            },
            {
              key: "type",
              text: isWomens ? "Mode: Women" : "Mode: Men",
              subMenuProps: {
                items: [
                  {
                    key: "option1",
                    text: isWomens ? "Men" : "Women",
                    onClick: () => setIsWomens(!isWomens),
                  },
                ],
              },
            },
          ]}
          farItems={[
            {
              key: "submit",
              text: "Submit",
              type: "submit",
              iconProps: { iconName: "Send" },
              onRenderIcon: isSubmitting ? () => <Spinner /> : undefined,
              disabled: (errors?.length ?? 0) > 0 || isSubmitting,
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

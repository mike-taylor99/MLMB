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
  const items = [
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
    {
      key: "1",
      name: "Connecticut",
      logo: "https://www.ncaa.com/sites/default/files/images/logos/schools/bgd/uconn.svg",
    },
  ];

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
                backgroundColor: "#0C2340",
                width: (currentWidth ?? 0) + 20,
                height: 42,
              }}
            >
              <img style={{ height: 30 }} src={item.logo} />
            </Stack>
          );
        },
      },
      {
        key: "column1",
        name: "Name",
        fieldName: "name",
        minWidth: 40,
        maxWidth: 200,
        isResizable: false,
      },
      {
        key: "rank",
        name: "Rank",
        fieldName: "key",
        minWidth: 40,
        maxWidth: 40,
        isResizable: false,
      },
    ] as IColumn[];
  });

  return (
    <div>
      {false ? (
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

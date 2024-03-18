import {
  CommandBar,
  IButtonStyles,
  ICommandBarItemProps,
  ICommandBarProps,
  IPanelProps,
  Icon,
  Link,
  Panel,
  Stack,
  Text,
  getTheme,
} from "@fluentui/react";
import { useBoolean } from "@fluentui/react-hooks";
import { Navigation } from "./Navigation";
import { Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";

export const Layout: React.FC = () => {
  const theme = getTheme();
  const navigate = useNavigate();
  const [isNavOpen, { setFalse: closeNav, toggle: toggleNav }] =
    useBoolean(false);
  const [isPanelOpen, { toggle: togglePanel }] = useBoolean(false);
  const [panelType, setPanelType] = useState<string>("feedback");

  const commandBarStyles: ICommandBarProps["styles"] = {
    root: {
      backgroundColor: theme.palette.orangeLighter,
      padding: 0,
    },
  };

  const buttonStyles: IButtonStyles = {
    root: {
      backgroundColor: theme.palette.orangeLighter,
      color: theme.semanticColors.primaryButtonText,
      paddingLeft: 14,
      paddingRight: 14,
    },
    rootHovered: {
      backgroundColor: theme.palette.orangeLight,
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    rootExpanded: {
      backgroundColor: theme.palette.orangeLight,
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    rootExpandedHovered: {
      backgroundColor: theme.palette.orangeLight,
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    icon: {
      color: theme.semanticColors.primaryButtonText,
    },
    iconHovered: {
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    iconExpanded: {
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    menuIcon: {
      color: theme.semanticColors.primaryButtonText,
    },
    menuIconHovered: {
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    menuIconExpanded: {
      color: theme.semanticColors.primaryButtonTextHovered,
    },
    menuIconExpandedHovered: {
      color: theme.semanticColors.primaryButtonTextHovered,
    },
  };

  const items: ICommandBarItemProps[] = [
    {
      key: "menu",
      iconProps: { iconName: "CollapseMenu" },
      iconOnly: true,
      buttonStyles: {
        ...buttonStyles,
        root: {
          ...(buttonStyles.root as object),
          backgroundColor: isNavOpen
            ? theme.palette.orangeLight
            : theme.palette.orangeLighter,
          color: isNavOpen
            ? theme.semanticColors.primaryButtonTextHovered
            : theme.semanticColors.primaryButtonText,
        },
      },
      onClick: () => {
        !isNavOpen && toggleNav();
      },
    },
    {
      key: "home",
      text: "MLMB",
      iconProps: { iconName: "CollegeHoops" },
      buttonStyles: {
        ...buttonStyles,
        root: {
          ...(buttonStyles.root as object),
          fontSize: "1.15rem",
          fontWeight: "bold",
        },
        icon: {
          ...(buttonStyles.icon as object),
          fontSize: "1.2rem",
        },
      },
      onClick: () => navigate("/"),
    },
  ];

  const farItems: ICommandBarItemProps[] = [
    {
      key: "donate",
      text: "Donate",
      ariaLabel: "Donate",
      iconOnly: true,
      iconProps: { iconName: "Money" },
      onClick: () => {
        setPanelType("donate");
        togglePanel();
      },
      buttonStyles: {
        ...buttonStyles,
        root: {
          ...(buttonStyles.root as object),
          backgroundColor:
            isPanelOpen && panelType === "donate"
              ? theme.palette.orangeLight
              : theme.palette.orangeLighter,
          color:
            isPanelOpen && panelType === "donate"
              ? theme.semanticColors.primaryButtonTextHovered
              : theme.semanticColors.primaryButtonText,
        },
      },
    },
    {
      key: "feedback",
      text: "Feedback",
      ariaLabel: "Feedback",
      iconOnly: true,
      iconProps: { iconName: "Feedback" },
      onClick: () => {
        setPanelType("feedback");
        togglePanel();
      },
      buttonStyles: {
        ...buttonStyles,
        root: {
          ...(buttonStyles.root as object),
          backgroundColor:
            isPanelOpen && panelType === "feedback"
              ? theme.palette.orangeLight
              : theme.palette.orangeLighter,
          color:
            isPanelOpen && panelType === "feedback"
              ? theme.semanticColors.primaryButtonTextHovered
              : theme.semanticColors.primaryButtonText,
        },
      },
    },
  ];

  const panelProps: { [name: string]: IPanelProps } = {
    donate: {
      headerText: "Donate",
      children: (
        <Stack>
          <Text>
            Behind the scenes, there’s a dedicated team investing time, effort,
            and resources to keep this tool running smoothly. If you’ve found it
            valuable and it has aided you in your endeavors, please consider
            making a donation. Every contribution, no matter how small, helps
            sustain this service and ensures its continued availability.
          </Text>
          <Link href="https://venmo.com/u/Michael-Taylor-254">
            Venmo <Icon iconName="Link" />
          </Link>
        </Stack>
      ),
    },
    feedback: {
      headerText: "Feedback",
      children: (
        <Stack>
          <Text>
            For issues or feature requests, use the Github issues link below.
          </Text>
          <Link href="https://github.com/mike-taylor99/MLMB/issues">
            MLMB Github <Icon iconName="Link" />
          </Link>
        </Stack>
      ),
    },
  };

  return (
    <>
      <CommandBar
        styles={commandBarStyles}
        items={items}
        farItems={farItems}
        overflowButtonProps={{ styles: buttonStyles }}
      />
      <Navigation isOpen={isNavOpen} closeNav={closeNav} />
      <Panel
        isOpen={isPanelOpen}
        onDismiss={togglePanel}
        isLightDismiss
        styles={{ root: { top: 44 } }}
        {...panelProps[panelType]}
      />
      <div className="content">
        <Stack grow>
          <Outlet />
        </Stack>
      </div>
      <div className="footer"></div>
    </>
  );
};

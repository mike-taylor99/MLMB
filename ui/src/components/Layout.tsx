import {
  CommandBar,
  IButtonStyles,
  ICommandBarItemProps,
  ICommandBarProps,
  Stack,
  getTheme,
} from "@fluentui/react";
import { useBoolean } from "@fluentui/react-hooks";
import { Navigation } from "./Navigation";
import { Outlet, useNavigate } from "react-router-dom";

export const Layout: React.FC = () => {
  const theme = getTheme();
  const navigate = useNavigate();
  const [isNavOpen, { setFalse: closeNav, toggle: toggleNav }] =
    useBoolean(false);

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
      key: "info",
      text: "Info",
      ariaLabel: "Info",
      iconOnly: true,
      iconProps: { iconName: "Info" },
      buttonStyles,
    },
  ];

  return (
    <>
      <CommandBar
        styles={commandBarStyles}
        items={items}
        farItems={farItems}
        overflowButtonProps={{ styles: buttonStyles }}
      />
      <Navigation isOpen={isNavOpen} closeNav={closeNav} />
      <div className="content">
        <Stack grow>
          <Outlet />
        </Stack>
      </div>
      <div className="footer"></div>
    </>
  );
};

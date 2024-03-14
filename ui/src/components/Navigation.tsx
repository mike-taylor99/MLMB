import {
  INavLink,
  INavLinkGroup,
  INavProps,
  Nav,
  getTheme,
} from "@fluentui/react";
import { useWindowDimensions } from "../common/hooks";
import { useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";

export interface INavigationProps {
  isOpen: boolean;
  closeNav: () => void;
}

export const Navigation: React.FC<INavigationProps> = ({
  isOpen,
  closeNav,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const theme = getTheme();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { height } = useWindowDimensions();

  const styles: INavProps["styles"] = {
    root: {
      minWidth: 200,
      height: height - 44, // Header/CommandBar height is 44
      boxSizing: "border-box",
      border: "2px solid #eee",
      overflowY: "auto",
      zIndex: 1,
      backgroundColor: theme.palette.white,
      boxShadow:
        "0 6.4px 14.4px 0 rgba(0,0,0,.132),0 1.2px 3.6px 0 rgba(0,0,0,.108)",
    },
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        closeNav();
      }
    };

    document.addEventListener("click", handleClickOutside, true);

    return () => {
      document.removeEventListener("click", handleClickOutside, true);
    };
  }, []);

  const _onClick = (
    _ev?: React.MouseEvent<HTMLElement, MouseEvent>,
    item?: INavLink
  ) => {
    if (!item) return;
    navigate(item.key!);
    closeNav();
  };

  const groups: INavLinkGroup[] = [
    {
      links: [
        {
          name: "Home",
          key: "/",
          url: "",
          onClick: _onClick,
          iconProps: {
            iconName: "HomeSolid",
            styles: { root: { color: theme.palette.themePrimary } },
          },
        },
        {
          name: "Predict",
          key: "/predict",
          url: "",
          onClick: _onClick,
          iconProps: {
            iconName: "Trophy2Solid",
            styles: { root: { color: theme.palette.yellow } },
          },
        },
        {
          name: "Teams",
          key: "/teams",
          url: "",
          onClick: _onClick,
          iconProps: {
            iconName: "PageListSolid",
            styles: { root: { color: theme.palette.blueLight } },
          },
        },
      ],
    },
  ];

  return (
    <div ref={ref}>
      {isOpen && (
        <Nav isOnTop selectedKey={pathname} groups={groups} styles={styles} />
      )}
    </div>
  );
};

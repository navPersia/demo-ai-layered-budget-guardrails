import * as React from "react";
import "./studiostreamx-logo.css";

export function StudioStreamXAnimatedLogo(props: React.SVGProps<SVGSVGElement>) {
  const titleId = React.useId();

  return (
    <svg
      viewBox="0 0 1060 300"
      role="img"
      aria-labelledby={titleId}
      className={`ssx-logo ${props.className ?? ""}`}
      {...props}
    >
      <title id={titleId}>StudioStreamX animated logo</title>

      <text
        className="ssx-logo__word"
        x="60"
        y="180"
        fill="currentColor"
        fontFamily="Inter, Arial, Helvetica, sans-serif"
        fontSize="120"
        fontWeight="700"
        fontStyle="italic"
        letterSpacing="-7.2"
      >
        StudioStream
      </text>

      <g className="ssx-logo__x" fill="currentColor" transform="translate(760 60)">
        <path d="M40 220 82 174 201 50 218 36 204 53 85 177Z" />
        <path d="M75 35h21l40 41-17 8Z" />
        <path d="m139 121 17-8 41 42 1 22-17-2Z" />
      </g>
    </svg>
  );
}

import * as React from "react";

type LogoVariant = "full" | "mark" | "wordmark";

export type StudioStreamXLogoProps = React.SVGProps<SVGSVGElement> & {
  variant?: LogoVariant;
  title?: string;
};

export function StudioStreamXLogo({
  variant = "full",
  title = variant === "mark" ? "StudioStreamX mark" : variant === "wordmark" ? "StudioStream" : "StudioStreamX",
  className,
  ...props
}: StudioStreamXLogoProps) {
  const titleId = React.useId();

  if (variant === "mark") {
    return (
      <svg viewBox="0 0 256 256" role="img" aria-labelledby={titleId} className={className} {...props}>
        <title id={titleId}>{title}</title>
        <g fill="currentColor">
          <path d="M40 220 82 174 201 50 218 36 204 53 85 177Z" />
          <path d="M75 35h21l40 41-17 8Z" />
          <path d="m139 121 17-8 41 42 1 22-17-2Z" />
        </g>
      </svg>
    );
  }

  if (variant === "wordmark") {
    return (
      <svg viewBox="0 0 820 300" role="img" aria-labelledby={titleId} className={className} {...props}>
        <title id={titleId}>{title}</title>
        <text
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
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 1060 300" role="img" aria-labelledby={titleId} className={className} {...props}>
      <title id={titleId}>{title}</title>
      <g fill="currentColor">
        <text
          x="60"
          y="180"
          fontFamily="Inter, Arial, Helvetica, sans-serif"
          fontSize="120"
          fontWeight="700"
          fontStyle="italic"
          letterSpacing="-7.2"
        >
          StudioStream
        </text>
        <g transform="translate(760 60)">
          <path d="M40 220 82 174 201 50 218 36 204 53 85 177Z" />
          <path d="M75 35h21l40 41-17 8Z" />
          <path d="m139 121 17-8 41 42 1 22-17-2Z" />
        </g>
      </g>
    </svg>
  );
}

export default StudioStreamXLogo;

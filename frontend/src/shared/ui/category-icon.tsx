import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function SchematicIcon({ size = 24, children, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      {children}
    </svg>
  );
}

function BreakerIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <rect
        height="18"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.5"
        width="14"
        x="5"
        y="3"
      />
      <path
        d="M12 7v4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="15" r="2" stroke="currentColor" strokeWidth="1.5" />
    </SchematicIcon>
  );
}

function ProtectionIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="m12 3 7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
      <path
        d="m9 12 2 2 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function CableIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="M4 8c3 0 3 3 6 3s3-3 6-3 3 3 4 3M4 15c3 0 3 3 6 3s3-3 6-3 3 3 4 3"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function SocketIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <rect
        height="16"
        rx="3"
        stroke="currentColor"
        strokeWidth="1.5"
        width="16"
        x="4"
        y="4"
      />
      <circle cx="9.5" cy="12" fill="currentColor" r="1.4" />
      <circle cx="14.5" cy="12" fill="currentColor" r="1.4" />
    </SchematicIcon>
  );
}

function BulbIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="M9 18h6M10 21h4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <path
        d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1.1 1.3 1.1 2.2h5a2.7 2.7 0 0 1 1.1-2.2A6 6 0 0 0 12 3Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function PanelIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <rect
        height="18"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.5"
        width="16"
        x="4"
        y="3"
      />
      <path
        d="M7 7.5h10M7 12h10M7 16.5h6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function GaugeIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="M4 15a8 8 0 1 1 16 0M12 15l3.5-4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="15" fill="currentColor" r="1.3" />
    </SchematicIcon>
  );
}

function GroundIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="M12 3v9M6 12h12M8 15.5h8M10 19h4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function BatteryIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <rect
        height="10"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.5"
        width="16"
        x="3"
        y="7"
      />
      <path
        d="M21 10.5v3M7 12h8"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function HeatIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="M4 9c1.5 1.5 1.5 3 0 4.5M9 9c1.5 1.5 1.5 3 0 4.5M14 9c1.5 1.5 1.5 3 0 4.5M19 9c1.5 1.5 1.5 3 0 4.5M4 18h16"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

function HomeIcon(props: IconProps) {
  return (
    <SchematicIcon {...props}>
      <path
        d="m4 11 8-6 8 6M6 10v9h12v-9M10 19v-5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </SchematicIcon>
  );
}

const iconByCategory: Record<string, (props: IconProps) => React.ReactNode> = {
  sockets: SocketIcon,
  lowvoltage: BreakerIcon,
  relay: ProtectionIcon,
  switching: SocketIcon,
  cable: CableIcon,
  cabletrays: CableIcon,
  installation: PanelIcon,
  panels: PanelIcon,
  light: BulbIcon,
  hv: BreakerIcon,
  metering: GaugeIcon,
  grounding: GroundIcon,
  network: CableIcon,
  power: BatteryIcon,
  heating: HeatIcon,
  evcharge: BatteryIcon,
  smarthome: HomeIcon,
  other: PanelIcon,
};

export function CategoryIcon({ slug, ...props }: IconProps & { slug: string }) {
  const Icon = iconByCategory[slug] ?? PanelIcon;
  return <Icon {...props} />;
}

export type CapabilityIconName =
  | "Globe"
  | "FileKey"
  | "FileText"
  | "Network"
  | "FileWarning"
  | "KeyRound"
  | "Terminal"
  | "CircleHelp";

export interface CapabilityDisplay {
  label: string;
  iconName: CapabilityIconName;
}

const capabilityDisplays: Record<string, CapabilityDisplay> = {
  network: { label: "Network Access", iconName: "Network" },
  file_sensitive: { label: "Sensitive File Access", iconName: "FileKey" },
  file_general: { label: "General File Access", iconName: "FileText" },
  env_secrets: { label: "Secrets Access", iconName: "KeyRound" },
  subprocess: { label: "Subprocess Execution", iconName: "Terminal" },
  file_read: { label: "File Read", iconName: "FileWarning" },
  env_read: { label: "Environment Variable Read", iconName: "KeyRound" },
};

export function getCapabilityDisplay(capability: string): CapabilityDisplay {
  const knownCapability = capabilityDisplays[capability];

  if (knownCapability) {
    return knownCapability;
  }

  const label = capability
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  return {
    label: label || "Unknown Capability",
    iconName: "CircleHelp",
  };
}
